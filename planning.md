# TakeMeter — planning.md

> A text classifier that sorts r/indieheads comments into the *kind of take* they are:
> a real argument, a bare opinion, or an in-the-moment reaction.
> This document is written **before** any data is collected or labeled.
> It will be updated before starting any stretch feature.

---

## 1. Community

**Chosen community:** [r/indieheads](https://www.reddit.com/r/indieheads/) — a large, active subreddit for indie and alternative music discussion.

**Why this community.** Music discourse on r/indieheads spans the full quality range we care about: long, evidenced breakdowns of production and songwriting sit right next to bare one-line opinions and pure emotional release-day reactions. The community itself already polices this distinction — members call each other out for "just stating a take" versus "actually making a point," which means the labels are *grounded in real community norms*, not imposed from outside.

**Why it's a good fit for classification.** The discourse is text-heavy (comment threads, not images/links) and genuinely *varied in quality*, so the labels carve out meaningful distinctions rather than separating obvious categories. Crucially, the variety is wide enough that no single label trivially dominates, which is what makes the task non-trivial and the failure analysis interesting.

**Unit of classification.** We classify **individual opinion-bearing comments**, not top-level posts. Comments are where opinions actually live, and scoping to opinion threads keeps us out of the "other" bucket (see §4).

---

## 2. Label taxonomy

Three mutually exclusive labels. The decision tell for each is the one-line test we apply during annotation.

### `analysis`
**Definition:** A claim about music supported by *specific, verifiable, load-bearing* evidence — production/instrumentation details, music theory, a lyrical reading, or a discography/historical comparison — that explains *how or why* the claim is true.
**Decision tell:** Strip away the opinion and a real reason still stands on its own.

*Examples:*
1. "The whole record is built on detuned Rhodes chords sitting just behind the beat — that drag is why it feels narcotic, the same thing Portishead did on *Dummy*."
2. "People call the mix muddy, but it's intentional: the vocals are buried under tape saturation so the album sounds like a half-remembered memory, which is the entire lyrical theme of the record."

### `hot_take`
**Definition:** A bold, confident *judgment* asserted without genuine support. The claim may well be true, but the comment tells you the conclusion and never the reasoning. Decorative or cherry-picked facts do **not** count as support.
**Decision tell:** It gives you the verdict but never the *why*.

*Examples:*
1. "This is the best album of the decade and anyone who disagrees doesn't get music."
2. "Radiohead is the most overrated band of all time and *OK Computer* is boring."

### `reaction`
**Definition:** An immediate *emotional* response anchored to a specific event or moment (a release, a concert, a piece of news) — a feeling expressed in the moment, not a standalone evaluative claim.
**Decision tell:** Emotional language plus an event/time anchor ("just heard," "last night," "vinyl arrived").

*Examples:*
1. "vinyl just arrived, dropped the needle, and I'm fully in tears on my kitchen floor"
2. "the new Beach House track came on shuffle and I had to pull over. holy."

---

## 3. Hard edge cases & decision rules

Mutual exclusivity is enforced by a **substance priority** tie-break: `analysis` > `hot_take` > `reaction`. When a comment plausibly fits more than one label, the highest-priority label that genuinely applies wins.

### Edge case A — `analysis` vs `hot_take` (the central boundary)
A take dressed up with a fact.
> "Boygenius is overrated — they got a 9.0 on Pitchfork but not one of them can write a real bridge."

**Rule:** Label `analysis` *only if* the evidence is specific, verifiable, **and load-bearing** — i.e., it explains *why* the claim holds. If the fact is decorative, cherry-picked, or just jargon name-dropping ("the mix is muddy," "no real bridge") with no explanation of how/why, it's a `hot_take`. → The example above is **`hot_take`** (the score is decoration; "can't write a bridge" is asserted, not shown).

### Edge case B — `reaction` vs `hot_take`
Both are short and opinionated.
> "album of the year, not close"  vs.  "album of the year just dropped and I'm SHAKING, holy"

**Rule:** A *standalone evaluative judgment* about the music → `hot_take`. An *emotional response anchored to the listening/event moment* (temporal anchor + feeling language) → `reaction`. → First is **`hot_take`**, second is **`reaction`**.

### Edge case C — the substance tie-break in action (`analysis` vs `reaction`)
An emotional comment that also contains a genuine argument.
> "Saw them live last night and I was wrecked — and hearing it live made me realize the bridge modulates up a third, which is exactly what gives that lift on the recording."

**Rule:** Substance priority promotes any comment containing genuine, load-bearing reasoning to `analysis`, regardless of emotional framing. → **`analysis`**.
*Known risk:* a mostly-emotional comment with one buried real reason will be labeled `analysis`; we accept this for annotation consistency and will watch for it in error analysis.

### Documented hard cases from real data (annotation)

**Hard case 1 — `analysis` vs `hot_take` (Cure roast thread):**
> "Pornography can be a difficult album to get into, but you just have to realize that drum machines were very primitive back then."

Could be `hot_take` (casual aside) or `analysis` (production/historical context explains accessibility). **Decision:** `analysis` — the drum-machine detail is load-bearing for *why* the album is hard to enter.

**Hard case 2 — `reaction` vs `hot_take` (Cure roast / dedupe conflict):**
> "the only thing they've cured is my insomnia (but seriously tho does anyone have good tips for getting to sleep…)"

Roast joke + personal aside. **Decision:** `hot_take` in final dataset (dedupe kept first row); could be `reaction` if treating the insomnia line as in-the-moment aside.

**Hard case 3 — `reaction` vs `hot_take` (Tiny Desk, test set):**
> "I love this band, and I even got to attend their Tiny Desk. It kicked ass."

Event-anchored positive experience vs bare opinion. **Decision:** `reaction`. Both fine-tuned and baseline models predicted `hot_take` — validates that this boundary is hard.

---

## 4. Data collection plan

**Source.** Comments scraped from r/indieheads via the **official Reddit API (PRAW)** — free, rule-compliant, and scriptable. We pull from threads where people express views: daily discussion threads, new-release "rate this album" / megathreads, "unpopular opinions" threads, and comment sections under reviews. This scoping is deliberate — it's what keeps ≥90% of collected comments cleanly labelable without an "other" bucket.

**Size & split.** At least **200 labeled comments**, split into **train / validation / test** (target ~70 / 15 / 15). The test set is held out and never seen during training.

**Target distribution.** A **floor of ~25% per label** (≈50+ each out of 200), so no label exceeds ~50% and the ≤80% rule has comfortable margin. We expect `analysis` to be the rarest (it takes effort to write) and `hot_take` / `reaction` to be abundant.

**Underrepresentation fallback (targeted collection).** If a label runs short after an initial sweep:
- short on `analysis` → mine review / essay / "album appreciation" threads, where evidenced writing concentrates;
- short on `reaction` → mine release-day megathreads, where in-the-moment reactions concentrate;
- short on `hot_take` → mine "unpopular opinion" / ranking threads.

---

## 5. Evaluation metrics

Accuracy alone is insufficient here because the data is imbalanced and `analysis` is the rare, hard class — a majority-class predictor could post decent accuracy while being useless at the distinction we care about. We therefore report:

- **Macro-F1 (headline metric).** Averages F1 across the three classes *equally*, so the rare `analysis` class counts as much as the common ones. This is the honest summary for a task that deliberately cares about the hard minority class.
- **Overall accuracy.** Required and reported, but read alongside macro-F1, not on its own.
- **Per-class precision & recall** for every label. For `analysis`: precision answers "when it predicts analysis, is it right?" (over-calling); recall answers "of real analysis comments, how many did it catch?" (missing real arguments).
- **Confusion matrix.** The centerpiece of the analysis — it reveals *which* classes get swapped. Expected hotspot: `analysis` ↔ `hot_take` (Edge case A).

Both the fine-tuned model and the zero-shot Groq baseline are evaluated on the **same held-out test set**.

---

## 6. Definition of success

A composite criterion, chosen so we can objectively determine at the end whether we hit it:

1. **Beats the baseline by a real margin:** fine-tuned macro-F1 ≥ zero-shot baseline macro-F1 **+ 0.10**. (This is the actual test of whether fine-tuning helped.)
2. **Absolute floor:** fine-tuned **macro-F1 ≥ 0.70**.
3. **No collapsed class:** **per-class F1 ≥ 0.55** for *every* label — so the model isn't just good at the easy classes.
4. **Sanity ceiling:** if macro-F1 **> 0.95**, treat it as a red flag and audit for test-set leakage or labels that are too easy, *before* claiming success.

"Good enough for deployment" in a real community tool means all of (1)–(3) hold and (4) does not trip. 200 examples on a subjective task makes ~0.65–0.80 macro-F1 the realistic landing zone, so these thresholds are ambitious but attainable.

---

## 7. AI Tool Plan

This project has no implementation code to generate, so AI tools are used in the three places where they actually help on a labeling task.

### Label stress-testing (done before annotation)
We generated boundary comments with an AI tool and ran them through the §2–§3 rules to confirm the taxonomy is *decidable*. All test cases resolved without a coin-flip (including the analysis-with-a-buried-fact and the emotional-comment-with-an-argument cases), so the definitions are committed. We will re-run this if real data exposes a new ambiguous pattern.

### Annotation assistance (pre-labeling — with explicit safeguards)
We **will** use an LLM to pre-label a batch, then review every label by hand. To protect the integrity of the baseline comparison:
- **Pre-label with a *different* model than the baseline.** The baseline is Groq `llama-3.3-70b-versatile`; pre-labeling uses a *different* model so gold labels aren't just "what the baseline already thinks" (avoids a circular comparison).
- **The test set is hand-adjudicated.** Both models are scored on it, so its labels are reviewed fully manually rather than trusted from the pre-labeler.
- **Track the correction rate.** We record the fraction of pre-labels we changed — both as a disclosure figure and as a check that we were genuinely reviewing, not rubber-stamping.
- **Disclosure.** Which examples were pre-labeled, by which model, and the correction rate are all documented in the README's AI-usage section.
*Accepted risk:* pre-labeling introduces anchoring bias; the safeguards above bound it but don't eliminate it.

### Failure analysis (after evaluation)
We will hand the list of the model's wrong predictions to an AI tool and ask it to surface *systematic* patterns (e.g., "misclassifies short analysis as hot_take," "treats jargon as evidence"). Every proposed pattern is then **verified manually** against the actual misclassified comments before it goes in the evaluation report — the AI proposes, we confirm.

---

## 8. Stretch features (decided per-feature before starting)

Candidates, in rough priority order; planning.md will be updated before any is begun:
- **Error pattern analysis** — promote the §7 failure-analysis step into a named systematic finding.
- **Confidence calibration** — check whether the fine-tuned model's confidence scores are meaningful (does 90%-confident beat 60%-confident?).
- **Inter-annotator reliability** — a second annotator labels 30+ examples; report Cohen's kappa and analyze disagreements.
- **Deployed interface** — a small app that takes a new comment and shows the predicted label + confidence.

---

## Status
- [x] Milestone 1 — label taxonomy, edge cases, decision rules
- [x] Milestone 2 — this planning.md (all six questions + AI Tool Plan)
- [x] Milestone 3 — data collection & annotation (468 unique labels; minimal hand review)
- [x] Milestone 4 — Groq zero-shot baseline on test set (acc 0.451, macro-F1 0.37)
- [x] Milestone 5 — fine-tuning DistilBERT (acc 0.521, macro-F1 0.23; majority-class collapse)
- [x] Milestone 6 — README evaluation report (demo video: pending user recording)
