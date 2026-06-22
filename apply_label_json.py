"""
apply_label_json.py — Merge Cursor-agent label JSON into data/comments.csv.

Usage:
    python apply_label_json.py data/cursor_batches/batch_0_labels.json

JSON format (one of):
  {"labels": ["analysis", "hot_take", ...]}  — same order as batch_N_meta.json
  {"ortc1k0": "hot_take", "eoniw65": "analysis", ...}  — by permalink id
"""

import csv
import json
import sys
from pathlib import Path

OUT = Path("data/comments.csv")
RAW = Path("data/raw_comments.csv")
DROPPED = Path("data/dropped.txt")
FIELDS = ["text", "label", "prelabel_original", "notes", "score", "permalink", "source"]


def pid(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python apply_label_json.py <labels.json>")
    labels_data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    raw_by_pid = {pid(r["permalink"]): r for r in csv.DictReader(RAW.open(encoding="utf-8"))}
    done = set()
    if OUT.exists():
        done = {r["permalink"] for r in csv.DictReader(OUT.open(encoding="utf-8"))}

    # resolve label list to pid -> label
    mapping: dict[str, str] = {}
    if "labels" in labels_data:
        meta_path = Path(sys.argv[1]).with_name(
            Path(sys.argv[1]).stem.replace("_labels", "_meta").replace("batch_", "batch_")
        )
        # try sibling meta file: batch_0_labels.json -> batch_0_meta.json
        stem = Path(sys.argv[1]).stem.replace("_labels", "")
        meta_path = Path(sys.argv[1]).parent / f"{stem}_meta.json"
        if not meta_path.exists():
            sys.exit(f"Need {meta_path} for ordered labels array.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for m, lab in zip(meta, labels_data["labels"]):
            mapping[pid(m["permalink"])] = lab.strip().lower()
    else:
        mapping = {k: v.strip().lower() for k, v in labels_data.items()}

    new_file = not OUT.exists()
    added = 0
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for pid_key, lab in mapping.items():
            row = raw_by_pid.get(pid_key)
            if not row or row["permalink"] in done:
                continue
            if lab == "skip":
                lab = "SKIP"
            if lab == "SKIP":
                with DROPPED.open("a", encoding="utf-8") as df:
                    df.write(row["permalink"] + "\n")
                continue
            w.writerow(
                {
                    "text": row["text"],
                    "label": lab,
                    "prelabel_original": lab,
                    "notes": "",
                    "score": row.get("score", ""),
                    "permalink": row["permalink"],
                    "source": row.get("source", ""),
                }
            )
            added += 1
    print(f"Added {added} rows to {OUT}")


if __name__ == "__main__":
    main()
