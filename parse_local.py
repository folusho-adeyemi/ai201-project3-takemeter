"""
parse_local.py — Build the comment CSV from browser-saved Reddit JSON files.

Reddit blocks unauthenticated scripts (403), but your *browser* can load the
".json" view of any thread. So:

  1. For each thread, open its .json URL in your browser, e.g.:
       https://www.reddit.com/r/indieheads/comments/bshqd5/..../.json
  2. Save the page (or copy all + paste) into data/raw_json/ as a .json file.
     Any filename is fine (e.g., cure_roast.json, modest_mouse.json).
  3. Run:  python parse_local.py

Output: data/raw_comments.csv (text, score, author, permalink, source)
Reuses the same filtering/dedup as collect.py. Next step: prelabel.py.
"""

import csv
import json
import sys
from pathlib import Path

from collect import MAX_PER_THREAD, is_usable, walk_comments

RAW_JSON_DIR = Path("data/raw_json")
OUTPUT_FILE = Path("data/raw_comments.csv")


def load_comments(path: Path) -> list[dict]:
    """Handle both a saved thread (list: [post, comments]) and odd wrappers."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and len(payload) >= 2:
        return walk_comments(payload[1].get("data", {}).get("children", []))
    # Fallback: a single listing of comments
    if isinstance(payload, dict) and payload.get("kind") == "Listing":
        return walk_comments(payload.get("data", {}).get("children", []))
    return []


def main() -> None:
    files = sorted(RAW_JSON_DIR.glob("*.json"))
    if not files:
        sys.exit(
            f"No .json files in {RAW_JSON_DIR}. Open each thread's .json URL in your "
            "browser and save it there first."
        )
    print(f"Parsing {len(files)} saved thread file(s)...\n")

    seen_ids: set[str] = set()
    seen_text: set[str] = set()
    rows: list[dict] = []

    for path in files:
        try:
            comments = load_comments(path)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {path.name}: could not parse ({exc})")
            continue

        kept = 0
        for c in comments:
            if kept >= MAX_PER_THREAD:
                break
            cid = c.get("id")
            body = (c.get("body") or "").strip()
            author = c.get("author") or ""
            if cid in seen_ids or body in seen_text:
                continue
            if not is_usable(body, author):
                continue
            seen_ids.add(cid)
            seen_text.add(body)
            rows.append(
                {
                    "text": body,
                    "score": c.get("score", 0),
                    "author": author,
                    "permalink": "https://www.reddit.com" + c.get("permalink", ""),
                    "source": path.name,
                }
            )
            kept += 1
        print(f"  {path.name}: kept {kept} (running total: {len(rows)})")

    if not rows:
        sys.exit("\nNo usable comments found. Check the saved files are full thread JSON.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "score", "author", "permalink", "source"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Wrote {len(rows)} comments to {OUTPUT_FILE}.")
    if len(rows) < 200:
        print(f"Only {len(rows)} so far — save a few more threads to clear 200.")
    print("Next: run prelabel.py, then review every label by hand.")


if __name__ == "__main__":
    main()
