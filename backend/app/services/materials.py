"""Course materials: what may be uploaded, and turning presentations into PDF so they open in the browser."""
import asyncio
import os
import shutil
import subprocess
import tempfile

from fastapi import HTTPException, UploadFile

from app.services import uploads

MAX = 60 * uploads.MB
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # old binary Office files (.ppt, .doc)
PPT = "application/vnd.ms-powerpoint"


async def read_material(file: UploadFile) -> tuple[bytes, str]:
    data = await uploads.read_limited(file, MAX)
    if data.startswith(OLE):
        return data, PPT
    t = uploads.detect_document(data)
    if t in (None, uploads.TEXT, uploads.PNG, uploads.JPEG):
        raise HTTPException(status_code=422, detail="Upload a PDF or a presentation / document (PowerPoint, Word, LibreOffice)")
    return data, t


def soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def _convert(data: bytes, name: str) -> bytes | None:
    exe = soffice()
    if exe is None:
        return None
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "input" + os.path.splitext(name)[1].lower()[:6])
        with open(src, "wb") as f:
            f.write(data)
        # a private profile per run: parallel conversions don't collide, and nothing is kept
        cmd = [exe, f"-env:UserInstallation=file://{d}/profile", "--headless", "--norestore", "--convert-to", "pdf",
               "--outdir", d, src]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return None
        out = os.path.join(d, "input.pdf")
        if os.path.exists(out):
            with open(out, "rb") as f:
                return f.read()
    return None


async def to_pdf(data: bytes, name: str) -> bytes | None:
    """A PDF version of a presentation / document (None if LibreOffice isn't installed or it failed)."""
    return await asyncio.to_thread(_convert, data, name)
