"""
export_batches.py — Export unlabeled comments for Cursor-agent pre-labeling.

When Groq rate-limits, paste each batch file into Cursor chat with your label
definitions from planning.md and ask for a JSON labels array. Then merge with:

    python apply_label_json.py data/cursor_batches/batch_0_labels.json

Or ask the Cursor agent to run finish_cursor_labels / apply_label_json directly.
"""

import csv
import json
from pathlib import Path

RAW = Path("data/raw_comments.csv")
OUT = Path("data/comments.csv")
BATCH_DIR = Path("data/cursor_batches")
BATCH_SIZE = 15

PROMPT_HEADER = """Label each comment below with exactly ONE of: analysis, hot_take, reaction.

Definitions (r/indieheads):
- analysis: claim backed by specific, load-bearing musical evidence (production, theory, lyrics, discography) explaining how/why.
- hot_take: bold judgment without real support; decorative facts don't count.
- reaction: emotional response anchored to a specific event/moment.
Tie-break: analysis > hot_take > reaction. Mark off-topic (sleep advice, sushi, mod posts) as SKIP.

Reply with ONLY JSON: {"labels": ["analysis", "hot_take", ...]} in order. Use "SKIP" for off-topic.
"""


def main() -> None:
    raw = list(csv.DictReader(RAW.open(encoding="utf-8")))
    done = set()
    if OUT.exists():
        done = {r["permalink"] for r in csv.DictReader(OUT.open(encoding="utf-8"))}
    todo = [r for r in raw if r["permalink"] not in done]
    if not todo:
        print("All rows already labeled.")
        return

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for i, start in enumerate(range(0, len(todo), BATCH_SIZE)):
        chunk = todo[start : start + BATCH_SIZE]
        lines = [PROMPT_HEADER, f"\n--- batch {i} ({len(chunk)} comments) ---\n"]
        for j, r in enumerate(chunk, 1):
            lines.append(f"{j}. {r['text']}\n")
        path = BATCH_DIR / f"batch_{i}.txt"
        path.write_text("\n".join(lines), encoding="utf-8")
        meta = [{"permalink": r["permalink"], "text": r["text"][:80]} for r in chunk]
        (BATCH_DIR / f"batch_{i}_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Exported {len(todo)} comments in {(len(todo)+BATCH_SIZE-1)//BATCH_SIZE} batches to {BATCH_DIR}/")
