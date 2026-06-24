from pathlib import Path

from .extractors import (
    CsvExtractionStrategy,
    DocExtractionStrategy,
    DoclingExtractionStrategy,
    HtmlExtractionStrategy,
    MsgExtractionStrategy,
    TextExtractionStrategy,
    UnsupportedFileTypeError,
    XlsxExtractionStrategy,
)

class DocumentExtractor:
    def extract(self, file_path: str | Path) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()
        strategy = self._strategy_for(ext, path)
        return strategy.extract(path)

    # Each case picks the strategy object that knows how to read that
    # file type; the underscore "_" case is the default/no-match fallback.
    def _strategy_for(self, ext: str, path: Path):
        match ext:
            case ".pdf" | ".docx" | ".pptx":
                return DoclingExtractionStrategy()
            case ".doc":
                return DocExtractionStrategy()
            case ".png" | ".jpg" | ".jpeg" | ".webp" | ".bmp" | ".tiff":
                return DoclingExtractionStrategy()
            case ".txt" | ".md" | ".rst":
                return TextExtractionStrategy()
            case ".msg":
                return MsgExtractionStrategy()
            case ".xlsx":
                return XlsxExtractionStrategy()
            case ".csv":
                return CsvExtractionStrategy()
            case ".html":
                return HtmlExtractionStrategy()
            case _:
                raise UnsupportedFileTypeError(f"No extractor for: {ext} ({path.name})")
