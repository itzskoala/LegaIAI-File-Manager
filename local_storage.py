import os
import csv
import pdfplumber
import pytesseract

from pathlib import Path
from PIL import Image
from docx import Document
from pdf2image import convert_from_path


class UnsupportedFileTypeError(Exception):
    pass


TEXT_DENSITY_THRESHOLD = 50  # chars per page below which we fall back to OCR
PDF_DPI = 300


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF.
    Uses pdfplumber for digital text; falls back to pytesseract on low-density pages.
    """
    final_pages = []

    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            if len(text.strip()) < TEXT_DENSITY_THRESHOLD:
                print(f"  [OCR] {Path(file_path).name} page {i + 1}: low text density, running OCR...")
                images = convert_from_path(file_path, first_page=i + 1, last_page=i + 1, dpi=PDF_DPI) #saves as an image 
                if images:
                    text = pytesseract.image_to_string(images[0]) #converts that img to txt

            final_pages.append(text)

    return "\n\n--- PAGE BREAK ---\n\n".join(final_pages)


def extract_text_from_image(file_path: str) -> str:
    img = Image.open(file_path)
    return pytesseract.image_to_string(img)


def extract_text_from_file(file_path: str) -> str:
    """
    Dispatch to the right extractor based on file extension.
    Raises UnsupportedFileTypeError for unrecognized types.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)

    elif ext == ".docx":
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    elif ext in (".txt", ".md", ".rst"):
        return path.read_text(encoding="utf-8")

    elif ext == ".csv":
        with open(file_path, "r", encoding="utf-8") as f:
            return "\n".join(", ".join(row) for row in csv.reader(f))

    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
        return extract_text_from_image(file_path)

    else:
        raise UnsupportedFileTypeError(f"No extractor for: {ext} ({path.name})")


class LocalFiles:
    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)

    def locate_files(self) -> list[Path]:
        return [
            p for p in self.folder_path.rglob("*")
            if p.is_file() and p.name != ".DS_Store"
        ]

    def extract_all(self) -> dict[str, str]:
        results = {}

        for file_path in self.locate_files():
            try:
                results[str(file_path)] = extract_text_from_file(str(file_path))
            except UnsupportedFileTypeError as e:
                results[str(file_path)] = f"SKIPPED: {e}"
            except Exception as e:
                results[str(file_path)] = f"ERROR: {e}"

        return results