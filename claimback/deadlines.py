"""Escalation ladder: insurer grievance -> Bima Bharosa -> Insurance Ombudsman.

Day counts name their source and stay `confirmed: False` until checked against
the official text (see README, "Rule sources").
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

LIMITS = {
    "insurer_grievance_reply_days": {"value": 14, "source": "IRDAI grievance redressal rules (most sources: 14 days; one older page says 15)", "confirmed": False},
    "ombudsman_wait_days": {"value": 30, "source": "Insurance Ombudsman Rules 2017, as amended", "confirmed": False},
    "ombudsman_file_within_days": {"value": 365, "source": "Insurance Ombudsman Rules 2017, as amended", "confirmed": False},
    "ombudsman_max_claim_inr": {"value": 50_00_000, "source": "Insurance Ombudsman (Amendment) Rules 2023", "confirmed": False},
}


@dataclass
class Step:
    name: str
    due: date | None
    note: str


def ladder(grievance_sent: date, claim_amount_inr: int) -> list[Step]:
    v = {k: x["value"] for k, x in LIMITS.items()}
    reply_due = grievance_sent + timedelta(days=v["insurer_grievance_reply_days"])
    ombud_from = grievance_sent + timedelta(days=v["ombudsman_wait_days"])
    steps = [
        Step("Send grievance to insurer", grievance_sent, "Letter with citations and evidence pack"),
        Step("Insurer's reply due", reply_due, "Upload the reply; ClaimBack re-checks it"),
        Step("Escalate on Bima Bharosa if no fair reply", reply_due + timedelta(days=1), "IRDAI's grievance portal, text pre-filled"),
    ]
    if claim_amount_inr <= v["ombudsman_max_claim_inr"]:
        steps.append(Step("Ombudsman complaint can be filed", ombud_from,
                          f"Free; file within {v['ombudsman_file_within_days']} days of the insurer's final reply"))
    else:
        steps.append(Step("Claim above the Ombudsman limit", None, "Consumer commission route instead"))
    return steps


def to_ics(steps: list[Step]) -> str:
    """Calendar file with one all-day event per dated step."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ClaimBack//EN"]
    for i, s in enumerate(steps):
        if s.due is None:
            continue
        d = s.due.strftime("%Y%m%d")
        lines += ["BEGIN:VEVENT", f"UID:claimback-{d}-{i}", f"DTSTAMP:{d}T000000Z",
                  f"DTSTART;VALUE=DATE:{d}", f"SUMMARY:ClaimBack: {s.name}", f"DESCRIPTION:{s.note}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
