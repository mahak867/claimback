"""Run a deployed ClaimBack model over test letters and save its answers for eval_extraction.py.

Works with any OpenAI-compatible chat endpoint (Together AI, vLLM, Ollama, and similar hosts
of open models). Settings come from the environment:
  CLAIMBACK_BASE_URL   e.g. https://api.together.xyz/v1  or  http://localhost:11434/v1
  CLAIMBACK_MODEL      the deployed model's name
  CLAIMBACK_API_KEY    the key, if the host needs one

Usage:
  python tools/run_model.py test.jsonl predictions.jsonl
  python tools/eval_extraction.py test.jsonl predictions.jsonl
"""
import json
import os
import re
import sys
import urllib.request

FIELDS = ["insurer_name", "policy_number", "policy_inception_date", "claim_type", "claim_amount_inr",
          "admission_date", "discharge_date", "diagnosis", "rejection_ground", "clause_cited",
          "rejection_reason_quote"]
IN_KEYS = ("input", "prompt", "enhanced_prompt")
SYSTEM = ("Read the Indian health insurance claim rejection letter and return only a JSON object with these keys: "
          + ", ".join(FIELDS) + ". Use null for facts the letter does not state. Dates as YYYY-MM-DD. "
          "clause_cited and rejection_reason_quote must be copied character for character from the letter.")


def parse_answer(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    return {k: out.get(k) for k in FIELDS} if isinstance(out, dict) else {k: None for k in FIELDS}


def ask(letter: str) -> str:
    # The fine-tuned model was trained on plain chats (letter -> JSON) with no system prompt, so ask it the
    # same way. Set CLAIMBACK_SYSTEM_PROMPT=1 only for base models that need the instructions.
    messages = [{"role": "user", "content": letter}]
    if os.environ.get("CLAIMBACK_SYSTEM_PROMPT") == "1":
        messages.insert(0, {"role": "system", "content": SYSTEM})
    body = json.dumps({"model": os.environ["CLAIMBACK_MODEL"], "temperature": 0, "messages": messages})
    req = urllib.request.Request(os.environ["CLAIMBACK_BASE_URL"].rstrip("/") + "/chat/completions",
                                 data=body.encode(), headers={"Content-Type": "application/json"})
    if os.environ.get("CLAIMBACK_API_KEY"):
        req.add_header("Authorization", "Bearer " + os.environ["CLAIMBACK_API_KEY"])
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def main(test_path, out_path):
    rows = [json.loads(l) for l in open(test_path, encoding="utf-8")]
    with open(out_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            letter = next(r[k] for k in IN_KEYS if k in r)
            f.write(json.dumps(parse_answer(ask(letter)), ensure_ascii=False) + "\n")
            print(f"\r{i}/{len(rows)}", end="", flush=True)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
