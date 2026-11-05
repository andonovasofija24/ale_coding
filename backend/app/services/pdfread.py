"""Reading PDFs and pictures for the AI: the text of a PDF, or its pages as pictures (scanned task sheets, a
diagram exported from draw.io / StarUML, a photo of a drawing)."""
import io

from app.services import uploads

MAX_PAGES = 4
MAX_SIDE = 1800  # px: big enough to read small labels, small enough for the AI's limits


def pdf_text(data: bytes, max_pages: int = 20) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages[:max_pages]).strip()
    except Exception:
        return ""


def _png(im) -> bytes:
    im = im.convert("RGB")
    if max(im.size) > MAX_SIDE:
        r = MAX_SIDE / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def pdf_pages(data: bytes, max_pages: int = MAX_PAGES) -> list[bytes]:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(data)
    try:
        out = []
        for i in range(min(len(pdf), max_pages)):
            page = pdf[i]
            w, h = page.get_size()
            scale = min(2.5, MAX_SIDE / max(w, h, 1))
            out.append(_png(page.render(scale=scale).to_pil()))
        return out
    finally:
        pdf.close()


def images_for_ai(data: bytes, ctype: str) -> list[bytes]:
    """PNG pictures of the file (one per PDF page)."""
    if ctype == uploads.PDF:
        return pdf_pages(data)
    from PIL import Image
    return [_png(Image.open(io.BytesIO(data)))]
