"""Precedent finder: past Insurance Ombudsman awards on the same rejection reason.

Awards come in the format published by the Alei project
(https://github.com/Ashmit-rai17/alei, MIT): a header line
`===== AWARD n: <case id> (<claim type>; LLM label G1+G7) =====` then the award text.
Ranking is TF-IDF cosine similarity in plain Python, so this runs anywhere.
Outcomes are read from the decision text and reported as "not stated" when the
text has no decision, never guessed.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

# Alei taxonomy codes -> ClaimBack rejection grounds (see taxonomy.py).
ALEI_CODES = {
    "G1": "non_disclosure_proposal", "G2": "non_disclosure_revival", "G3": "fraud_misrepresentation",
    "G4": "policy_not_in_force", "G5": "documents_not_submitted", "G6": "excluded_by_clause",
    "G7": "pre_existing_disease", "G8": "waiting_period", "G9": "hospitalisation_not_justified",
    "G10": "treatment_not_covered", "G11": "amount_limited", "G12": "cause_outside_cover",
}
# Grounds argued the same way, so their awards are useful to each other.
RELATED = {
    "non_disclosure_proposal": {"non_disclosure_revival", "pre_existing_disease"},
    "non_disclosure_revival": {"non_disclosure_proposal"},
    "pre_existing_disease": {"non_disclosure_proposal", "waiting_period"},
    "waiting_period": {"pre_existing_disease"},
}

_HEADER = re.compile(r"^===== AWARD \d+: (?P<id>.+?) \((?P<kind>[^;]+); LLM label (?P<codes>[G0-9+]+)\) =====$", re.M)
_ALLOWED = re.compile(r"award is passed directing the insurer to pay|repudiation of the claim is unsustainable|"
                      r"insurer is directed to (pay|settle)|complaint is allowed|claim is allowed", re.I)
_PARTLY = re.compile(r"partly allowed|allowed partially|ex[- ]gratia", re.I)
_DISMISSED = re.compile(r"uphold the decision|rightly repudiated|complaint is dismissed|no further relief|"
                        r"not allowed|stands dismissed", re.I)


@dataclass
class Award:
    case_id: str
    claim_kind: str
    grounds: set[str]
    text: str

    @property
    def outcome(self) -> str:
        tail = self.text[-2500:]
        if _PARTLY.search(tail):
            return "partly allowed"
        if _ALLOWED.search(tail):
            return "allowed"
        if _DISMISSED.search(tail):
            return "dismissed"
        return "not stated"


@dataclass
class Match:
    award: Award
    score: float
    key_sentence: str


def parse_awards(text: str) -> list[Award]:
    heads = list(_HEADER.finditer(text))
    awards = []
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip()
        codes = {ALEI_CODES[c] for c in h.group("codes").split("+") if c in ALEI_CODES}
        awards.append(Award(h.group("id").strip(), h.group("kind").strip(), codes, body))
    return awards


def _tokens(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in _STOP]


_STOP = set("the and that was for with this from had has have were are not but which been his her she him their "
            "they its into than then there these those also any all per under such who whom whose shall would "
            "could should may can claim insurer policy complainant".split())


def _sentences(s: str) -> list[str]:
    flat = re.sub(r"\s+", " ", s)
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat) if len(x.split()) >= 6]


def find(ground: str, query: str, awards: list[Award], k: int = 3) -> list[Match]:
    """Awards on the same or a related ground, most similar to `query` first."""
    wanted = {ground} | RELATED.get(ground, set())
    pool = [a for a in awards if a.grounds & wanted]
    if not pool:
        return []
    docs = [Counter(_tokens(a.text)) for a in pool]
    df = Counter(t for d in docs for t in d)
    n = len(docs)

    def vec(c: Counter) -> dict[str, float]:
        return {t: (1 + math.log(f)) * math.log((n + 1) / (df.get(t, 0) + 1) + 1) for t, f in c.items()}

    def cos(a: dict, b: dict) -> float:
        dot = sum(v * b.get(t, 0.0) for t, v in a.items())
        na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    q = vec(Counter(_tokens(query)))
    qset = set(q)
    out = []
    for a, d in zip(pool, docs):
        exact = 0.1 if ground in a.grounds else 0.0  # prefer the same ground over a related one
        sents = _sentences(a.text)
        key = max(sents, key=lambda s: len(qset & set(_tokens(s))), default="")
        out.append(Match(a, cos(q, vec(d)) + exact, key))
    return sorted(out, key=lambda m: m.score, reverse=True)[:k]
