"""End-to-end run on the prototype's fictional case:  python -m claimback.demo

Facts are hard-coded here; in the product they come from the model's extraction step.
"""
from datetime import date

from .citations import Citation
from .deadlines import ladder
from .letter import grievance_letter
from .rules import Case, run_rules, strength

SOURCES = {
    "rejection_letter": (
        "We refer to your cashless request towards Coronary Angioplasty. Your claim stands "
        "repudiated under Clause 7.3 (Non-disclosure of material facts) as the insured was "
        "found to be suffering from Hypertension prior to policy inception, which was not "
        "disclosed in the proposal form."
    ),
    "renewal_certificate": "Policy continuously renewed without break since 12/04/2019. Cumulative bonus: 50%.",
    "pre_policy_check": "BP 128/82. No abnormalities detected. Accepted at standard rates.",
}


def main() -> None:
    case = Case(policy_inception=date(2019, 4, 12), continuous_cover=True, admission=date(2026, 8, 14),
                rejection_ground="non_disclosure_proposal", pre_policy_check_normal=True)
    grounds = run_rules(case)
    print(f"Case strength: {strength(grounds)}  ({len(grounds)} grounds)\n")
    citations = [
        Citation("stands repudiated under Clause 7.3 (Non-disclosure of material facts)", "rejection_letter"),
        Citation("Policy continuously renewed without break since 12/04/2019", "renewal_certificate"),
        Citation("No abnormalities detected. Accepted at standard rates.", "pre_policy_check"),
    ]
    print(grievance_letter(insurer="Suraksha General Insurance Ltd (fictional)", policy_no="SGI/HL/2019/448213",
                           name="Meena S.", claim_inr=246500, treatment="coronary angioplasty (14-19 August 2026)",
                           rejection_date="02/09/2026", grounds=grounds, citations=citations, sources=SOURCES))
    print("\nEscalation plan:")
    for s in ladder(date(2026, 11, 25), 246500):
        print(f"  {str(s.due or '-'):>10}  {s.name}  ({s.note})")


if __name__ == "__main__":
    main()
