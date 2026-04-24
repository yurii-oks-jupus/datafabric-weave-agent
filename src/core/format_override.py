"""User-requested output-format detection (FAB-2101 Sprint 3.3.4).

The LLM is instructed to emit JSON matching a schema by default. When a user
explicitly asks for a different format, we skip the schema instruction for
that turn so the model can honour the ask (markdown table, prose, CSV, etc.).

Detection is intentionally keyword-based, not LLM-based — an extra round-trip
to detect format intent would defeat the latency win of Sprint 3.1.
"""

from __future__ import annotations

import re

_FORMAT_WORDS = r"(json|table|markdown|md|csv|tsv|list|prose|text|bullet\s*s?|yaml|xml)"

_OVERRIDE_PATTERNS = [
    re.compile(rf"\bas\s+(a\s+)?{_FORMAT_WORDS}\b", re.I),
    re.compile(r"\bformat(?:ted)?\s+as\b", re.I),
    re.compile(rf"\bin\s+{_FORMAT_WORDS}\b", re.I),
    re.compile(rf"\bgive\s+me\s+(a\s+)?{_FORMAT_WORDS}\b", re.I),
    re.compile(rf"\bshow\s+(?:me\s+)?(?:as|in)\s+{_FORMAT_WORDS}\b", re.I),
    re.compile(rf"\boutput\s+(?:as|in)\s+{_FORMAT_WORDS}\b", re.I),
    re.compile(rf"\breturn\s+(?:as|in)\s+{_FORMAT_WORDS}\b", re.I),
]


def detects_format_override(message: str) -> bool:
    """Return True if `message` contains a recognisable output-format request."""
    return any(p.search(message) for p in _OVERRIDE_PATTERNS)
