"""Extract plain text from uploaded solution materials (PDF / DOCX / text)."""
import io


def extract(raw: bytes, content_type: str | None, filename: str | None) -> str:
    name = (filename or "").lower()
    ct = (content_type or "").lower()

    if name.endswith(".pdf") or "pdf" in ct:
        return _from_pdf(raw)
    if name.endswith(".docx") or "word" in ct or "officedocument" in ct:
        return _from_docx(raw)
    # default: treat as utf-8 text/markdown/html
    return raw.decode("utf-8", errors="ignore")


def _from_pdf(raw: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _from_docx(raw: bytes) -> str:
    import docx

    doc = docx.Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs)
