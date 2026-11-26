"""Deterministic IRDAI rule checks. No model calls in here.

Each rule takes the case facts and returns a Ground (an argument for appeal)
or None. Every numeric limit lives in RULES with the document it comes from,
so a reviewer can check each one against the official text.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Each limit names its source. `confirmed` flips to True once a team member
# has read the clause in the official document and filled in `clause`.
RULES = {
    "moratorium_months": {
        "value": 60,
        "source": "IRDAI Master Circular on Health Insurance Business, 29 May 2024",
        "clause": "Chapter I, para 13 (p.22): no claim contestable for non-disclosure or misrepresentation "
                  "except established fraud after 60 months of continuous coverage; ported and migrated "
                  "credits count. Sum-insured increases and permanent exclusions: Master Circular on "
                  "Protection of Policyholders' Interests 2024, customer information sheet (p.196)",
        "confirmed": True,
    },
    "ped_max_wait_months": {
        "value": 36,
        "source": "IRDAI (Insurance Products) Regulations 2024; IRDAI Health Department page (irdai.gov.in/health-dept)",
        "clause": "Maximum waiting period for pre-existing diseases not more than 36 months, with continuous renewal",
        "confirmed": True,
    },
    "cashless_decision_hours": {
        "value": 1,
        "source": "IRDAI Master Circular on Health Insurance Business, 29 May 2024",
        "clause": "Chapter I, para 15(b) (p.22-23)",
        "confirmed": True,
    },
    "discharge_authorisation_hours": {
        "value": 3,
        "source": "IRDAI Master Circular on Health Insurance Business, 29 May 2024",
        "clause": "Chapter I, para 16(a)-(b) (p.23): extra charges from a delay are borne by the insurer",
        "confirmed": True,
    },
    "insurer_collects_documents": {
        "value": True,
        "source": "IRDAI Master Circular on Health Insurance Business, 29 May 2024",
        "clause": "Chapter I, para 17(c) (p.23): insurers and TPAs collect documents from hospitals",
        "confirmed": True,
    },
    "rejection_must_cite_terms": {
        "value": True,
        "source": "IRDAI Master Circular on Health Insurance Business, 29 May 2024",
        "clause": "Chapter I, para 17(b) (p.23)",
        "confirmed": True,
    },
}


@dataclass
class Case:
    policy_inception: date
    continuous_cover: bool
    admission: date
    rejection_ground: str  # one of taxonomy.GROUNDS
    fraud_alleged: bool = False
    ped_wait_months_in_policy: int | None = None
    pre_policy_check_normal: bool | None = None
    cashless_decision_hours: float | None = None
    sum_insured_increased_on: date | None = None  # the moratorium clock restarts for the added amount
    permanent_exclusion_cited: bool = False  # permanent exclusions survive the moratorium
    discharge_authorisation_hours: float | None = None
    cites_specific_terms: bool = True  # does the rejection letter cite the policy terms it relies on?


@dataclass
class Ground:
    rule: str
    title: str
    explanation: str
    sources: list[str]
    letter: str = ""  # first-person wording for the grievance letter


def months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def moratorium(case: Case) -> Ground | None:
    """Non-disclosure can't be raised after the moratorium, except for fraud."""
    limit = RULES["moratorium_months"]["value"]
    if case.rejection_ground != "non_disclosure_proposal":
        return None
    if not case.continuous_cover or case.fraud_alleged or case.permanent_exclusion_cited:
        return None
    covered = months_between(case.policy_inception, case.admission)
    if covered < limit:
        return None
    caveat = ""
    if case.sum_insured_increased_on and months_between(case.sum_insured_increased_on, case.admission) < limit:
        caveat = (" The sum insured was increased less than 60 months before admission, so this "
                  "protection covers the original sum insured only.")
    return Ground(
        rule="moratorium",
        title="The moratorium protects this claim",
        explanation=(
            f"The policy has run for {covered} continuous months. After {limit} months "
            "a claim cannot be contested for non-disclosure unless fraud is established, "
            "and the rejection does not allege fraud." + caveat
        ),
        sources=[RULES["moratorium_months"]["source"], "policy renewal history"],
        letter=(
            f"My policy has been renewed without a break for {covered} months. After {limit} continuous "
            "months of cover, no claim can be contested on grounds of non-disclosure except established "
            "fraud, and your letter does not allege fraud." + (
                " I accept this protection applies to my original sum insured." if caveat else "")
        ),
    )


def ped_wait_cap(case: Case) -> Ground | None:
    """A policy can't impose a pre-existing-disease wait longer than the cap."""
    cap = RULES["ped_max_wait_months"]["value"]
    if case.rejection_ground not in ("pre_existing_disease", "waiting_period"):
        return None
    if case.ped_wait_months_in_policy is None or case.ped_wait_months_in_policy <= cap:
        return None
    covered = months_between(case.policy_inception, case.admission)
    if covered < cap:
        return None
    return Ground(
        rule="ped_wait_cap",
        title="The waiting period applied is longer than allowed",
        explanation=(
            f"The policy applies a {case.ped_wait_months_in_policy}-month wait for pre-existing "
            f"diseases, above the {cap}-month maximum, and you have been covered {covered} months."
        ),
        sources=[RULES["ped_max_wait_months"]["source"], "policy wording"],
        letter=(
            f"The policy applies a {case.ped_wait_months_in_policy}-month waiting period for pre-existing "
            f"diseases, above the {cap}-month maximum permitted, and I have been covered for {covered} months."
        ),
    )


def insurer_own_health_check(case: Case) -> Ground | None:
    """Evidence argument: the insurer's own pre-policy check contradicts non-disclosure."""
    if case.rejection_ground != "non_disclosure_proposal" or not case.pre_policy_check_normal:
        return None
    return Ground(
        rule="pre_policy_check",
        title="The insurer checked your health before issuing the policy",
        explanation="The insurer's own pre-policy medical check recorded no abnormality for the condition now said to be concealed.",
        sources=["pre-policy medical report"],
        letter="Your own pre-policy medical check recorded no abnormality and accepted me at standard rates.",
    )


def cashless_delay(case: Case) -> Ground | None:
    limit = RULES["cashless_decision_hours"]["value"]
    if case.cashless_decision_hours is None or case.cashless_decision_hours <= limit:
        return None
    return Ground(
        rule="cashless_delay",
        title="The cashless decision was late",
        explanation=f"The insurer took {case.cashless_decision_hours:g} hours to decide; the limit is {limit} hour.",
        sources=[RULES["cashless_decision_hours"]["source"], "hospital TPA correspondence"],
        letter=f"The cashless decision took {case.cashless_decision_hours:g} hours against the {limit}-hour limit.",
    )


def documents_collected_by_insurer(case: Case) -> Ground | None:
    """Insurers and TPAs must collect claim documents from the hospital themselves."""
    if case.rejection_ground != "documents_not_submitted":
        return None
    return Ground(
        rule="documents_collected_by_insurer",
        title="The insurer must collect the documents itself",
        explanation=("IRDAI requires insurers and TPAs to collect the required documents from the hospital; "
                     "the policyholder is not required to submit them."),
        sources=[RULES["insurer_collects_documents"]["source"] + ", " + RULES["insurer_collects_documents"]["clause"]],
        letter=("Under the IRDAI Master Circular on Health Insurance Business, insurers and TPAs must collect the "
                "required documents from the hospital, and the policyholder is not required to submit them."),
    )


def discharge_delay(case: Case) -> Ground | None:
    limit = RULES["discharge_authorisation_hours"]["value"]
    if case.discharge_authorisation_hours is None or case.discharge_authorisation_hours <= limit:
        return None
    return Ground(
        rule="discharge_delay",
        title="Charges from the late discharge approval are the insurer's to pay",
        explanation=(f"Final discharge approval took {case.discharge_authorisation_hours:g} hours against the "
                     f"{limit}-hour limit; any extra hospital charges from the delay must be borne by the insurer."),
        sources=[RULES["discharge_authorisation_hours"]["source"] + ", " + RULES["discharge_authorisation_hours"]["clause"]],
        letter=(f"Final discharge approval took {case.discharge_authorisation_hours:g} hours against the {limit}-hour "
                "limit, so any additional hospital charges caused by the delay must be borne by you."),
    )


def vague_rejection(case: Case) -> Ground | None:
    if case.cites_specific_terms:
        return None
    return Ground(
        rule="vague_rejection",
        title="The rejection does not cite the policy terms it relies on",
        explanation=("A rejection must give full details with reference to the specific terms and conditions "
                     "of the policy. This letter does not."),
        sources=[RULES["rejection_must_cite_terms"]["source"] + ", " + RULES["rejection_must_cite_terms"]["clause"]],
        letter=("Your letter does not refer to the specific terms and conditions of the policy relied on, as the "
                "IRDAI Master Circular on Health Insurance Business requires."),
    )


ALL_RULES = [moratorium, ped_wait_cap, insurer_own_health_check, cashless_delay,
             documents_collected_by_insurer, discharge_delay, vague_rejection]


def run_rules(case: Case) -> list[Ground]:
    return [g for rule in ALL_RULES if (g := rule(case))]


def strength(grounds: list[Ground]) -> str:
    """Strong / Fair / Weak. Rule-based grounds weigh more than evidence-only ones."""
    legal = sum(g.rule != "pre_policy_check" for g in grounds)
    if legal >= 1:
        return "Strong"
    if grounds:
        return "Fair"
    return "Weak"
