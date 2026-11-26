"""Merge clean datasets, remove duplicates, and split 80/20 by rejection reason.

Usage:  python tools/prepare_training.py out_dir v1_clean.jsonl [v2_clean.jsonl ...]

Writes out_dir/train.jsonl and out_dir/test.jsonl, one {"prompt": letter, "completion": json-string}
per line, ready to upload to Adaption / AutoScientist. The test file is never used for training.
"""
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

IN_KEYS = ("input", "prompt", "enhanced_prompt")
OUT_KEYS = ("output", "response", "completion", "enhanced_completion")


def rows(path):
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        letter = next(r[k] for k in IN_KEYS if k in r)
        out = next(r[k] for k in OUT_KEYS if k in r)
        if isinstance(out, str):
            out = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
        yield letter.strip(), out


def split(pairs, test_share=0.2, seed=7):
    by_ground = defaultdict(list)
    for p in pairs:
        by_ground[p[1].get("rejection_ground")].append(p)
    rng = random.Random(seed)
    train, test = [], []
    for g in sorted(by_ground, key=str):
        items = by_ground[g]
        rng.shuffle(items)
        k = max(1, round(len(items) * test_share)) if len(items) > 1 else 0
        test += items[:k]
        train += items[k:]
    return train, test


def main(out_dir, *paths):
    seen, pairs = set(), []
    for p in paths:
        for letter, out in rows(p):
            key = re.sub(r"\s+", " ", letter.lower())
            if key not in seen:
                seen.add(key)
                pairs.append((letter, out))
    train, test = split(pairs)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", train), ("test", test)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for letter, ans in part:
                f.write(json.dumps({"prompt": letter, "completion": json.dumps(ans, ensure_ascii=False)},
                                   ensure_ascii=False) + "\n")
    print(f"{len(pairs)} unique rows -> train {len(train)}, test {len(test)} in {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], *sys.argv[2:])
