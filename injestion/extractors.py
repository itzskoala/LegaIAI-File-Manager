import csv
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import extract_msg
import html2text
import pandas as pd
from doc2docx import convert as convert_doc_to_docx
from docling.document_converter import DocumentConverter


class UnsupportedFileTypeError(Exception):
    pass


# Strategy pattern: every file type gets its own small class that knows how
# to turn a file into plain text. DocumentExtractor just picks the right one.
class ExtractionStrategy(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> str:
        pass


# docling does the heavy lifting for PDFs/DOCX/images: it figures out on its
# own whether a page needs OCR instead of us juggling pdfplumber + pytesseract
# + pdf2image by hand. One converter instance is reused across files since
# building it loads ML models, which is slow.
class DoclingExtractionStrategy(ExtractionStrategy):
    _converter = DocumentConverter()

    def extract(self, file_path: Path) -> str:
        result = self._converter.convert(str(file_path))
        return result.document.export_to_markdown()


# old binary .doc files aren't something docling can read directly, so we
# convert them to .docx first (doc2docx shells out to LibreOffice/Word) and
# then reuse the same docling strategy on the converted file.
class DocExtractionStrategy(ExtractionStrategy):
    def extract(self, file_path: Path) -> str:
        with tempfile.TemporaryDirectory() as tmp_dir:
            convert_doc_to_docx(str(file_path), tmp_dir)
            converted_path = Path(tmp_dir) / (file_path.stem + ".docx")
            return DoclingExtractionStrategy().extract(converted_path)


class TextExtractionStrategy(ExtractionStrategy):
    def extract(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8", errors="ignore")


class MsgExtractionStrategy(ExtractionStrategy):
    def extract(self, file_path: Path) -> str:
        msg = extract_msg.openMsg(str(file_path))

        return (
            f"From: {msg.sender}\n"
            f"Date: {msg.date}\n"
            f"Subject: {msg.subject}\n"
            f"{'-' * 40}\n"
            f"Body:\n{msg.body}"
        )


class XlsxExtractionStrategy(ExtractionStrategy):
    def extract(self, file_path: Path) -> str:
        return pd.read_excel(file_path).to_string(index=False)


class CsvExtractionStrategy(ExtractionStrategy):
    def extract(self, file_path: Path) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return "\n".join(", ".join(row) for row in csv.reader(f))


class HtmlExtractionStrategy(ExtractionStrategy):
    def extract(self, file_path: Path) -> str:
        converter = html2text.HTML2Text()
        converter.ignore_links = False

        html = file_path.read_text(encoding="utf-8", errors="ignore")
        return converter.handle(html)
