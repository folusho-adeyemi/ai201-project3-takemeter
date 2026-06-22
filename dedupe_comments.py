"""
dedupe_comments.py — Remove duplicate permalinks from data/comments.csv.

Keeps one row per permalink. On conflicting labels for the same comment:
  1. Prefer a row where label != prelabel_original (hand-corrected)
  2. Otherwise keep the first occurrence

Logs conflicts to data/dedupe_conflicts.txt.
"""

import csv
from pathlib import Path

OUT = Path("data/comments.csv")
LOG = Path("data/dedupe_conflicts.txt")
FIELDS = ["text", "label", "prelabel_original", "notes", "score", "permalink", "source"]
VALID = {"analysis", "hot_take", "reaction"}


def pick_best(rows: list[dict]) -> dict:
    corrected = [r for r in rows if r.get("prelabel_original") in VALID and r["label"] != r["prelabel_original"]]
    if corrected:
        return corrected[0]
    noted = [r for r in rows if r.get("notes", "").strip()]
    if noted:
        return noted[0]
    return rows[0]


def main() -> None:
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    by_perm: dict[str, list[dict]] = {}
    for r in rows:
        by_perm.setdefault(r["permalink"], []).append(r)

    conflicts = []
    kept = []
    for permalink, group in by_perm.items():
        if len(group) > 1:
            labels = {g["label"] for g in group}
            if len(labels) > 1:
                chosen = pick_best(group)
                conflicts.append(
                    f"{permalink}\n  labels: {sorted(labels)}\n  kept: {chosen['label']}\n  text: {chosen['text'][:100]}...\n"
                )
            else:
                chosen = pick_best(group)
            kept.append(chosen)
        else:
            kept.append(group[0])

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(kept)

    if conflicts:
        LOG.write_text("Dedupe conflicts resolved automatically:\n\n" + "\n".join(conflicts))
    else:
        LOG.write_text("No label conflicts among duplicates.\n")

    print(f"Removed {len(rows) - len(kept)} duplicate rows.")
    print(f"Before: {len(rows)}  After: {len(kept)}  Conflicts resolved: {len(conflicts)}")
    if conflicts:
        print(f"See {LOG} for conflict details.")


if __name__ == "__main__":
    main()
