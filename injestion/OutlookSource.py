from .DocumentExtractor import DocumentExtractor
from .models import DocumentSource
from .models import DocumentSource


'''
# 1. Power Automate watches Outlook/shared mailbox.
# MS Power Automate downloads attachments to that email and puts it in a desinated folder
# So all my code has to do is just scan/sync that folder (on a scheduler) the SharePoint library.

5. Python sends each file through:
   DocumentExtractionPipeline
       handles ZIP
       calls DocumentExtractor
       calls PDF/DOCX/CSV/MSG/Image strategies

6. Python outputs:
   DocumentRecord
   checksum
   source path
   source system
   email metadata
   extracted text
'''


class OutlookSource(DocumentSource):
    def __init__(self):
        self.extractor = DocumentExtractor()

    def load_documents(self):
        for attachment_path in .... this has to be the folder/outlook source?
            # iterate over each attachemnt/email whatever it is and send it to the extractors layer which then calls the indivuals
            content = self.extractor.extract(attachment_path)

            yield DocumentRecord(
                source_type="outlook",
                source_id=str(attachment_path),
                title=attachment_path.name,
                content=content,
                date=None,
            )



