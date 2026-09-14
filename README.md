# Data Vortex — Social Engine Hackathon

> **Team: Event Horizon**
> **Research Institute Dataset Recovery, Cleaning & Advanced Exploratory Data Analysis Pipeline**

---

## Quick Start (One Command)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the complete recovery & cleaning pipeline
python src/run_pipeline.py
```

**Outputs**: `data/cleaned/users_clean.csv`, `data/cleaned/posts_clean.json`, `data/cleaned/merged_summary.csv`
**EDA report**: Open `notebooks/eda.ipynb` to view charts and interpretations.

This automated workflow executes:
1. **Raw Profiling** → `reports/raw_profile.html`
2. **Multi-Table Data Cleaning & Harmonization** → `data/cleaned/` (`users_clean.csv`, `posts_clean.csv`, `merged_summary.csv`)
3. **Cleaned Profiling & Association Analysis** → `reports/cleaned_profile.html`, `reports/comparison_profile.html`
4. **Statistical EDA & Visualization Suite** → `reports/figures/`, `docs/eda_summary.md`, `notebooks/eda.ipynb`

To skip heavy HTML profiling reports for quick execution:
```bash
python src/run_pipeline.py --skip-profile
```

---

## Project Structure

```
Data_Vortex/
├── data/
│   ├── raw/                   # Corrupted source datasets (users_raw.csv, posts_raw.csv)
│   └── cleaned/               # Recovered & harmonized output datasets
│       ├── users_clean.csv    # Cleaned user profiles (1,501 rows)
│       ├── posts_clean.csv    # Cleaned social posts (12,000 rows)
│       └── merged_summary.csv # User-level aggregated engagement metrics
├── docs/
│   ├── decisions.md           # Statistical justifications & imputation rationale
│   ├── recovery_notes.md      # Investigation of corrupted raw formats
│   ├── profiling_comparison.md# Before vs. after data quality audit
│   └── change_log.csv         # Machine-readable transformation audit log
├── notebooks/
│   └── eda.ipynb              # Comprehensive interactive EDA notebook
├── reports/
│   ├── figures/               # Generated high-resolution publication charts
│   ├── raw_profile.html       # Automated sweetviz profile of raw data
│   ├── cleaned_profile.html   # Automated sweetviz profile of cleaned data
│   ├── comparison_profile.html# Automated side-by-side comparison report
│   └── eda_summary.md         # Plain-language EDA report with business recommendations
├── src/
│   ├── __init__.py
│   ├── clean_data.py          # Core 7-stage cleaning engine
│   ├── run_cleaning.py        # Multi-table cleaning & aggregation orchestrator
│   ├── run_pipeline.py        # Master pipeline CLI runner
│   ├── profile_data.py        # Profiling report generator
│   ├── generate_eda_report.py # Automated statistical visualization & markdown reporter
│   └── inspect_raw.py         # Diagnostic data inspection utility
├── requirements.txt           # Pinned dependencies
└── README.md                  # Project overview & evaluation mapping
```

---

## Evaluation Criteria Mapping

| Criterion | Addressed In | Implementation Highlights |
|-----------|--------------|---------------------------|
| **1. Data Cleaning Accuracy** | `src/clean_data.py`, `docs/decisions.md` | Accurate multi-tier date parsing, regex HTML/mojibake stripping, outlier-resistant median imputation |
| **2. Data Handling & Preprocessing Logic** | `src/run_cleaning.py`, `src/clean_data.py` | 7-stage pipeline (Load → Validate → Placeholders → Missing → Standardize → Deduplicate → Export) |
| **3. EDA Depth & Insight Discovery** | `notebooks/eda.ipynb`, `docs/eda_summary.md` | Follower vs. engagement independence, cross-platform conversions, hashtag clustering, geo-demographic patterns |
| **4. Data Consistency & Standardisation** | `docs/profiling_comparison.md`, `data/cleaned/` | ISO 8601 timestamps, uniform category enums, normalized float/int columns, 100% duplicate elimination |
| **5. Code Quality & Documentation** | `src/`, `README.md`, `docs/` | Modular functions, PEP-8 compliance, comprehensive docstrings, zero hardcoded absolute paths |
| **6. Insight Interpretation & Clarity** | `docs/eda_summary.md`, `reports/figures/` | Actionable recommendations for research institutes, clear visual storytelling with charts |

---

## Key Findings Summary

1. **Follower Count vs. Engagement Independence**: Follower count exhibits near-zero correlation ($r \approx 0.00$) with engagement score. Platform algorithms prioritize content resonance and watch/read time over account follower volume.
2. **Platform Engagement Divergence**:
   - **YouTube & Instagram**: Highest raw volume of likes per post.
   - **Twitter & Reddit**: Highest share-to-like velocity and discussion density.
   - **Facebook**: Stable community retention and comments.
3. **Global Geographic Footprint**: User base is balanced across global tier-1 cities (London, New York, Tokyo, São Paulo, Paris) with even language representation.
4. **Clean Recovery Rate**: 100% of uncorrupted records retained, 360 duplicate posts removed, and all multi-format timestamps normalized to ISO 8601.
