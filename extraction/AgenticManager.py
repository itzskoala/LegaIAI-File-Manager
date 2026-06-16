import ollama
import json
import sys
import os
import pdfplumber
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources_injestion.FileManager import DocumentRecord, DocumentSource

# from LocalFileSource import LocalFileSource
# from EmailFileSource import EmailFileSource
# from SharepointFileSource import SharepointFileSource

from Schema import Schema

#right down all the tools
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
        #call the Baseclass so I don't have to individually call the children...!
        self.source = source #stores the child obj

    def process_all(self):
        for doc in self.source.load_documents():
            yield self.ai_extraction(doc)


    def ai_extraction(self, doc: DocumentRecord) -> Schema: 
        #This returns a schema that the naming convention will parse together and rename the file...

        text = doc.content #this should only be a page at first

        #instructions for Ollama
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
                    f"Extract contract metadata from this document:\n\n{text}\n\n"
                    "Conform to the schema as given in your format.\n\n"
                    "If you are unable to parse ALL the structured schema from the text "
                    "of the document you MUST call the extra_context_tool.\n\n"
                    "Here are some examples of what we are expecting...\n\n"
                    #TODO
                )
            }
        ]

        current_page = 1
        MAX_PAGES = 5  # don't read more than 5 pages before giving up

        while True:
            response = ollama.chat(
                model="gemma3",
                messages=messages,
                format=Schema.model_json_schema(),
                tools=[extra_context_tool]
            )
            if response.message.tool_calls and current_page <= MAX_PAGES:
                for tool_call in response.message.tool_calls:
                    extra = self.extra_context(doc, current_page) #actually calling the tool and grabbing extra content
                    current_page += 1  # always move forward — don't trust the model to track this
                    # record model's tool call and our response back into the conversation
                    messages.append({"role": "assistant", "content": response.message.content, "tool_calls": response.message.tool_calls})
                    messages.append({"role": "tool", "content": extra, "name": "extra_context_tool"}) #adding the result of the tool call to the messages
            else:
                # model has enough (or hit page limit) — return the schema
                return Schema.model_validate_json(response.message.content)
        
    def extra_context_tool(self, doc: DocumentRecord, page_number: int) -> str:
    #code to call the next page of the document. feed back to ai_extraction, if still can't understand then go to the next page
        ext = Path(doc.source_id).suffix.lower()
        if ext == ".pdf":
                # PDFs get the actual next page
                with pdfplumber.open(doc.source_id) as pdf:
                    if page_number < len(pdf.pages):
                        return pdf.pages[page_number].extract_text() or ""
                    return ""
        else:
            # everything else (including scanned/OCR'd docs) gets the next 4000 char chunk
            full_text = self.source.extract_text_from_file(doc.source_id)
            start = page_number * 4000
            return full_text[start:start + 4000]

    
    def naming_convention(self, schema: Schema):
        #The naming convention must be {Counterparty} - {AgreementType} - {Brand} ({YYYY-MM-DD}) ({Status}).{ext}
        #use the schema object to contrsut the naming convention
        return f"{schema.counterparty} - {schema.agreement} - {schema.brand} ({schema.date}) {schema.version}"
    

    
    if __name__ == 'main':
        from LocalFileSource import LocalFileSource
        src = LocalFileSource('/Users/srikotala/Documents/projects/ContractRepo')
        manager = AgenticManager(src)

        for result in manager.process_all():
            print(result)

    # def confidence_check():
    #     #call another LLM?
    #     #how else can we do a confidence check?

    