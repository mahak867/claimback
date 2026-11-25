"""Citation verifier: a quote is shown to the user only if it appears word for word
in its source. Whitespace, case, curly quotes and dashes are normalised first,
so OCR line breaks don't cause false failures, but words must match exactly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                            "–": "-", "—": "-", " ": " "})


def normalise(text: str) -> str:
    text = text.translate(_TRANSLATE).lower()
    # Hyphens are dropped on both sides, so "Non-\ndisclosure", "Non-disclo-\nsure" and
    # "Non-disclosure" all compare equal; every other character must still match.
    text = re.sub(r"-\s*\n\s*", "", text).replace("-", "")
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Citation:
    quote: str
    source_id: str
    verified: bool = False
    normalised_offset: int | None = None  # offset in normalise(source), not in the original text


def verify(citation: Citation, sources: dict[str, str]) -> Citation:
    source = sources.get(citation.source_id)
    if source is None:
        citation.verified, citation.normalised_offset = False, None
        return citation
    pos = normalise(source).find(normalise(citation.quote))
    citation.verified = pos >= 0 and len(normalise(citation.quote)) >= 12
    citation.normalised_offset = pos if citation.verified else None
    return citation


def verify_all(citations: list[Citation], sources: dict[str, str]) -> tuple[list[Citation], list[Citation]]:
    """Return (verified, rejected). The letter may only be released when rejected is empty."""
    checked = [verify(c, sources) for c in citations]
    return [c for c in checked if c.verified], [c for c in checked if not c.verified]
