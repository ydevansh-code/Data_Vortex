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
