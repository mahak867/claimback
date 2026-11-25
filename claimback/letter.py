"""Grievance letter builder. Refuses to produce a letter while any citation is unverified."""
from __future__ import annotations

from .citations import Citation, verify_all
from .rules import Ground


def inr(n: int) -> str:
    """Indian digit grouping: 246500 -> 2,46,500."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
    return f"{head},{tail}"


class UnverifiedCitations(Exception):
    def __init__(self, rejected: list[Citation]):
        self.rejected = rejected
        super().__init__(f"{len(rejected)} citation(s) not found in their sources")


def grievance_letter(*, insurer: str, policy_no: str, name: str, claim_inr: int, treatment: str,
                     rejection_date: str, grounds: list[Ground], citations: list[Citation],
                     sources: dict[str, str]) -> str:
    verified, rejected = verify_all(citations, sources)
    if rejected:
        raise UnverifiedCitations(rejected)
    amount = f"Rs {inr(claim_inr)}"
    body = [
        "To the Grievance Redressal Officer,",
        insurer,
        "",
        f"Subject: Grievance against repudiation of claim under Policy No. {policy_no}, dated {rejection_date}",
        "",
        f"I write to contest the repudiation of my claim of {amount} for {treatment}.",
        "",
    ]
    for i, g in enumerate(grounds, 1):
        body += [f"{i}. {g.letter or g.explanation}", ""]
    body += [
        "I request that you withdraw the repudiation, settle the claim in full within the timeline "
        "required by IRDAI, and send me a copy of the complete claim file and the documents relied on.",
        "",
        "Yours faithfully,",
        name,
        "",
        "Sources quoted:",
    ]
    body += [f"[{i}] {c.source_id}: \"{c.quote}\"" for i, c in enumerate(verified, 1)]
    return "\n".join(body)
