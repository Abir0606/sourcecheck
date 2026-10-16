"""OCR adapter. Disabled by default; Tesseract used when available."""
from __future__ import annotations

import abc


class OcrProvider(abc.ABC):
    available: bool = False

    @abc.abstractmethod
    def extract(self, fileobj, *, content_type: str) -> list[tuple[int, str]]:
        """Return a list of (page_number, text). Page numbers are 1-based."""
        ...


class NullOcr(OcrProvider):
    available = False

    def extract(self, fileobj, *, content_type: str):
        return []


class TesseractOcr(OcrProvider):
    available = True

    def __init__(self, cmd: str):
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = cmd
        self._t = pytesseract

    def extract(self, fileobj, *, content_type: str):

        from pdf2image import convert_from_bytes

        data = fileobj.read() if hasattr(fileobj, "read") else fileobj
        images = convert_from_bytes(data)
        results: list[tuple[int, str]] = []
        for idx, image in enumerate(images, start=1):
            try:
                text = self._t.image_to_string(image)
            except Exception:
                text = ""
            results.append((idx, text.strip()))
        return results
