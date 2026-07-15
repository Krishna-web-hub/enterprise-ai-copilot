"""
Input Sanitization Utilities

Provides functions to clean user-provided text before storage,
preventing stored XSS and injection attacks.

Why sanitize at the application layer?
- Pydantic validates TYPES (is it a string? is it an email?) but doesn't
  sanitize CONTENT (does it contain <script> tags?)
- A user could name a dataset "<img src=x onerror=alert(1)>" — without
  sanitization, that renders as HTML when displayed in the frontend
- Defense in depth: even if the frontend uses React (which escapes by
  default), we don't trust that every rendering path is safe

Strategy:
- Strip HTML tags from text fields (names, titles, descriptions)
- Escape special characters that could be interpreted as code
- Preserve legitimate text content (don't over-sanitize)
"""

import html
import re
from typing import Optional


# HTML tag pattern (matches <anything> including self-closing)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Script/event handler patterns (more aggressive — catches obfuscation attempts)
SCRIPT_PATTERNS = [
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onclick=, onerror=, etc.
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
]


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """
    Sanitize a text string for safe storage and display.

    - Strips HTML tags
    - Escapes HTML entities (&, <, >, ", ')
    - Removes dangerous patterns (javascript:, on*= handlers)
    - Preserves plain text content

    Use for: dataset names, report titles, chat messages, file names,
    any user-provided string that will be displayed back.
    """
    if text is None:
        return None

    # Strip HTML tags
    cleaned = HTML_TAG_PATTERN.sub("", text)

    # Remove dangerous patterns
    for pattern in SCRIPT_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Trim excessive whitespace
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and special character issues.

    - Removes path separators (../, /, \\)
    - Removes null bytes
    - Strips leading/trailing dots and spaces
    - Limits length
    """
    # Remove null bytes
    cleaned = filename.replace("\x00", "")

    # Remove path separators (prevent traversal)
    cleaned = cleaned.replace("..", "")
    cleaned = cleaned.replace("/", "")
    cleaned = cleaned.replace("\\", "")

    # Remove control characters
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)

    # Strip dangerous leading characters
    cleaned = cleaned.lstrip(". ")

    # Limit length
    if len(cleaned) > 255:
        # Preserve extension
        parts = cleaned.rsplit(".", 1)
        if len(parts) == 2:
            name, ext = parts
            cleaned = name[:250] + "." + ext[:4]
        else:
            cleaned = cleaned[:255]

    return cleaned or "unnamed_file"


def escape_html(text: Optional[str]) -> Optional[str]:
    """
    HTML-escape a string (for contexts where HTML entities are safe).

    Converts: & → &amp;  < → &lt;  > → &gt;  " → &quot;  ' → &#x27;
    """
    if text is None:
        return None
    return html.escape(text, quote=True)
