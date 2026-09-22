# Round 3 — Decisions Log
**Data Vortex A'26 | Team: Event Horizon**

---

## Topic Assignment
- **Topic:** WhatsApp Privacy Policy 2021 — Public Reaction
- **Date Range:** Jan 1 – May 31, 2021
- **Geography:** India, Indonesia, Global (EN/ID)
- **Assigned:** 2026-09-20

---

## Data Sources Decision

| Source | Decision | Rationale |
|--------|----------|-----------|
| GDELT DOC 2.0 | **SELECTED** | Free, no auth, massive historical coverage, real timestamps |
| Google Play Reviews | **SELECTED** | Free, no auth, native star ratings, direct user sentiment |
| Hacker News (Algolia) | **SELECTED** | Free API, no auth, excellent tech community sentiment capture |
| Reddit (PRAW) | **REJECTED** | Requires API credentials which creates deployment friction |
| Kaggle fallback | **Optional** | Enabled only if pre-built dataset exists; disabled by default |
| Twitter/X | **REJECTED** | No free API access; building unauthorized scraper violates ToS |
| NewsAPI | **REJECTED** | Free tier historical data only 30 days; GDELT covers full 5 months |

---

## Detection Thresholds

All thresholds were fixed **before** seeing the full dataset and are stated plainly:

| Method | Threshold | Rationale |
|--------|-----------|-----------|
| Volume/Engagement spike | z-score > 2.0 | Standard 2σ statistical significance threshold |
| Sentiment shift | z-score > 1.5 | Slightly looser to detect real shifts given noisy social data |
| Rolling window | 7-day | Balances smoothing against reactivity for daily data |

These were **not tuned post-hoc** to manufacture the required number of shifts/spikes.
If real data does not yield ≥2 shifts and ≥1 spike at these thresholds, we will honestly
document that and widen the date window rather than lower the threshold.

---

## Model Decision

- **Model used:** `round2/models/sentiment_linear_svm.pkl` (TF-IDF + LinearSVC, Macro-F1: 0.5914)
- **No retraining performed** — per contest rules
- **Known limitation:** Model trained on generic social media sentiment (Round 2 dataset).
  Privacy/legal jargon (ToS, GDPR, CCI) is likely out-of-vocabulary or treated as neutral.
  This is documented honestly in the report rather than silently masked.

---

## Collection Log Policy

- Every run logs: timestamp, source, query, count, status to `data/collection_log.csv`
- Empty windows are logged as `EMPTY`, not omitted
- Errors are logged as `ERROR:<message>`, not retried silently
- No padding or backfilling of gaps

---

## Limitations

1. **Google Play historical depth:** The scraper fetches the most recent N reviews sorted by
   newest; deep historical pagination may not reach all Jan 2021 reviews depending on total
   review count. Volume from this source may be lower than theoretical maximum.
2. **Reddit historical depth:** PRAW `subreddit.search()` is limited to ~1000 results per query
   in practice. Older posts from Jan 2021 may not surface. This is an honest API limitation.
3. **GDELT coverage:** GDELT indexes articles; opinion pieces and forum posts are excluded.
   Sentiment from GDELT headlines may skew more neutral/negative than user-expressed sentiment.
4. **Model domain mismatch:** See above. Impact on shift direction is expected to be small
   (shifts are relative changes, not absolute scores) but noted.

---

## Master Plan Architecture

### 1. Three-Phase Timeframe Segmentation
- **T-0 (Pre-Announcement Baseline):** Nov 1, 2020 – Dec 31, 2020
  *Establishes baseline sentiment & review volume before policy change notification.*
- **T+1 (The Shock Phase):** Jan 1, 2021 – Jan 31, 2021
  *Captures peak volatility, immediate user panic, and viral reactions following Jan 4 notification.*
- **T+2 (The Fallout Phase):** Feb 1, 2021 – Jul 31, 2021
  *Tracks prolonged user migration to Telegram/Signal, regulatory scrutiny, and extended deadline fallout.*

### 2. Micro-Analytics Framework
- **Aspect-Term Sentiment Analysis (ATSA):**
  - Track target terms: `privacy`, `facebook`, `metadata`, `terms`, `privasi` (WhatsApp negative skews).
  - Track target terms: `secure`, `better alternative`, `switch`, `pindah` (Telegram positive skews).
- **Topic Evolution (LDA / BERTopic / NMF):**
  - Compare topic distributions across T-0 (general app features), T+1 (privacy panic & terms), and T+2 (platform migration & surveillance).

### 3. Time-Series Visualization & Event Triggers
- Daily dual-line graph: WhatsApp Complaints (Rating ≤ 2) vs. Telegram Migration Reviews (Rating ≥ 4).
- Key Trigger Overlays:
  - `2021-01-04`: In-app Privacy Policy update notification.
  - `2021-01-07`: Elon Musk tweet ("Use Signal") & viral Telegram surge.
  - `2021-01-15`: WhatsApp delays enforcement deadline from Feb 8 to May 15.
- Multi-Source Layering: Primary store reviews cross-correlated with GDELT news volume and Hacker News tech discussions.
