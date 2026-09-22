# Data Quality Report — Round 3 Processed Datasets
Generated: 2026-09-22 23:07

---
## whatsapp_privacy_2021_merged_final.csv
- **Rows dropped:** 4,299
- **Issues found & fixed:**
  - Duplicate post_id: 4,254 rows
  - Empty text: 45 rows → dropped
  - Unparseable timestamps: 3,884 rows → set NaT
  - source_name normalized (1 mappings updated)

## telegram_migration_clean.csv
- **Rows dropped:** 0
- No issues found ✓

## whatsapp_backlash_clean.csv
- **Rows dropped:** 0
- **Issues found & fixed:**
  - source_name normalized (1 mappings updated)

## whatsapp_privacy_2021_scored_20260922T085513Z.csv
- **Rows dropped:** 4,299
- **Issues found & fixed:**
  - Duplicate post_id: 4,254 rows
  - Empty text: 45 rows → dropped
  - Unparseable timestamps: 3,884 rows → set NaT
  - Sentiment label/score hard conflicts: 225 (kept, flagged below)
  - source_name normalized (1 mappings updated)

