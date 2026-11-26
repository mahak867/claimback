"""Baseline rejection-reason classifier: TF-IDF + logistic regression, 5-fold cross-validation.

This is the number the fine-tuned ClaimBack model has to beat.

Usage:  python tools/train_baseline.py path/to/clean.jsonl
(the *_clean.jsonl file written by tools/validate_dataset.py)
"""
import json
import re
import sys
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

IN_KEYS = ("input", "prompt", "enhanced_prompt")
OUT_KEYS = ("output", "response", "completion", "enhanced_completion")


def load(path):
    texts, labels = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            letter = next((row[k] for k in IN_KEYS if k in row), None)
            out = next((row[k] for k in OUT_KEYS if k in row), None)
            if isinstance(out, str):
                out = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
            if letter and out and out.get("rejection_ground"):
                texts.append(letter)
                labels.append(out["rejection_ground"])
    return texts, labels


def main(path):
    texts, labels = load(path)
    counts = Counter(labels)
    keep = [i for i, y in enumerate(labels) if counts[y] >= 5]
    texts, labels = [texts[i] for i in keep], [labels[i] for i in keep]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )
    pred = cross_val_predict(model, texts, labels, cv=StratifiedKFold(5, shuffle=True, random_state=0))
    print(f"Rows: {len(texts)}  classes: {len(set(labels))}")
    print(f"Macro-F1 (5-fold): {f1_score(labels, pred, average='macro'):.3f}")
    print(f"Accuracy (5-fold): {sum(p == y for p, y in zip(pred, labels)) / len(labels):.3f}\n")
    print(classification_report(labels, pred, digits=2, zero_division=0))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
