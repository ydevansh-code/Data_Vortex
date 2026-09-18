# Decisions Log — Social Engine / Data Vortex Hackathon

> **Purpose**: Record all data cleaning decisions, imputation strategies, dropped records, and assumptions with mathematical and statistical justification.

---

## 1. Corruption Patterns Found in Raw Data

| Dataset | Column | Pattern Detected | Detection Method | Severity & Impact |
|---------|--------|------------------|------------------|-------------------|
| Users | `account_created` | Unix epoch timestamps mixed with ISO-8601 strings | Regex & numeric casting inspection | High — parsed to standard `YYYY-MM-DD` |
| Users | `follower_count` | Negative values / corrupted strings / missing entries | Numeric bounds check | Medium — median imputed, negatives clipped |
| Users | `location` | Trailing spaces, mixed casing | String inspection | Low — stripped & standardized |
| Posts | `platform` | Placeholder strings (`NULL`, `None`, `?`), 1,219 missing | Categorical frequency check | High — filtered to 5 valid platforms |
| Posts | `text_content` | HTML tags (`<b>`, `<p>`), HTML entities (`&amp;`, `&quot;`), mojibake (`Ã©`) | Regex regex pattern scan | High — cleaned via HTML/entity stripping |
| Posts | `timestamp` | Tri-modal formats: ISO-8601, `DD-MM-YYYY`, and Unix epoch seconds | Composite date parser | High — converted to uniform `YYYY-MM-DDTHH:MM:SS` |
| Posts | `likes` / `shares` / `comments` | Numeric string placeholders and 1,858 missing records | Type coercion & null check | Medium — median imputation applied |
| Posts | `post_id` | 360 duplicate post entries | `post_id` frequency check | Medium — deduplicated keeping first instance |

---

## 2. Cleaning & Imputation Decisions

### Placeholder Replacement
- **Decision**: Replace all sentinel strings (`N/A`, `none`, `null`, `NULL`, `?`, `-`, `unknown`) with proper `np.nan`.
- **Justification**: These strings are data-entry artefacts. Coercing to `np.nan` ensures correct type inference in downstream statistical operations. Validated via regex exact-string matching (e.g., `^\s*-\s*$`) to ensure in-text hyphens in legitimate text were preserved.

### Numeric Columns — Median Imputation
- **Decision**: Impute missing values in numeric columns (`follower_count`, `likes`, `shares`, `comments`) with the column **median**.
- **Justification**: Engagement metrics are heavily skewed with fat-tail distributions. The median is resistant to outliers (e.g. viral posts), preventing bias propagation (Little & Rubin, 2002).

### Categorical Columns — Explicit Null Preservation & Flagging
- **Decision**: For `platform` and `text_content`, preserve `NaN` / flag invalid categories with an indicator column rather than imputing arbitrary values.
- **Justification**: Imputing text content or platform names where no clear dominant category exists (>30% mode threshold) would introduce phantom signal and synthetic bias.

### Multi-Format Timestamp Parsing
- **Decision**: Implement a 3-tier date parser: (1) Unix epoch seconds, (2) Day-first `DD-MM-YYYY`, (3) ISO-8601 strings.
- **Justification**: Captures 100% of valid timestamps across heterogeneous logging sources without data loss.

---

## 3. Rows / Columns Dropped

| Stage | Dataset | Target | Count Dropped | Reason |
|-------|---------|--------|---------------|--------|
| Deduplication | Posts | Duplicate `post_id` | 360 rows | Exact duplicates produced during data transmission retry |
| Standardization | Text | HTML tags / entities | 11,164 cells | Cleaned noisy formatting markup from scraped content |

---

## 4. Deliverables → Evaluation Criteria Mapping

| Deliverable | Evaluation Criterion Addressed |
|-------------|-------------------------------|
| `src/clean_data.py`, `src/run_cleaning.py` | Data Handling & Preprocessing Logic |
| `docs/decisions.md`, `docs/change_log.csv` | Data Cleaning Accuracy & Auditability |
| `reports/raw_profile.html`, `reports/cleaned_profile.html` | Data Consistency & Standardisation |
| `docs/profiling_comparison.md` | Data Consistency & Standardisation |
| `notebooks/eda.ipynb`, `reports/eda_summary.md` | EDA Depth & Insight Discovery |
| `reports/figures/`, markdown commentary | Insight Interpretation & Clarity |
| `README.md`, docstrings, modular pipeline | Code Quality & Documentation |


# Data Vortex Phase 2: Decisions & Statistical Assumptions

> **Purpose**: Record all logic, filtering thresholds, and schema decisions made during Phase 2 to ensure complete transparency and auditability.

---

## 1. Schema Design & Data Integrity Rules
- **Relational Integrity**: The dataset was normalized into a star-schema equivalent (`users` and `posts`) using SQLite, enforcing `FOREIGN KEY` constraints. Orphan posts were checked and zero were found.
- **Strict Data Types**: Constraints such as `CHECK(shares >= 0)` and `CHECK(comments >= 0)` were applied.
- **Preservation of Raw State**: We deliberately *did not* clip negative likes or remove missing platforms during data load. Modifying data during the ETL load process constitutes "data fabrication". Instead, we loaded the exact artifacts from Phase 1 and applied analytical filters in SQL dynamically.
- **Virtual Engagement View**: Created `v_post_engagement` to calculate total engagement (`likes + shares + comments`). SQLite treats `NULL + number = NULL`. To prevent cascading data loss, we applied `COALESCE` to ensure robust math operations.

## 2. Row Exclusion Logic per Query
To ensure accurate statistical representation without bias, explicit `WHERE` clauses were used.

### E3 (Platform Averages), H3 (Platform Outliers), and Trend Bonus
- **Condition**: `WHERE platform IS NOT NULL AND likes >= 0`
- **Exclusion Count**: 1,784 rows dropped due to `NULL` platforms. An additional 421 rows dropped due to negative likes (imputation artifacts from Phase 1). Total dataset evaluated: **9,795 posts**.
- **Justification**: A platform average cannot include posts without a platform. Negative likes distort aggregations.

### M1 (Location Engagement)
- **Condition**: `WHERE likes >= 0`
- **Exclusion Count**: 509 rows dropped due to negative likes. Total dataset evaluated: **11,491 posts**.
- **Justification**: Since M1 analyzes geographic location, `platform IS NULL` posts were retained as they still represent valid geographic engagement.

## 3. Transition from Phase 1 Weighted Score to Phase 2 Simple Sum
In Phase 1, we defined Engagement Score as `0.5*Likes + 0.3*Shares + 0.2*Comments` to penalize click-farm inflation.
In Phase 2, we transitioned to a simple sum (`Likes + Shares + Comments`).
**Justification**: The Phase 2 problem statements define engagement explicitly as `likes + shares + comments`. Adhering to client/competition definitions supersedes exploratory models.

## 4. The H3 "Zero Result" Insight (Statistical Impossibility)
For question H3, we were asked to find posts where engagement is $> 2 \times \text{Platform Average}$.
- **Result**: 0 rows returned.
- **Statistical Insight**: This occurs because the synthetic dataset follows a roughly uniform distribution within strict boundaries (Likes cap at 5000, Shares at 2000, Comments at 1000). The mathematical maximum engagement possible is 8,000. The mean across all platforms sits roughly around 4,000. Therefore, the absolute maximum value is physically incapable of exceeding twice the mean ($8000 < 2 \times 4000$).
- **Action Taken**: We provided the exact literal query to prove the mathematical constraint, and offered a supplementary `PERCENT_RANK()` query to identify the top 5% performers relative to their platform, providing actionable business value despite dataset limitations.
