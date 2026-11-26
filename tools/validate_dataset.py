"""Check an Adaption-generated ClaimBack extraction dataset before training on it.

Usage:  python validate_dataset.py path/to/export.jsonl   (or .csv / .json)

Each row needs an input (the rejection letter) and an output (JSON string or object).
Column names are guessed: input/prompt/instruction and output/response/completion.
"""
import csv
import json
import re
import sys
from collections import Counter
from datetime import date

GROUNDS = {
    "non_disclosure_proposal", "pre_existing_disease", "waiting_period",
    "hospitalisation_not_justified", "treatment_not_covered", "amount_limited",
    "documents_not_submitted", "policy_not_in_force", "excluded_by_clause",
    "fraud_misrepresentation",
}
REQUIRED = [
    "insurer_name", "policy_number", "policy_inception_date", "claim_type",
    "claim_amount_inr", "admission_date", "discharge_date", "diagnosis",
    "rejection_ground", "clause_cited", "rejection_reason_quote",
]
# These may be null when the letter genuinely doesn't state them; the key must still be present.
NULLABLE = {"policy_number", "policy_inception_date", "admission_date", "discharge_date", "clause_cited",
            "claim_type", "diagnosis", "claim_amount_inr"}
INSTRUCTION = re.compile(r"\b(please (generate|create|draft|write)|generate an?|draft an?|write an?|the letter should|"
                         r"the tone should|use formal indian english|the ground (for rejection )?is)\b", re.I)
IN_KEYS = ("input", "prompt", "enhanced_prompt", "instruction", "question", "text")
OUT_KEYS = ("output", "response", "completion", "enhanced_completion", "answer")


def load(path):
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def pick(row, keys):
    for k in keys:
        for rk in row:
            if rk.lower() == k:
                return row[rk]
    return None


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def parse_date(s):
    """ISO (2026-08-14) or Indian day-first (14/08/2026, 14-08-2026). None if unparseable."""
    s = str(s).strip()
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def check(row):
    problems = []
    letter, out = pick(row, IN_KEYS), pick(row, OUT_KEYS)
    if not letter or out is None:
        return ["missing input or output column"], None
    if isinstance(out, str):
        m = re.search(r"\{.*\}", out, re.S)
        try:
            out = json.loads(m.group(0) if m else out)
        except (json.JSONDecodeError, AttributeError):
            return ["output is not valid JSON"], None
    if not isinstance(out, dict):
        return ["output is not a JSON object"], None
    if INSTRUCTION.search(str(letter)):
        problems.append("input is an instruction, not a letter")
    for k in REQUIRED:
        if k not in out:
            problems.append(f"missing key: {k}")
        elif out[k] in (None, "") and k not in NULLABLE:
            problems.append(f"missing value: {k}")
    g = out.get("rejection_ground")
    if g and g not in GROUNDS:
        problems.append(f"unknown ground: {g!r}")
    for k in ("rejection_reason_quote", "clause_cited"):
        v = out.get(k)
        if v and norm(v) not in norm(letter):
            problems.append(f"{k} not verbatim in letter")
    try:
        if out.get("claim_amount_inr") is None:
            raise LookupError
        amt = float(str(out.get("claim_amount_inr", "")).replace(",", ""))
        if not 5_000 <= amt <= 25_00_000:
            problems.append(f"amount out of range: {amt:.0f}")
    except LookupError:
        pass
    except ValueError:
        problems.append("claim_amount_inr not a number")
    a, d, p = (parse_date(out.get(k)) for k in
               ("admission_date", "discharge_date", "policy_inception_date"))
    for k, v in zip(("admission_date", "discharge_date", "policy_inception_date"), (a, d, p)):
        if out.get(k) and (v is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(out[k]))):
            problems.append(f"date not YYYY-MM-DD: {k}")
    if a and d and d < a:
        problems.append("discharge before admission")
    if p and a and a < p:
        problems.append("admission before policy start")
    if out.get("claim_type") not in (None, "cashless", "reimbursement", "partial_settlement"):
        problems.append(f"bad claim_type: {out.get('claim_type')!r}")
    return problems, out


def main(path):
    rows = load(path)
    issues, grounds, bad = Counter(), Counter(), []
    for i, row in enumerate(rows):
        problems, out = check(row)
        if out:
            grounds[out.get("rejection_ground")] += 1
        for p in problems:
            issues[p.split(":")[0]] += 1
        if problems:
            bad.append((i, problems))
    n = len(rows)
    print(f"Rows: {n}   clean: {n - len(bad)} ({(n - len(bad)) / max(n, 1):.0%})\n")
    print("Problems (rows affected):")
    for p, c in issues.most_common():
        print(f"  {c:5d}  {p}")
    print("\nRejection-ground balance:")
    for g, c in grounds.most_common():
        print(f"  {c:5d}  {g}")
    missing = GROUNDS - set(grounds)
    if missing:
        print(f"\nGrounds never generated: {', '.join(sorted(missing))}")
    print("\nFirst 5 bad rows:")
    for i, p in bad[:5]:
        print(f"  row {i}: {'; '.join(p)}")
    bad_ids = {i for i, _ in bad}
    clean = [r for j, r in enumerate(rows) if j not in bad_ids]
    out_path = re.sub(r"(\.\w+)?$", "_clean.jsonl", path, count=1)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in clean:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(clean)} clean rows to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
