import anthropic
import sys
import os
import time
import pdfplumber
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources_injestion.FileManager import DocumentRecord, DocumentSource

# from LocalFileSource import LocalFileSource
# from EmailFileSource import EmailFileSource
# from SharepointFileSource import SharepointFileSource

from Schema import Schema

extra_context_tool = {
    "name": "extra_context_tool",
    "description": "Call this to get more content from the document when you need additional context to fill the schema.",
    "input_schema": {
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

class AgenticManager:
    def __init__(self, source: DocumentSource):
        self.source = source
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def process_all(self):
        for doc in self.source.load_documents():
            yield self.ai_extraction(doc)

    def ai_extraction(self, doc: DocumentRecord) -> Schema:
        text = doc.content

        system_prompt = (
            "You are working for Minnesota Public Radio's Legal Department. "
            "You are responsible for searching through text and finding the metadata required to create a naming convention. "
            "If you are unable to parse ALL the structured/required schema from the text, you MUST call the extra_context_tool."
        )

        messages = [
            {
                "role": "user",
                "content": (
                    f"File name: {Path(doc.source_id).name}\n\n"
                    f"Extract contract metadata from this document:\n\n{text}\n\n"
                    "Conform to the schema as given in your format.\n\n"
                    "If you are unable to parse ALL the structured schema from the text "
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
        json_schema = {**Schema.model_json_schema(), "additionalProperties": False}

        while True:
            response = self.client.messages.create(
                model="claude-opus-4-8",
                max_tokens=4096,
                system=system_prompt,
                tools=[extra_context_tool],
                messages=messages,
                output_config={"format": {"type": "json_schema", "schema": json_schema}}
            )

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # end_turn — response is already structured JSON
                text_block = next(b for b in response.content if b.type == "text")
                return Schema.model_validate_json(text_block.text)

            # Handle tool calls
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tb in tool_use_blocks:
                if current_page <= MAX_PAGES:
                    print(f"    [TOOL] extra_context_tool called -> fetching page {current_page} of {Path(doc.source_id).name}")
                    content = self.extra_context(doc, current_page)
                    current_page += 1
                else:
                    print(f"    [LIMIT] Page limit reached for {Path(doc.source_id).name}")
                    content = "Maximum pages reached. Use 'Unknown' for any fields you could not determine."

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tb.id,
                    "content": content
                })

            messages.append({"role": "user", "content": tool_results})

    def extra_context(self, doc: DocumentRecord, page_number: int) -> str:
        ext = Path(doc.source_id).suffix.lower()
        if ext == ".pdf":
            with pdfplumber.open(doc.source_id) as pdf:
                if page_number < len(pdf.pages):
                    return pdf.pages[page_number].extract_text() or ""
                return ""
        else:
            full_text = self.source.extract_text_from_file(doc.source_id)
            start = page_number * 4000
            return full_text[start:start + 4000]

    def naming_convention(self, schema: Schema):
        return f"{schema.counterparty} - {schema.agreement_type} - {schema.helpful_phrase} - {schema.brand} {schema.date} v1.0 FE"


#testing suite
if __name__ == '__main__':

    from sources_injestion.LocalFileSource import LocalFileSource

    TEST_DIR = '/Users/srikotala/Documents/projects/testDocuments'
    print(f"\n{'='*60}")
    print(f"  LegaIAI Extraction Run")
    print(f"  Source: {TEST_DIR}")
    print(f"{'='*60}\n")

    src = LocalFileSource(TEST_DIR)
    manager = AgenticManager(src)

    success_count = 0
    fail_count = 0

    for i, doc in enumerate(src.load_documents(), start=1):
        print(f"[{i}] Processing: {doc.source_id}")
        try:
            result = manager.ai_extraction(doc)
            success_count += 1
            print(f"    Counterparty   : {result.counterparty}")
            print(f"    Agreement Type : {result.agreement_type}")
            print(f"    Helpful Phrase : {result.helpful_phrase}")
            print(f"    Brand          : {result.brand}")
            print(f"    Date           : {result.date}")
            print(f"    Needs Review   : {result.needs_review}")
            print(f"    -> Named       : {manager.naming_convention(result)}")
        except Exception as e:
            fail_count += 1
            print(f"    ERROR: {type(e).__name__}: {e}")
        print()
        # time.sleep(3)

    print(f"{'='*60}")
    print(f"  Done. {success_count} succeeded, {fail_count} failed.")
    print(f"{'='*60}\n")
