"""Score field extraction against gold answers.

Usage:
  python tools/eval_extraction.py gold.jsonl                  # scores the rule-based baseline
  python tools/eval_extraction.py gold.jsonl predictions.jsonl  # scores a model's outputs (same row order)

gold.jsonl: the *_clean.jsonl written by validate_dataset.py.
predictions.jsonl: one JSON object per line, the model's 11-key answer for each gold row.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from claimback.citations import normalise  # noqa: E402
from claimback.extract_baseline import extract  # noqa: E402

FIELDS = ["insurer_name", "policy_number", "policy_inception_date", "claim_type", "claim_amount_inr",
          "admission_date", "discharge_date", "diagnosis", "rejection_ground", "clause_cited",
          "rejection_reason_quote"]
IN_KEYS = ("input", "prompt", "enhanced_prompt")
OUT_KEYS = ("output", "response", "completion", "enhanced_completion")


def load_gold(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        letter = next(r[k] for k in IN_KEYS if k in r)
        out = next(r[k] for k in OUT_KEYS if k in r)
        if isinstance(out, str):
            out = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
        rows.append((letter, out))
    return rows


def same(field, pred, gold):
    if gold in (None, ""):
        return pred in (None, "")
    if pred in (None, ""):
        return False
    if field == "claim_amount_inr":
        try:
            return abs(float(pred) - float(gold)) < 1
        except (TypeError, ValueError):
            return False
    if field in ("clause_cited", "rejection_reason_quote", "insurer_name", "diagnosis"):
        p, g = normalise(str(pred)), normalise(str(gold))
        return p == g or (len(p) >= 8 and (p in g or g in p))
    return normalise(str(pred)) == normalise(str(gold))


def score(rows, preds):
    hits = {f: 0 for f in FIELDS}
    quotes_verbatim = 0
    for (letter, gold), pred in zip(rows, preds):
        for f in FIELDS:
            hits[f] += same(f, pred.get(f), gold.get(f))
        q = pred.get("rejection_reason_quote")
        quotes_verbatim += bool(q) and normalise(q) in normalise(letter)
    n = len(rows)
    return {f: hits[f] / n for f in FIELDS}, quotes_verbatim / n


def main(gold_path, pred_path=None):
    rows = load_gold(gold_path)
    if pred_path:
        preds = [json.loads(l) for l in open(pred_path, encoding="utf-8")]
        label = "model"
    else:
        preds = [extract(letter) for letter, _ in rows]
        label = "rule-based baseline"
    per_field, verbatim = score(rows, preds)
    print(f"{label} on {len(rows)} rows\n")
    for f, v in per_field.items():
        print(f"  {f:24s} {v:6.1%}")
    print(f"\n  mean field accuracy      {sum(per_field.values()) / len(per_field):6.1%}")
    print(f"  quotes found verbatim    {verbatim:6.1%}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(*sys.argv[1:])
