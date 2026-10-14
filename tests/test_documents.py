import pytest
import pymupdf

from connectors.documents import extract_uploaded_document


class Upload:
    def __init__(self, name, data):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


def test_text_pdf_extracts_embedded_text():
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Python programming course certificate completed")
    data = doc.tobytes()
    doc.close()

    result = extract_uploaded_document(Upload("certificate.pdf", data))

    assert "Python programming course certificate completed" in result
    assert "embedded text" in result


def test_image_only_pdf_attempts_ocr_or_gives_setup_guidance(monkeypatch):
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()

    # A blank page should either produce a useful OCR setup/error message or no-text result.
    with pytest.raises(ValueError) as exc_info:
        extract_uploaded_document(Upload("scanned.pdf", data))
    assert any(word in str(exc_info.value).lower() for word in ("ocr", "readable text", "tesseract"))


def test_txt_file_extracts_text():
    result = extract_uploaded_document(Upload("certificate.txt", b"Completed C Programming Fundamentals"))
    assert result == "Completed C Programming Fundamentals"


def test_unsupported_file_type_rejected():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_uploaded_document(Upload("certificate.docx", b"not a pdf"))
