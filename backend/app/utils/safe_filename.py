"""Sanitize untrusted upload filenames (path traversal, control chars)."""

import re
from typing import Optional

# Allow common document name characters only
_SAFE_NAME = re.compile(r"^[\w.\- ()\[\]]+$")


def sanitize_upload_filename(name: Optional[str], max_len: int = 255) -> str:
    """
    Return a basename-only, filesystem-safe filename for metadata/logging.

    Strips path components (e.g. ../../etc/passwd -> passwd).
    """
    if not name or not str(name).strip():
        return "upload.bin"

    # Normalize separators; take basename only (blocks path traversal)
    base = str(name).replace("\\", "/").split("/")[-1].strip()
    if not base:
        return "upload.bin"

    # Remove null bytes and other control characters
    base = "".join(c for c in base if ord(c) >= 32 and c not in "\x7f")

    # If still suspicious, reduce to alnum + limited punctuation
    if not _SAFE_NAME.match(base):
        ext = ""
        if "." in base:
            ext = "." + base.rsplit(".", 1)[-1][:16]
            ext = re.sub(r"[^a-zA-Z0-9.]", "", ext)
        safe_core = re.sub(r"[^a-zA-Z0-9_-]+", "_", base.rsplit(".", 1)[0])[:200]
        base = (safe_core or "upload") + (ext if ext else "")

    return base[:max_len] if base else "upload.bin"
