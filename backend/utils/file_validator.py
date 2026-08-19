"""File validation: extension whitelist plus content signature sniffing.

Extension checks alone are unreliable because attackers control filenames.
For audio uploads we additionally sniff the first bytes of the file so a
renamed binary cannot pass validation, and so clearly-corrupt uploads fail
fast before being sent to the transcription service.
"""

from pathlib import Path

from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def safe_filename(filename: str) -> str:
    return secure_filename(filename)


def _header_bytes(path: Path, length: int = 12) -> bytes:
    with open(path, "rb") as handle:
        return handle.read(length)


def _sniffs_mp3(header: bytes) -> bool:
    return header[:3] == b"ID3" or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0)


def _sniffs_wav(header: bytes) -> bool:
    return header[:4] == b"RIFF" and header[8:12] == b"WAVE"


def _sniffs_m4a(header: bytes) -> bool:
    return header[4:8] == b"ftyp"


def has_valid_signature(filepath) -> bool:
    """Return True if the file content matches an allowed audio container."""
    path = Path(filepath)
    if not path.is_file() or path.stat().st_size < 12:
        return False
    header = _header_bytes(path)
    return _sniffs_mp3(header) or _sniffs_wav(header) or _sniffs_m4a(header)