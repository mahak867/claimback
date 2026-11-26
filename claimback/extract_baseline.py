"""Rule-based extraction baseline: regex and keyword rules, no model.

The fine-tuned ClaimBack model must beat these field-level scores
(tools/eval_extraction.py). It returns the same 11-key JSON as the model.
"""
from __future__ import annotations

import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}

GROUND_KEYWORDS = [
    ("fraud_misrepresentation", r"fraud|forged|fabricat|manipulat|misrepresent"),
    ("policy_not_in_force", r"lapse|not in force|grace period|premium (was )?not paid|non-payment"),
    ("waiting_period", r"waiting period"),
    ("non_disclosure_proposal", r"non-?disclosure|not disclosed|suppress|conceal"),
    ("pre_existing_disease", r"pre-?existing"),
    ("documents_not_submitted", r"documents?.{0,40}(not (been )?(submitted|received|provided))|non-?submission|pending documents"),
    ("hospitalisation_not_justified", r"not medically necessary|opd basis|did not (warrant|require) (hospitali|admission)|hospitali[sz]ation (was )?not (justified|required)"),
    ("amount_limited", r"sub-?limit|room rent|proportionate|capped|restricted to|deduct"),
    ("treatment_not_covered", r"not covered|not payable under|day-?care list|outside the scope"),
    ("excluded_by_clause", r"exclu"),
]

_DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), "dmy"),
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[ -]([A-Za-z]{3})[A-Za-z]*[ ,-]+(\d{4})\b"), "dMy"),
]


def _dates(text: str) -> list[tuple[int, date]]:
    found = []
    for pat, kind in _DATE_PATTERNS:
        for m in pat.finditer(text):
            try:
                if kind == "ymd":
                    d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                elif kind == "dmy":
                    d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                else:
                    mon = MONTHS.get(m.group(2).lower()[:3])
                    if not mon:
                        continue
                    d = date(int(m.group(3)), mon, int(m.group(1)))
                found.append((m.start(), d))
            except ValueError:
                continue
    return sorted(found)


def _near(text: str, words: str, dates: list[tuple[int, date]]) -> date | None:
    for m in re.finditer(words, text, re.I):
        after = [d for pos, d in dates if 0 <= pos - m.end() <= 60]
        if after:
            return after[0]
    return None


def _amount(text: str) -> int | None:
    m = re.search(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*(?:\.\d+)?)\s*(lakh|lac)?", text, re.I)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    return int(round(value * 100_000)) if m.group(2) else int(round(value))


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", re.sub(r"[ \t]+", " ", text)) if s.strip()]


def extract(letter: str) -> dict:
    low = letter.lower()
    dates = _dates(letter)
    ground = next((g for g, pat in GROUND_KEYWORDS if re.search(pat, low)), None)
    reason = next((s for s in _sentences(letter)
                   if re.search(r"repudiat|reject|not (admissible|payable)|declin|denied", s, re.I)), None)
    clause = re.search(r"((?:Clause|Section|Exclusion)\s+[\dA-Z][\w.()-]*)", letter)
    policy = re.search(r"Policy\s*(?:No\.?|Number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})", letter, re.I)
    insurer = re.search(r"([A-Z][A-Za-z&.\- ]{2,60}?(?:Insurance|Assurance|General|Health)(?: [A-Z][A-Za-z.]*)*(?: Co\.?| Company| Limited| Ltd\.?)?)", letter)
    claim_type = ("cashless" if re.search(r"cashless|pre-?auth", low)
                  else "partial_settlement" if re.search(r"partial|deduct", low)
                  else "reimbursement" if re.search(r"reimburs", low) else None)
    diag = re.search(r"(?:for|towards|treatment of|diagnosed with)\s+'?([A-Z][A-Za-z ()-]{3,60}?)'?\s+(?:at|from|in)\b", letter)
    return {
        "insurer_name": insurer.group(1).strip() if insurer else None,
        "policy_number": policy.group(1) if policy else None,
        "policy_inception_date": _iso(_near(letter, r"inception|commence|issued on|since|start date", dates)),
        "claim_type": claim_type,
        "claim_amount_inr": _amount(letter),
        "admission_date": _iso(_near(letter, r"admi|from", dates)),
        "discharge_date": _iso(_near(letter, r"discharg|\bto\b|till", dates)),
        "diagnosis": diag.group(1).strip() if diag else None,
        "rejection_ground": ground,
        "clause_cited": clause.group(1) if clause else None,
        "rejection_reason_quote": reason,
    }


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None
