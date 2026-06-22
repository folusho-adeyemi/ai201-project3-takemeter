"""
check_distribution.py — Sanity-check your labeled dataset before training.

Reports total count, per-label distribution (warns if any label > 70%), how many
rows still need review (UNSURE / blank), and your correction rate vs. the
pre-labels (a disclosure metric for your AI usage section).

    python check_distribution.py
"""

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

DATA_FILE = Path("data/comments.csv")
VALID = {"analysis", "hot_take", "reaction"}


def main() -> None:
    if not DATA_FILE.exists():
        sys.exit(f"Missing {DATA_FILE}. Run collect.py + prelabel.py first.")

    df = pd.read_csv(DATA_FILE)
    total = len(df)
    print(f"Total rows: {total}\n")

    labels = df["label"].fillna("").str.strip()
    counts = Counter(labels)

    unreviewed = sum(counts[k] for k in counts if k not in VALID)
    print("Label distribution:")
    for label in sorted(VALID):
        n = counts.get(label, 0)
        pct = (100 * n / total) if total else 0
        flag = "  <-- OVER 70%!" if pct > 70 else ""
        print(f"  {label:10s} {n:4d}  ({pct:5.1f}%){flag}")
    if unreviewed:
        print(f"  {'UNSURE/blank':10s} {unreviewed:4d}  <-- still need review")

    print()
    valid_total = sum(counts.get(l, 0) for l in VALID)
    if valid_total < 200:
        print(f"WARNING: only {valid_total} fully-labeled rows (need >= 200).")
    over_70 = total and any((100 * counts.get(l, 0) / total) > 70 for l in VALID)
    if over_70:
        print("WARNING: a label exceeds 70% — collect more of the rare labels.")

    if "prelabel_original" in df.columns:
        comparable = df[df["prelabel_original"].isin(VALID) & df["label"].isin(VALID)]
        if len(comparable):
            changed = (comparable["label"] != comparable["prelabel_original"]).sum()
            rate = 100 * changed / len(comparable)
            print(
                f"\nCorrection rate: you changed {changed}/{len(comparable)} "
                f"pre-labels ({rate:.1f}%). Report this in your AI usage section."
            )


if __name__ == "__main__":
    main()
