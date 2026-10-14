"""Document ingestion for text-based and scanned PDFs.

Text-based PDFs use embedded text first. If a PDF is image-only, the connector
tries OCR with PyMuPDF + the locally installed Tesseract OCR engine. If OCR is
not available, it gives clear setup instructions instead of silently failing.
"""

import io
import os
import pymupdf

MAX_DOCUMENT_CHARS = 80_000
MIN_EMBEDDED_TEXT_CHARS = 20


def _ocr_page(page, page_number):
    """OCR a scanned PDF page using Tesseract when installed."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise ValueError(
            "This PDF appears to be scanned (image-only), so it needs OCR. "
            "Install the Python packages with `python -m pip install -r requirements.txt`, "
            "then install the Tesseract OCR application for Windows. "
            "See README.md → OCR for scanned PDFs. You can also use a text-based PDF."
        ) from exc

    # Optional override for installations where Tesseract is not on PATH:
    # TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        result = pytesseract.image_to_string(image, lang="eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "OCR is enabled in Skill Passport, but the Tesseract OCR application "
            "was not found. Install Tesseract for Windows, restart VS Code, and retry. "
            "If it is installed outside PATH, set TESSERACT_CMD in your .env file. "
            "See README.md → OCR for scanned PDFs."
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"OCR could not read page {page_number}. Check that Tesseract is installed "
            "and English language data is available."
        ) from exc
    return result.strip()


def extract_uploaded_document(uploaded_file):
    """Extract text from PDF, TXT or Markdown uploads, using OCR for scanned PDFs."""
    name = str(getattr(uploaded_file, "name", "uploaded document")).lower()
    data = uploaded_file.getvalue()

    if name.endswith(".pdf"):
        text_parts = []
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.page_count == 0:
                raise ValueError("This PDF contains no pages.")

            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                if len(page_text) >= MIN_EMBEDDED_TEXT_CHARS:
                    text_parts.append(f"[Page {page_number} · embedded text]\n{page_text}")
                else:
                    ocr_text = _ocr_page(page, page_number)
                    if ocr_text:
                        text_parts.append(f"[Page {page_number} · OCR extracted]\n{ocr_text}")

        text = "\n\n".join(text_parts).strip()
        if not text:
            raise ValueError(
                "No readable text could be extracted from this PDF, even with OCR. "
                "Try a clearer scan or enter the relevant details manually. "
                "OCR text should be reviewed for mistakes before it is used as evidence."
            )
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace").strip()
    else:
        raise ValueError("Unsupported file type. Use PDF, TXT or MD.")

    if not text:
        raise ValueError("The document contains no readable text.")
    return text[:MAX_DOCUMENT_CHARS]
