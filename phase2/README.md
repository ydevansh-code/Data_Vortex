# Data Vortex Phase 2: Relational Schema & Analysis

This repository contains the Phase 2 submission for Team Event Horizon. We have transitioned from the exploratory data cleaning of Phase 1 to a strict, relational SQLite schema to answer advanced business queries.

## Quick Setup
1. **Prerequisites**: Python 3.9+, SQLite3, Pandas.
2. **Database Generation**: Run `python phase2/load_data.py`. This reads the cleaned CSVs from Phase 1, enforces strict schema constraints, splits location data, and populates `social_engine.db`.
3. **Run Queries**: Connect to `social_engine.db` using any SQLite tool (DB Browser, DBeaver, or CLI) to execute the SQL files in `phase2/queries/`.

## Schema Overview
- **`users`**: Contains demographic data. Location has been normalized into `city` and `country`.
- **`posts`**: Contains post metadata and metrics. Strict `CHECK` constraints prevent corrupted numeric injection.
- **`v_post_engagement`**: A centralized virtual view that calculates `total_engagement = likes + shares + comments` using `COALESCE` to prevent silent `NULL` propagation.

## Query Descriptions
- **`e3.sql`**: Calculates average engagement per platform.
- **`m1.sql`**: Identifies the top 10 geographic locations generating the most total engagement.
- **`h3_part1.sql` / `h3_part2.sql`**: Identifies posts exceeding 2x the platform average (Part 1 demonstrates the statistical impossibility of this threshold; Part 2 provides the top 5% performers as actionable fallback insight).
- **`bonus_trend.sql`**: Calculates Month-over-Month percentage growth per platform using window functions.
- **`bonus_h5.sql`**: Flags specific data corruption anomalies inherited from Phase 1.
- **`validation.sql`**: Proves data integrity, row counts, and absence of PK duplication post-load.

## Submission Report
The full logic explanations, insights, ERD structure, and business takeaways are detailed in the master submission file: **`Phase2_Submission.md`** (which is exported to PDF for the final submission).
