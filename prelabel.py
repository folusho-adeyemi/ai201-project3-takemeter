"""
prelabel.py — Tentative labels via Groq (optional; rate-limited on free tier).

If you hit Groq 429 rate limits, use the Cursor-agent workflow instead:
  1. python export_batches.py          # export unlabeled comments
  2. Paste batches into Cursor chat    # agent labels with planning.md rules
  3. python apply_label_json.py ...    # merge JSON back
  Or ask the Cursor agent to label directly (see finish_cursor_labels.py).

Reads data/raw_comments.csv, asks a Groq model (different from the zero-shot
baseline `llama-3.3-70b-versatile`) to assign one label per comment, and writes
data/comments.csv with a pre-filled `label` column.

Design notes (learned the hard way):
  * BATCHED — ~10 comments per request, so 298 comments = ~30 requests, which
    stays under Groq's free-tier 30 requests/minute limit.
  * RESUMABLE — already-labeled rows in data/comments.csv are skipped, so you can
    stop/restart safely.
  * INCREMENTAL — each batch is written and flushed immediately; nothing is lost
    on interruption.
  * BACKOFF — on a 429 rate-limit, it waits and retries instead of failing.

IMPORTANT: these labels are TENTATIVE. You must read and correct every row by
hand. `prelabel_original` preserves the model's guess so check_distribution.py
can report your correction rate (your disclosure metric).

Setup:
    pip install -r requirements.txt
    cp .env.example .env   # then add your GROQ_API_KEY
    python prelabel.py
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

INPUT_FILE = Path("data/raw_comments.csv")
OUTPUT_FILE = Path("data/comments.csv")
FIELDS = ["text", "label", "prelabel_original", "notes", "score", "permalink", "source"]

# Deliberately NOT the baseline model (llama-3.3-70b-versatile) — avoids a
# circular comparison between the baseline and labels derived from it.
PRELABEL_MODEL = "openai/gpt-oss-120b"

BATCH_SIZE = 10
PAUSE_BETWEEN_BATCHES = 1.0  # seconds; keeps us well under 30 requests/minute
LABELS = {"analysis", "hot_take", "reaction"}

SYSTEM_PROMPT = """You label r/indieheads music comments. Each comment gets exactly ONE label:

analysis  - a claim backed by SPECIFIC, VERIFIABLE, LOAD-BEARING evidence
            (production/instrumentation detail, music theory, a lyrical reading,
            or discography/historical comparison) that explains HOW or WHY.
hot_take  - a bold, confident JUDGMENT asserted WITHOUT real support. Decorative
            or cherry-picked facts do NOT count as evidence.
reaction  - an immediate EMOTIONAL response anchored to a specific event/moment
            (a release, a concert, news) - a feeling, not a standalone claim.

Tie-break (substance priority): if a comment contains ANY genuine load-bearing
reasoning, label it analysis even if it is emotional. Otherwise, an emotional
in-the-moment response is reaction; a bare judgment is hot_take.

You will receive a numbered list of comments. Respond with ONLY a JSON object of
the form {"labels": ["analysis", "hot_take", ...]} containing one label per
comment, IN ORDER. The array length MUST equal the number of comments."""


def classify_batch(client: Groq, texts: list[str], max_retries: int = 5) -> list[str]:
    numbered = "\n\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    delay = 5.0
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=PRELABEL_MODEL,
                temperature=0,
                max_tokens=2000,  # room for the model's reasoning + JSON output
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": numbered},
                ],
            )
            content = resp.choices[0].message.content or "{}"
            labels = json.loads(content).get("labels", [])
            cleaned = []
            for lab in labels:
                lab = str(lab).strip().lower()
                cleaned.append(lab if lab in LABELS else "UNSURE")
            # align length to the batch (pad/truncate defensively)
            if len(cleaned) < len(texts):
                cleaned += ["UNSURE"] * (len(texts) - len(cleaned))
            return cleaned[: len(texts)]
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "429" in msg or "rate_limit" in msg:
                print(f"    (rate-limited; waiting {delay:.0f}s and retrying)")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            print(f"    ! batch error: {msg} -> marking UNSURE")
            return ["UNSURE"] * len(texts)
    return ["UNSURE"] * len(texts)


def load_done_texts() -> set[str]:
    if not OUTPUT_FILE.exists():
        return set()
    with OUTPUT_FILE.open(encoding="utf-8") as f:
        return {row["text"] for row in csv.DictReader(f)}


def main() -> None:
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        sys.exit("Missing GROQ_API_KEY. Copy .env.example to .env and add your key.")
    if not INPUT_FILE.exists():
        sys.exit(f"Missing {INPUT_FILE}. Run collect.py / parse_local.py first.")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)

    with INPUT_FILE.open(encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    done = load_done_texts()
    todo = [r for r in all_rows if r["text"] not in done]
    print(f"{len(all_rows)} total, {len(done)} already labeled, {len(todo)} to do.")
    if not todo:
        print("Nothing to do. All rows already in data/comments.csv.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUTPUT_FILE.exists()
    with OUTPUT_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        for start in range(0, len(todo), BATCH_SIZE):
            batch = todo[start : start + BATCH_SIZE]
            labels = classify_batch(client, [r["text"] for r in batch])
            for row, label in zip(batch, labels):
                writer.writerow(
                    {
                        "text": row["text"],
                        "label": label,
                        "prelabel_original": label,
                        "notes": "",
                        "score": row.get("score", ""),
                        "permalink": row.get("permalink", ""),
                        "source": row.get("source", ""),
                    }
                )
            f.flush()
            print(f"  labeled {min(start + BATCH_SIZE, len(todo))}/{len(todo)}")
            time.sleep(PAUSE_BETWEEN_BATCHES)

    print(f"\nDone. Wrote {OUTPUT_FILE}.")
    print("NOW: open it and review EVERY label by hand. Edit the `label` column,")
    print("add `notes` for tough cases, and DO NOT touch `prelabel_original`.")


if __name__ == "__main__":
    main()
