"""
add_from_json.py — Add ONE new browser-saved thread without rebuilding the whole dataset.

Workflow for analysis backfill:
  1. On r/indieheads, find an "Album Discussion" thread (see data/analysis_thread_tips.txt).
  2. Open the thread's .json URL in your browser and save to data/raw_json/.
  3. Run:  python add_from_json.py data/raw_json/your_new_thread.json

This appends new comments to data/raw_comments.csv and data/comments.csv
(pre-labeled as analysis when the thread name looks like album discussion,
otherwise label is blank for you to fill). Skips duplicates by permalink.
"""

import csv
import sys
from pathlib import Path

from collect import is_usable, walk_comments
from parse_local import load_comments

RAW = Path("data/raw_comments.csv")
OUT = Path("data/comments.csv")
FIELDS = ["text", "label", "prelabel_original", "notes", "score", "permalink", "source"]
RAW_FIELDS = ["text", "score", "author", "permalink", "source"]
MAX_KEEP = 60  # per thread


def read_csv(path: Path, fields: list[str]) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def is_analysis_thread(name: str) -> bool:
    n = name.lower()
    return "album_discussion" in n or "album discussion" in n


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python add_from_json.py data/raw_json/<file>.json")

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        sys.exit(f"File not found: {json_path}")

    comments = load_comments(json_path)
    existing_raw = read_csv(RAW, RAW_FIELDS)
    existing_out = read_csv(OUT, FIELDS)
    seen_perm = {r["permalink"] for r in existing_raw} | {r["permalink"] for r in existing_out}
    seen_text = {r["text"] for r in existing_raw}

    default_label = "analysis" if is_analysis_thread(json_path.name) else ""
    added_raw, added_out = 0, 0

    for c in comments:
        if added_raw >= MAX_KEEP:
            break
        body = (c.get("body") or "").strip()
        author = c.get("author") or ""
        permalink = "https://www.reddit.com" + c.get("permalink", "")
        if permalink in seen_perm or body in seen_text:
            continue
        if not is_usable(body, author):
            continue
        row_raw = {
            "text": body,
            "score": c.get("score", 0),
            "author": author,
            "permalink": permalink,
            "source": json_path.name,
        }
        existing_raw.append(row_raw)
        seen_perm.add(permalink)
        seen_text.add(body)
        added_raw += 1

        if default_label:
            existing_out.append(
                {
                    "text": body,
                    "label": default_label,
                    "prelabel_original": default_label,
                    "notes": "",
                    "score": row_raw["score"],
                    "permalink": permalink,
                    "source": json_path.name,
                }
            )
            added_out += 1

    write_csv(RAW, RAW_FIELDS, existing_raw)
    if added_out:
        write_csv(OUT, FIELDS, existing_out)

    print(f"Added {added_raw} comments from {json_path.name} to {RAW}.")
    if default_label:
        print(f"Pre-tagged {added_out} as analysis (filename match) — still review each row.")
    else:
        print("Not an album-discussion filename — added to raw only. Label with export_batches.py.")
    print("Run: python check_distribution.py")


if __name__ == "__main__":
    main()
