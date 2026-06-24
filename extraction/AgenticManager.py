import sys
import os
import tempfile
import ollama
import pdfplumber
from pathlib import Path
from pdf2image import convert_from_path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from injestion.models import DocumentRecord, DocumentSource

from .Schema import Schema, SignatureCheck
from .SignatureLocator import find_signature_page

TEXT_MODEL = "llama3.1:8b"
VISION_MODEL = "llava:7b"


extra_context_tool = {
    "type": "function",
    "function": {
        "name": "extra_context_tool",
        "description": "Call this to get more content from the document when you need additional context to fill the schema.",
        "parameters": {
            "type": "object",
            "properties": {
                "page_number": {
                    "type": "integer",
                    "description": "The page to retrieve (starting from 1). For non-PDF documents this returns the next 4000 character chunk."
                }
            },
            "required": ["page_number"]
        }
    }
}


class AgenticManager:
    def __init__(self, source: DocumentSource):
        self.source = source

    def process_all(self):
        for doc in self.source.load_documents():
            try:
                schema = self.ai_extraction(doc)
                signature_check = self.check_signatures(doc)
                yield doc, schema, signature_check, None
            except Exception as e:
                yield doc, None, None, e

    def ai_extraction(self, doc: DocumentRecord) -> Schema:
        text = doc.content

        system_prompt = (
            "You are working for Minnesota Public Radio's Legal Department. "
            "You are responsible for searching through text and finding the metadata required to create a naming convention. "
            "If you are unable to parse ALL the structured/required schema from the text, you MUST call the extra_context_tool."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"File name: {Path(doc.source_id).name}\n\n"
                    f"Extract contract metadata from this document:\n\n{text}\n\n"
                    "If you are unable to find ALL the required fields from the text "
                    "of the document you MUST call the extra_context_tool.\n\n"
                    "Here are some examples of what we are expecting...\n\n"
                    "Berlin Minneapolis - Location Rental Agreement  - Nina Bernat 4.22.25 - YC (2025.4.17) v1.0 FE\n"
                    "Charitable Adult Rides CARS - Standard Agreement - car donations - MPR (2025.4.10) v1.0 FE\n"
                    "Jackson River LLC - Order Form SOW - Springboard LAist Modal embed - LAist (2025.4.8.) v1.0 FE\n"
                    "HayesGiselle - Performance Artist Event and Recording Agreement - Amsterdam bar – the current (2025.4.10) v1.0 FE\n"
                    "Boston Beer Company - Sponsorship Agreement - Tournament of Cheeseburgers - LAist (2025.5.15) v1.0 FE\n"
                    "Bill.com - SaaS order form - Accounts Payable software - MPR Finance (2025.5.16) v1.0 FE"
                )
            }
        ]

        current_page = 1
        MAX_PAGES = 5

        # Phase 1: let the model freely call extra_context_tool as many
        # times as it needs. We deliberately do NOT pass `format` here —
        # mixing tool calls with a forced JSON schema confuses llama3.1:8b
        # (it'll just hallucinate JSON and ignore the tool entirely). So
        # this phase is plain back-and-forth text/tool-calls only.
        while True:
            response = ollama.chat(
                model=TEXT_MODEL,
                messages=messages,
                tools=[extra_context_tool],
            )

            if not response.message.tool_calls:
                # model is done gathering context — content here is just
                # free text, we don't trust it as the final answer yet
                break

            messages.append({
                "role": "assistant",
                "content": response.message.content or "",
                "tool_calls": response.message.tool_calls,
            })

            for tool_call in response.message.tool_calls:
                if current_page <= MAX_PAGES:
                    print(f"    [TOOL] extra_context_tool called -> fetching page {current_page} of {Path(doc.source_id).name}")
                    content = self.extra_context(doc, current_page)
                    current_page += 1
                else:
                    print(f"    [LIMIT] Page limit reached for {Path(doc.source_id).name}")
                    content = "Maximum pages reached. Use 'Unknown' for any fields you could not determine."

                messages.append({
                    "role": "tool",
                    "tool_name": tool_call.function.name,
                    "content": content,
                })

        # Phase 2: one final call, no tools this time, asking the model to
        # commit everything it has gathered into the actual schema shape.
        messages.append({
            "role": "user",
            "content": "Now output the final answer as JSON matching the required schema. Do not call any more tools."
        })
        json_schema = {**Schema.model_json_schema(), "additionalProperties": False}
        final_response = ollama.chat(
            model=TEXT_MODEL,
            messages=messages,
            format=json_schema,
        )
        return Schema.model_validate_json(final_response.message.content)

    def extra_context(self, doc: DocumentRecord, page_number: int) -> str:
        ext = Path(doc.source_id).suffix.lower()
        if ext == ".pdf":
            with pdfplumber.open(doc.source_id) as pdf:
                if page_number < len(pdf.pages):
                    return pdf.pages[page_number].extract_text() or ""
                return ""
        else:
            # the source object (e.g. LocalFileSource) owns a DocumentExtractor
            # which is what actually knows how to read each file type now
            full_text = self.source.extractor.extract(doc.source_id)
            start = page_number * 4000
            return full_text[start:start + 4000]

    def check_signatures(self, doc: DocumentRecord) -> SignatureCheck | None:
        # only PDFs go through this — signature pages for other formats
        # would need their own rendering approach, and we don't have one yet
        if Path(doc.source_id).suffix.lower() != ".pdf":
            return None

        page_number = find_signature_page(doc.source_id)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # render just the one page we found, not the whole document —
            # this is the expensive step (image + vision model), so we only
            # pay for it once per document
            images = convert_from_path(
                doc.source_id, first_page=page_number, last_page=page_number, dpi=200
            )
            image_path = Path(tmp_dir) / "signature_page.png"
            images[0].save(image_path)

            # llava is a small model — it does much better answering a short
            # list of concrete questions in order than one open-ended ask.
            # Spelling out exactly what counts as "signed" vs "blank" cuts
            # down on it guessing or pattern-matching the wrong thing.
            vision_prompt = (
                "Look closely at each signature line on this page, one at a time.\n\n"
                "A line is SIGNED only if it has an actual mark directly on it: "
                "handwritten cursive, a typed name, or a 'DocuSign'-style signature block.\n"
                "A line is BLANK if it is empty, or only shows a printed label like "
                "'Signature:' or 'X' with nothing filled in after it.\n\n"
                "Answer these three questions in order:\n"
                "1. Is this page a signature/execution page of a contract?\n"
                "2. Going line by line, is AT LEAST ONE signature line actually SIGNED "
                "(not blank)?\n"
                "3. ONLY IF you answered yes to question 2: what date is written next "
                "to that specific signed line? If no line is signed, leave this blank — "
                "do not report a date next to a blank line."
            )

            response = ollama.chat(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": vision_prompt,
                    "images": [str(image_path)],
                }],
                format=SignatureCheck.model_json_schema(),
            )

        return SignatureCheck.model_validate_json(response.message.content)

    def naming_convention(self, schema: Schema):
        return f"{schema.counterparty} - {schema.agreement_type} - {schema.helpful_phrase} - {schema.brand} {schema.date} {schema.executed} v1.0 FE"


#testing suite
if __name__ == '__main__':

    from injestion.LocalFileSource import LocalFileSource

    TEST_DIR = '/Users/srikotala/Documents/projects/testDocuments'
    print(f"\n{'='*60}")
    print(f"  LegaIAI Extraction Run")
    print(f"  Source: {TEST_DIR}")
    print(f"{'='*60}\n")

    src = LocalFileSource(TEST_DIR)
    manager = AgenticManager(src)

    success_count = 0
    fail_count = 0

    for i, (doc, schema, signature_check, error) in enumerate(manager.process_all(), start=1):
        print(f"[{i}] Processing: {doc.source_id}")
        if error is not None:
            fail_count += 1
            print(f"    ERROR: {type(error).__name__}: {error}")
        else:
            print(f"    Counterparty   : {schema.counterparty}")
            print(f"    Agreement Type : {schema.agreement_type}")
            print(f"    Helpful Phrase : {schema.helpful_phrase}")
            print(f"    Brand          : {schema.brand}")
            print(f"    Date           : {schema.date}")
            print(f"    Needs Review   : {schema.needs_review}")
            print(f"    -> Named       : {manager.naming_convention(schema)}")
            if signature_check:
                print(f"    Signed         : {signature_check.signed} (execution date: {signature_check.execution_date})")
            success_count += 1
        print()

    print(f"{'='*60}")
    print(f"  Done. {success_count} succeeded, {fail_count} failed.")
    print(f"{'='*60}\n")
