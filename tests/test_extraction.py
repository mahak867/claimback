import json
import subprocess
import sys

from claimback.extract_baseline import extract

LETTER = """Kaveri Health Insurance Ltd.
Date: 24/06/2026
Policy No: KHI/MDU/2023/77104
We refer to your claim for Rs. 1,38,000 towards Diabetic Foot Ulcer Surgery at City Hospital from 10/06/2026 to 16/06/2026.
The claim is not admissible as Diabetes Mellitus is a pre-existing disease and the 48-month waiting period under Clause 4.2 of the policy has not been completed."""


def test_baseline_extracts_core_fields():
    out = extract(LETTER)
    assert out["policy_number"] == "KHI/MDU/2023/77104"
    assert out["claim_amount_inr"] == 138000
    assert out["admission_date"] == "2026-06-10"
    assert out["rejection_ground"] == "waiting_period"
    assert out["clause_cited"] == "Clause 4.2"
    assert out["rejection_reason_quote"].startswith("The claim is not admissible")


def test_lakh_amounts():
    assert extract("We refer to your claim of ₹2.47 lakh.")["claim_amount_inr"] == 247000


def _gold(tmp_path):
    gold = {"insurer_name": "Kaveri Health Insurance Ltd.", "policy_number": "KHI/MDU/2023/77104",
            "policy_inception_date": None, "claim_type": "reimbursement", "claim_amount_inr": 138000,
            "admission_date": "2026-06-10", "discharge_date": "2026-06-16", "diagnosis": "Diabetic Foot Ulcer Surgery",
            "rejection_ground": "waiting_period", "clause_cited": "Clause 4.2",
            "rejection_reason_quote": "The claim is not admissible as Diabetes Mellitus is a pre-existing disease"}
    f = tmp_path / "gold.jsonl"
    f.write_text(json.dumps({"prompt": LETTER, "completion": json.dumps(gold)}) + "\n", encoding="utf-8")
    return f, gold


def test_evaluator_scores_perfect_predictions(tmp_path):
    f, gold = _gold(tmp_path)
    p = tmp_path / "pred.jsonl"
    p.write_text(json.dumps(gold) + "\n", encoding="utf-8")
    out = subprocess.run([sys.executable, "tools/eval_extraction.py", str(f), str(p)],
                         capture_output=True, text=True, check=True).stdout
    assert "mean field accuracy      100.0%" in out and "quotes found verbatim    100.0%" in out


def test_prepare_training_dedupes_and_splits(tmp_path):
    f, _ = _gold(tmp_path)
    out = subprocess.run([sys.executable, "tools/prepare_training.py", str(tmp_path / "split"), str(f), str(f)],
                         capture_output=True, text=True, check=True).stdout
    assert out.startswith("1 unique rows")
    assert (tmp_path / "split" / "train.jsonl").read_text(encoding="utf-8").count("\n") == 1
