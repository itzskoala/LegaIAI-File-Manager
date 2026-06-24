import datetime
import shutil
import tempfile
import zipfile
from pathlib import Path

from .DocumentExtractor import DocumentExtractor
from .extractors import UnsupportedFileTypeError
from .models import DocumentRecord, DocumentSource


#implements the interfact/ABC that is DocumentSource
#is connected to 
class LocalFileSource(DocumentSource):
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.extractor = DocumentExtractor()

        # sibling folder next to the source — avoids rglob picking up the copies on the next run
        self.unprocessed_folder = Path(folder_path).parent / (Path(folder_path).name + "_unprocessed")

    def load_documents(self):
        for file_path in Path(self.folder_path).rglob("*"):
            if not file_path.is_file():
                continue

            # zip files get special treatment — extract to a temp folder and recurse
            # so each file inside counts as its own document
            if file_path.suffix.lower() == ".zip":
                with tempfile.TemporaryDirectory() as tmp_dir:
                    with zipfile.ZipFile(file_path, "r") as zip_ref:
                        zip_ref.extractall(tmp_dir)
                    for extracted_doc in LocalFileSource(tmp_dir).load_documents():
                        yield extracted_doc #yield allows to trickle instead of all at once :)
                continue

            #main logic of this function
            try:
                content = self.extractor.extract(file_path)
                
                if file_path.suffix.lower() != ".pdf":  # pdfs should be the full first page...!
                    content = content[:4000]  # first 4000 chars for non-PDFs

                yield DocumentRecord(
                    source_type="local_file",
                    source_id=str(file_path),
                    title=file_path.name,
                    content=content, #this pulls from the extractor based on the file extension :)
                    date=datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                )
            except UnsupportedFileTypeError:
                print(f"  [SKIP] {file_path.name}")
                self._copy_to_unprocessed(file_path)
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
                self._copy_to_unprocessed(file_path)

    def _copy_to_unprocessed(self, file_path: Path):
        self.unprocessed_folder.mkdir(exist_ok=True)
        shutil.copy2(file_path, self.unprocessed_folder / file_path.name)


# if __name__ == "__main__":
#     print("Running script")
#     src = LocalFileSource("/Users/srikotala/Documents/projects/ContractRepo")
#     count = 0
#     for doc in src.load_documents():
#         print(doc.title, doc.date, "Document:", count)
#         count += 1
#     print(f"There are {count} documents in this hierachy of folders!")
