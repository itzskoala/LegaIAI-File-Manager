import os
import csv
import logging
import pdfplumber
import pytesseract
import datetime
import hashlib
import extract_msg
import zipfile
import subprocess
import tempfile
import shutil
import pandas as pd
import html2text

logging.getLogger("pdfminer").setLevel(logging.ERROR)

from pathlib import Path
from PIL import Image
from docx import Document
from pdf2image import convert_from_path

from FileManager import DocumentSource
from FileManager import DocumentRecord


class UnsupportedFileTypeError(Exception):
    pass


class LocalFileSource(DocumentSource):
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        # self.arr = []
        # sibling folder next to the source — avoids rglob picking up the copies on the next run
        self.unprocessed_folder = Path(folder_path).parent / (Path(folder_path).name + "_unprocessed")

    TEXT_DENSITY_THRESHOLD = 50  # chars per page below which we fall back to OCR
    PDF_DPI = 300

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
                        yield extracted_doc
                continue

            try:
                content = LocalFileSource.extract_text_from_file(str(file_path))
                yield DocumentRecord(
                    source_type="local_file",
                    source_id=str(file_path),
                    title=file_path.name,
                    content=content,
                    date=datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                )
            except UnsupportedFileTypeError:
                print(f"  [SKIP] {file_path.name}")
                # self.arr.append(file_path.name)
                self.unprocessed_folder.mkdir(exist_ok=True)
                shutil.copy2(file_path, self.unprocessed_folder / file_path.name)
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
                # self.arr.append(file_path.name)
                self.unprocessed_folder.mkdir(exist_ok=True)
                shutil.copy2(file_path, self.unprocessed_folder / file_path.name)

    # def deduplicate(self):
    #     # a potential function to handle duplicate files
    #     #probably have to use a hash on each content and then iterate over each file to delete
    #     # oh lol this is python so it's easier with a set (set of hashes) , delete the match
    #     def calculate_file_hash(file_path):
    #         """Calculates the hash value of a file's content."""
    #         hasher = hashlib.md5()
    #         with open(file_path, 'rb') as file:
    #             for chunk in iter(lambda: file.read(4096), b''):
    #                 hasher.update(chunk)
    #         return hasher.hexdigest()
        
    #     def find_duplicate_files(root_folder):
    #         #probably going to have to yield things...
    #         #use a generator to speed this up...

    #         """Traverses through the root folder and identifies duplicate files."""
    #         duplicates = {}
    #         for folder_path, _, file_names in os.walk(root_folder):
    #             for file_name in file_names:
    #                 file_path = os.path.join(folder_path, file_name)
    #                 file_hash = calculate_file_hash(file_path)
    #                 if file_hash in duplicates:
    #                     duplicates[file_hash].append(file_path)
    #                 else:
    #                     duplicates[file_hash] = [file_path]
    #         return duplicates

    #     def remove_duplicate_files(duplicates):
    #         """Removes duplicate files from the file system."""
    #         for file_paths in duplicates.values():
    #             if len(file_paths) > 1:
    #                 print(f"Duplicate files found:\n{file_paths}\n")
    #                 for file_path in file_paths[1:]:
    #                     os.remove(file_path)
    #                     print(f"{file_path} has been deleted.\n")

    #     duplicates = find_duplicate_files(self.folder_path)
    #     remove_duplicate_files(duplicates)


    @staticmethod 
    #https://www.geeksforgeeks.org/python/python-staticmethod-function/
    #this function is a utlity function so it doesn't need to modify the state of the class or instances
    #static methods are useful in situations where a function is logically related to a class but does not require access to instance-specific data
    def extract_text_from_pdf(file_path: str) -> str:
        """
        Extract text from a PDF.
        Uses pdfplumber for digital text; falls back to pytesseract on low-density pages.
        """
        final_pages = []

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""

                if len(text.strip()) < LocalFileSource.TEXT_DENSITY_THRESHOLD:
                    print(f"  [OCR] {Path(file_path).name} page {i + 1}: low text density, running OCR...")
                    images = convert_from_path(file_path, first_page=i + 1, last_page=i + 1, dpi=LocalFileSource.PDF_DPI)
                    if images:
                        text = pytesseract.image_to_string(images[0])
                        # print(text)

                final_pages.append(text)

        return "\n\n--- PAGE BREAK ---\n\n".join(final_pages)

    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        """
        Dispatch to the right extractor based on file extension.
        Raises UnsupportedFileTypeError for unrecognized types.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            return LocalFileSource.extract_text_from_pdf(file_path)

        elif ext == ".docx":
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        
        elif ext == ".doc":  #have the convert old MS word files to .docx typing
            result = subprocess.run(["antiword", file_path], capture_output=True, text=True)
            if result.returncode != 0:
                raise UnsupportedFileTypeError(f"antiword failed on {path.name}: {result.stderr.strip()}")
            return result.stdout

        elif ext in (".txt", ".md", ".rst"):
            return path.read_text(encoding="utf-8")

        elif ext == ".msg":
            msg = extract_msg.openMsg(path)
            # Extract email metadata and body
            email_subject = msg.subject
            email_sender = msg.sender
            email_date = msg.date
            email_body = msg.body  # This holds the plain text content

            text_content = f"From: {email_sender}\n"
            text_content += f"Date: {email_date}\n"
            text_content += f"Subject: {email_subject}\n"
            text_content += f"{'-'*40}\n"
            text_content += f"Body:\n{email_body}"

            return text_content

        elif ext == ".xlsx":
            return pd.read_excel(path).to_string(index=False)
                
        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                return "\n".join(", ".join(row) for row in csv.reader(f))

        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
            return LocalFileSource.extract_text_from_image(file_path)

        elif ext == ".html":
            converter = html2text.HTML2Text()
            converter.ignore_links = False  # Keep links in Markdown format

            # Convert to formatted text
            formatted_text = converter.handle(path.read_text(encoding="utf-8"))
            return formatted_text
        else:
            raise UnsupportedFileTypeError(f"No extractor for: {ext} ({path.name})")
        

if __name__ == "__main__":
    print("Running script")
    src = LocalFileSource("/Users/srikotala/Documents/projects/ContractRepo")
    count = 0
    for doc in src.load_documents():
        print(doc.title, doc.date, "Document:", count)
        count+=1 
    print(f'There are {count} documents in this hierachy of folders! ')
    