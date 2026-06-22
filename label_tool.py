"""
label_tool.py — Review pre-labels and correct by hand.

Hybrid workflow (planning.md):
  1. python prelabel.py   → tentative labels in data/comments.csv
  2. python label_tool.py → review each row: accept or override

Resumable: skips rows already reviewed (label changed from prelabel_original, or notes set).

Keys:
    Enter     = accept the pre-label suggestion
    a / h / r = override: analysis / hot_take / reaction
    s         = skip/drop
    b         = redo previous
    q         = quit
"""

import csv
import sys
from collections import Counter
from pathlib import Path

OUT = Path("data/comments.csv")
DROPPED = Path("data/dropped.txt")
FIELDS = ["text", "label", "prelabel_original", "notes", "score", "permalink", "source"]
KEYS = {"a": "analysis", "h": "hot_take", "r": "reaction"}
VALID = set(KEYS.values())

HELP = """\
  [Enter] accept suggestion
  [a] analysis   [h] hot_take   [r] reaction
  [s] skip       [b] back       [q] quit"""


def load_rows() -> list[dict]:
    if not OUT.exists():
        sys.exit(f"Missing {OUT}. Run prelabel.py first.")
    with OUT.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"{OUT} is empty. Run prelabel.py first.")
    if "prelabel_original" not in rows[0]:
        sys.exit(f"{OUT} missing prelabel_original column. Run prelabel.py first.")
    return rows


def is_reviewed(row: dict) -> bool:
    if row.get("notes", "").strip():
        return True
    orig = row.get("prelabel_original", "")
    lab = row.get("label", "")
    if orig in VALID and lab != orig:
        return True
    return False


def reviewed_counts(rows: list[dict]) -> Counter:
    c: Counter = Counter()
    for r in rows:
        if is_reviewed(r) and r["label"] in VALID:
            c[r["label"]] += 1
    return c


def write_all(rows: list[dict]) -> None:
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows = load_rows()
    dropped: set[str] = set()
    if DROPPED.exists():
        dropped = {x for x in DROPPED.read_text(encoding="utf-8").splitlines() if x}

    queue = [
        i for i, r in enumerate(rows)
        if r["permalink"] not in dropped and not is_reviewed(r)
    ]
    reviewed_n = sum(1 for r in rows if is_reviewed(r))
    print(f"\n{len(rows)} total, {reviewed_n} reviewed, {len(queue)} left.\n")

    if not queue:
        print("All reviewed. Run check_distribution.py next.")
        return

    pos = 0
    while pos < len(queue):
        i = queue[pos]
        r = rows[i]
        suggestion = r.get("prelabel_original", "UNSURE")
        c = reviewed_counts(rows)

        print("=" * 74)
        print(
            f"review {reviewed_n + pos + 1}/{len(rows)}   "
            f"suggestion -> {suggestion}   "
            f"(reviewed: a={c['analysis']} h={c['hot_take']} r={c['reaction']})  "
            f"[{r.get('source', '')}]"
        )
        print("-" * 74)
        print(r["text"])
        print("-" * 74)
        print(HELP)

        choice = input(f"label [{suggestion}]> ").strip().lower()

        if choice == "q":
            write_all(rows)
            print(f"\nSaved. {sum(reviewed_counts(rows).values())} reviewed labels.")
            return
        if choice == "b":
            if pos == 0:
                print("  (nothing to go back to)")
                continue
            prev = queue[pos - 1]
            rows[prev]["label"] = rows[prev]["prelabel_original"]
            rows[prev]["notes"] = ""
            write_all(rows)
            pos -= 1
            continue
        if choice == "s":
            with DROPPED.open("a", encoding="utf-8") as df:
                df.write(r["permalink"] + "\n")
            pos += 1
            continue
        if choice == "":
            rows[i]["label"] = suggestion
            write_all(rows)
            pos += 1
            continue
        if choice in KEYS:
            note = input("note (optional)> ").strip()
            rows[i]["label"] = KEYS[choice]
            rows[i]["notes"] = note
            write_all(rows)
            pos += 1
            continue
        print("  ? Enter=accept, a/h/r=override, s=skip, b=back, q=quit")


if __name__ == "__main__":
    main()
