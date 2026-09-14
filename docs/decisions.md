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
