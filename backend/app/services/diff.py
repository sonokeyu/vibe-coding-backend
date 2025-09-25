from __future__ import annotations

import difflib
from typing import Optional


def unified_diff(old: Optional[str], new: Optional[str], filename: str = "index.html") -> str:
    old_lines = (old or "").splitlines(keepends=True)
    new_lines = (new or "").splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "\n".join(diff)
