"""
collect.py — Pull opinion-bearing comments from curated r/indieheads threads.

No Reddit API credentials needed: this uses Reddit's public ".json" view of each
thread. Put one thread URL per line in data/threads.txt, then run:

    python collect.py

Output: data/raw_comments.csv  (columns: text, score, author, permalink, source)
This raw file is git-ignored. Next step is prelabel.py.
"""

import csv
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

# ---- Config (tweak as needed) ------------------------------------------------
THREADS_FILE = Path("data/threads.txt")
OUTPUT_FILE = Path("data/raw_comments.csv")

MIN_WORDS = 8           # skip very short comments (unlikely to be a real "take")
MAX_WORDS = 250         # skip essays that are awkward to label as one unit
MAX_PER_THREAD = 60     # spread collection across threads, don't drain one
TARGET_TOTAL = 280      # collect a buffer above 200 so you can drop bad rows
REQUEST_DELAY_SEC = 2.0 # be polite to Reddit between requests
SKIP_AUTHORS = {"AutoModerator", "[deleted]"}

# Reddit 403s obvious bot/default user-agents; a real browser UA is far more
# reliable from a residential IP.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
# -----------------------------------------------------------------------------


def read_thread_urls(path: Path) -> list[str]:
    if not path.exists():
        sys.exit(f"Missing {path}. Add thread URLs (one per line) first.")
    urls = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    if not urls:
        sys.exit(f"No thread URLs found in {path}. Add some (one per line).")
    return urls


def to_json_url(url: str, host: str = "www.reddit.com") -> str:
    url = url.split("?")[0].rstrip("/")
    if not url.endswith(".json"):
        url += ".json"
    # rebuild with the chosen host using just the path (so we can retry on
    # old.reddit.com if www is refused, without mangling the hostname)
    path = urlparse(url).path
    return f"https://{host}{path}"


def walk_comments(children: list) -> list[dict]:
    """Recursively flatten a Reddit comment tree into individual comments."""
    out = []
    for child in children:
        if child.get("kind") != "t1":  # t1 = comment; skip "more" stubs, etc.
            continue
        data = child.get("data", {})
        out.append(data)
        replies = data.get("replies")
        if isinstance(replies, dict):
            grandkids = replies.get("data", {}).get("children", [])
            out.extend(walk_comments(grandkids))
    return out


def is_usable(body: str, author: str) -> bool:
    if not body:
        return False
    if body in ("[deleted]", "[removed]"):
        return False
    if author in SKIP_AUTHORS:
        return False
    n_words = len(body.split())
    if n_words < MIN_WORDS or n_words > MAX_WORDS:
        return False
    return True


def fetch_thread(url: str) -> list[dict]:
    resp = None
    for host in ("www.reddit.com", "old.reddit.com"):
        resp = requests.get(to_json_url(url, host), headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            print(f"  ! Rate-limited (429) on {host} — waiting 30s and retrying once.")
            time.sleep(30)
            resp = requests.get(to_json_url(url, host), headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            break
        print(f"  ! {host} returned HTTP {resp.status_code}; trying next host...")
    if resp is None or resp.status_code != 200:
        print(f"  ! Skipping {url} — all hosts refused.")
        return []
    payload = resp.json()
    # payload[0] = the post listing, payload[1] = the comments listing
    comment_children = payload[1].get("data", {}).get("children", [])
    return walk_comments(comment_children)


def main() -> None:
    urls = read_thread_urls(THREADS_FILE)
    print(f"Reading {len(urls)} thread(s)...\n")

    seen_ids: set[str] = set()
    seen_text: set[str] = set()
    rows: list[dict] = []

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            comments = fetch_thread(url)
        except Exception as exc:  # noqa: BLE001 — keep going on a bad thread
            print(f"  ! Error: {exc}")
            comments = []

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
                    "source": url,
                }
            )
            kept += 1
        print(f"  + kept {kept} comments (running total: {len(rows)})")

        if len(rows) >= TARGET_TOTAL:
            print(f"\nReached target of {TARGET_TOTAL}; stopping early.")
            break
        time.sleep(REQUEST_DELAY_SEC)

    if not rows:
        sys.exit("\nNo comments collected. Check your URLs / try manual collection.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "score", "author", "permalink", "source"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Wrote {len(rows)} comments to {OUTPUT_FILE}.")
    print("Next: run prelabel.py to get tentative labels, then review them by hand.")


if __name__ == "__main__":
    main()
