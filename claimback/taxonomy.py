"""Rejection-ground labels.

Adapted from the Alei project's frozen repudiation taxonomy v1.0
(https://github.com/Ashmit-rai17/alei, MIT licence), built from Indian
Insurance Ombudsman awards. We use its shared and health categories.
"""

GROUNDS = {
    "non_disclosure_proposal": "Facts withheld or misstated on the proposal form",
    "non_disclosure_revival": "Facts withheld when reviving a lapsed policy",
    "fraud_misrepresentation": "Deliberately false claim or application",
    "policy_not_in_force": "Policy lapsed or event outside the policy period",
    "documents_not_submitted": "Required documents not provided",
    "excluded_by_clause": "A named exclusion clause applies",
    "pre_existing_disease": "Condition existed before cover began",
    "waiting_period": "A waiting period had not elapsed",
    "hospitalisation_not_justified": "Admission not medically necessary",
    "treatment_not_covered": "The procedure itself is not covered",
    "amount_limited": "Valid claim capped or reduced (sub-limits, room rent, consumables)",
}
