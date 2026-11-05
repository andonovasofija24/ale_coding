"""
Uploaded files (document and project submissions, teachers' reference solutions).

Safety rules
  - the type is decided by the file's content (magic bytes / zip structure), never by its name or the type the
    browser claims; anything else is refused
  - size limits are enforced while reading (a huge upload is cut off, not read into memory)
  - zips are only ever *read* for viewing — never extracted to disk, never executed; entries with absolute
    paths, "..", or symlinks are refused, and the number/total size of entries is limited (zip bombs)
  - files are served with Content-Disposition and nosniff, so a browser never runs them as a page
"""
import io
import re
import unicodedata
import zipfile
from urllib.parse import quote

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response

MB = 1024 * 1024
LIMITS = {"document": 20 * MB, "project": 50 * MB}
ZIP_MAX_ENTRIES = 3000
ZIP_MAX_TOTAL = 300 * MB          # uncompressed
VIEW_MAX = 1 * MB                 # largest file shown as text in the browser

PDF, PNG, JPEG, ZIP = "application/pdf", "image/png", "image/jpeg", "application/zip"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ODT, ODP, ODG = ("application/vnd.oasis.opendocument.text", "application/vnd.oasis.opendocument.presentation",
                 "application/vnd.oasis.opendocument.graphics")
TEXT = "text/plain"


async def read_limited(file: UploadFile, limit: int) -> bytes:
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit:
            raise HTTPException(status_code=413, detail=f"The file is larger than {limit // MB} MB")
    if not buf:
        raise HTTPException(status_code=422, detail="The file is empty")
    return bytes(buf)


def _zip(data: bytes) -> zipfile.ZipFile | None:
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None


def _office_type(zf: zipfile.ZipFile) -> str | None:
    names = set(zf.namelist())
    if "[Content_Types].xml" in names:
        if any(n.startswith("word/") for n in names):
            return DOCX
        if any(n.startswith("ppt/") for n in names):
            return PPTX
        if any(n.startswith("xl/") for n in names):
            return XLSX
    if "mimetype" in names:
        mt = zf.read("mimetype")[:100].decode("ascii", "ignore").strip()
        return {ODT: ODT, ODP: ODP, ODG: ODG}.get(mt)
    return None


def _is_text(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def detect_document(data: bytes) -> str | None:
    """PDF, PNG/JPEG picture, Word/PowerPoint/Excel/LibreOffice document, or plain text (e.g. .drawio, .puml, .md)."""
    if data.startswith(b"%PDF-"):
        return PDF
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data.startswith(b"PK"):
        zf = _zip(data)
        return _office_type(zf) if zf else None
    if _is_text(data):
        return TEXT
    return None


def check_project_zip(data: bytes) -> zipfile.ZipFile:
    zf = _zip(data)
    if zf is None or not data.startswith(b"PK"):
        raise HTTPException(status_code=422, detail="Upload the project as a .zip file")
    infos = zf.infolist()
    if len(infos) > ZIP_MAX_ENTRIES:
        raise HTTPException(status_code=422, detail="The zip has too many files")
    if sum(i.file_size for i in infos) > ZIP_MAX_TOTAL:
        raise HTTPException(status_code=422, detail="The zip is too large when unpacked")
    for i in infos:
        name = i.filename.replace("\\", "/")
        if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or ".." in name.split("/"):
            raise HTTPException(status_code=422, detail="The zip contains unsafe paths")
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            raise HTTPException(status_code=422, detail="The zip contains links")
    return zf


async def read_checked(file: UploadFile, kind: str) -> tuple[bytes, str]:
    """(bytes, content type) of an upload for a "document" or "project" task, or an HTTP error."""
    data = await read_limited(file, LIMITS[kind])
    if kind == "project":
        check_project_zip(data)
        return data, ZIP
    t = detect_document(data)
    if t is None:
        raise HTTPException(status_code=422, detail="Use a PDF, Word, PowerPoint, LibreOffice, picture or text file")
    return data, t


def safe_name(name: str | None) -> str:
    base = (name or "file").replace("\\", "/").rsplit("/", 1)[-1]
    base = unicodedata.normalize("NFC", base)
    base = re.sub(r"[\x00-\x1f\"<>|:*?]", "_", base).strip(" .") or "file"
    return base[:200]


def file_response(data: bytes, content_type: str, name: str, inline: bool = False) -> Response:
    # Only PDFs and pictures may be shown inline (they can't run scripts in the app's origin when sandboxed by the
    # browser's viewer); everything else is always a download.
    disp = "inline" if inline and content_type in (PDF, PNG, JPEG) else "attachment"
    return Response(content=data, media_type=content_type, headers={
        "Content-Disposition": f"{disp}; filename*=UTF-8''{quote(name)}",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
        "Cache-Control": "private, no-store",
    })


# ---------------------------------------------------------------------------
# Project zips: listing and reading single files (for the review page)
# ---------------------------------------------------------------------------

def zip_tree(data: bytes) -> list[dict]:
    zf = check_project_zip(data)
    return [{"path": i.filename.replace("\\", "/"), "size": i.file_size}
            for i in zf.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]


def zip_entry(data: bytes, path: str) -> dict:
    zf = check_project_zip(data)
    info = next((i for i in zf.infolist() if i.filename.replace("\\", "/") == path and not i.is_dir()), None)
    if info is None:
        raise HTTPException(status_code=404, detail="File not found in the zip")
    if info.file_size > VIEW_MAX:
        return {"path": path, "size": info.file_size, "text": None, "reason": "too_large"}
    with zf.open(info) as f:
        raw = f.read(VIEW_MAX + 1)
    if not _is_text(raw):
        try:  # Windows-1251 (Cyrillic) source files from older editors
            if b"\x00" not in raw:
                return {"path": path, "size": info.file_size, "text": raw.decode("cp1251"), "reason": None}
        except UnicodeDecodeError:
            pass
        return {"path": path, "size": info.file_size, "text": None, "reason": "binary"}
    return {"path": path, "size": info.file_size, "text": raw.decode("utf-8"), "reason": None}
