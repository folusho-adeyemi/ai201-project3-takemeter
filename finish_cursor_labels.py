"""
finish_cursor_labels.py — Apply Cursor-agent labels to remaining rows.

Groq free tier rate-limits pre-labeling; labels here were assigned using the
planning.md taxonomy (Cursor agent, not Groq). Rows marked SKIP are off-topic
(non-music takes) and go to data/dropped.txt.

Run once:  python finish_cursor_labels.py
"""

import csv
from pathlib import Path

OUT = Path("data/comments.csv")
DROPPED = Path("data/dropped.txt")
FIELDS = ["text", "label", "prelabel_original", "notes", "score", "permalink", "source"]

# permalink suffix -> label, or "SKIP"
LABELS: dict[str, str] = {
    # batch 0 — Oliver Tree thread + Cure roast start
    "ortc1k0": "hot_take",
    "ortjr2n": "hot_take",
    "ortz2ol": "hot_take",
    "orwl7zs": "hot_take",
    "ortrom0": "hot_take",
    "orumpab": "hot_take",
    "oruoim0": "reaction",
    "orv0zi2": "hot_take",
    "orxlfyj": "hot_take",
    "orsl9na": "reaction",
    "orsmn77": "hot_take",
    "orsmxa8": "hot_take",
    "eoniw65": "hot_take",
    "eoo24aa": "hot_take",
    "eong630": "hot_take",
    "eooea9v": "reaction",
    "eopb0dh": "hot_take",
    "eonga1n": "hot_take",
    "eons6h4": "hot_take",
    "eoo1rt8": "hot_take",
    "eooiu0p": "hot_take",
    "eonzppk": "hot_take",
    "eong9rn": "hot_take",
    "eongjz1": "hot_take",
    "eonhahz": "SKIP",
    # batch 1 — Cure roast
    "eonl2br": "hot_take",
    "eoni32a": "reaction",
    "eonhtkl": "reaction",
    "eoo66rt": "SKIP",
    "eonh6q8": "SKIP",
    "eonl291": "SKIP",
    "eoq2t54": "SKIP",
    "eons4x4": "hot_take",
    "eook0j3": "hot_take",
    "eoni2q2": "hot_take",
    "eoncj4g": "analysis",
    "eonkotc": "hot_take",
    "eons3bn": "hot_take",
    "ep1xvhx": "hot_take",
    "eonor3x": "hot_take",
    "eonzzmx": "hot_take",
    "eonj48o": "hot_take",
    "eoohupc": "hot_take",
    "eonda8y": "hot_take",
    "eonhhs5": "hot_take",
    "eonpsea": "hot_take",
    "eonij2f": "hot_take",
    "eonkzhe": "hot_take",
    "eoo2iv5": "hot_take",
    "eoniv0v": "hot_take",
    # batch 2 — Cure roast end + daily discussion
    "eonsalj": "hot_take",
    "eongvm0": "hot_take",
    "eonpdof": "hot_take",
    "eons7ia": "hot_take",
    "eooiknj": "reaction",
    "eonrd5b": "hot_take",
    "eooh0n4": "hot_take",
    "eopp9dy": "hot_take",
    "eop9p3x": "hot_take",
    "eougg8w": "hot_take",
    "ep6o1xg": "hot_take",
    "ostzdob": "analysis",
    "ostpj50": "reaction",
    "ostad8x": "analysis",
    "osta2do": "reaction",
    "ost6qws": "SKIP",
    "osubicy": "SKIP",
    "osuos6s": "SKIP",
    "osuh934": "SKIP",
    "osst41t": "analysis",
    "ossp644": "hot_take",
    "ost6teb": "SKIP",
    "ostgi2t": "hot_take",
    "osst3sb": "SKIP",
    "ossmx7g": "reaction",
    # batch 3 — daily discussion
    "ossweuy": "reaction",
    "ost6ao1": "hot_take",
    "ossjcw9": "analysis",
    "ostuzny": "hot_take",
    "osvbnmc": "reaction",
    "ostvijb": "reaction",
    "ostadql": "hot_take",
    "ostvwke": "analysis",
    "ost6tbz": "reaction",
    "ostwp27": "analysis",
    "osscvus": "hot_take",
    "ossc94b": "hot_take",
    "oss8f4o": "analysis",
    "ossly8d": "hot_take",
    "ost8gws": "hot_take",
    "ostaefx": "hot_take",
    "oss5o9j": "reaction",
    "osuhcym": "reaction",
    "osumidk": "reaction",
    "osti21a": "reaction",
    "ossck52": "hot_take",
    "ossh7nk": "reaction",
    "oss5w72": "hot_take",
    "ossczum": "hot_take",
    "ossegp1": "reaction",
    # batch 4
    "ossg96s": "hot_take",
    "ossgpv5": "SKIP",
    "ost3lj4": "SKIP",
    "oss16yf": "reaction",
    "oss9z7z": "reaction",
    "osrylfx": "analysis",
    "ossa5qz": "hot_take",
    "oss4dhb": "analysis",
    "oss4kjz": "hot_take",
    "oss579d": "analysis",
    "osrx52e": "hot_take",
    "ossqph6": "hot_take",
    "ossa86y": "hot_take",
    "ossrjhi": "hot_take",
    "ostsow6": "SKIP",
    "ossvk0m": "SKIP",
    "ossrvcl": "reaction",
    "ostsjoe": "SKIP",
    "ostvj92": "SKIP",
    "osukl21": "SKIP",
    "oryzmtg": "hot_take",
    "os37tb0": "reaction",
    "os8ntsx": "reaction",
    "orzfvvj": "hot_take",
    "os0bnjt": "reaction",
    # batch 5
    "os2tv81": "reaction",
    "os1pate": "reaction",
    "os9xg7i": "hot_take",
}


def permalink_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def main() -> None:
    raw = list(csv.DictReader(Path("data/raw_comments.csv").open(encoding="utf-8")))
    done = {permalink_id(r["permalink"]) for r in csv.DictReader(OUT.open(encoding="utf-8")) if OUT.exists()}
    new_file = not OUT.exists()
    added, skipped = 0, 0

    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()

        for row in raw:
            pid = permalink_id(row["permalink"])
            if pid in done:
                continue
            label = LABELS.get(pid)
            if label is None:
                print(f"  ! no label for {pid} — add to LABELS dict")
                continue
            if label == "SKIP":
                with DROPPED.open("a", encoding="utf-8") as df:
                    df.write(row["permalink"] + "\n")
                skipped += 1
                continue
            w.writerow(
                {
                    "text": row["text"],
                    "label": label,
                    "prelabel_original": label,
                    "notes": "",
                    "score": row.get("score", ""),
                    "permalink": row["permalink"],
                    "source": row.get("source", ""),
                }
            )
            added += 1

    print(f"Added {added} rows, skipped {skipped} off-topic.")
    print("Run: python check_distribution.py")


if __name__ == "__main__":
    main()
