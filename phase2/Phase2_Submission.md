# Data Vortex 2026: Phase 2 Submission
**Team**: Event Horizon

---

## 1. Schema Design & Table Structuring

We designed a strict, relational schema (star-schema equivalent) loaded directly into SQLite. We preserved all original data anomalies from Phase 1 without fabricating or clipping data during the load process, choosing instead to handle analytical filtering dynamically via SQL `WHERE` clauses.

### Table: `users`
| Column | Type | Constraints |
|---|---|---|
| `user_id` | TEXT | PRIMARY KEY, NOT NULL |
| `city` | TEXT | Extracted from original location |
| `country` | TEXT | Extracted from original location |
| `language` | TEXT | |
| `account_created` | TEXT | |
| `follower_count` | REAL | |
| `location_was_null` | INTEGER | Imputation flag retained |
| `language_was_null` | INTEGER | Imputation flag retained |
| `account_created_was_null` | INTEGER | Imputation flag retained |

### Table: `posts`
| Column | Type | Constraints |
|---|---|---|
| `post_id` | TEXT | PRIMARY KEY, NOT NULL |
| `user_id` | TEXT | FOREIGN KEY (users.user_id), NOT NULL |
| `platform` | TEXT | Indexed for fast grouping |
| `text_content` | TEXT | |
| `timestamp` | TEXT | |
| `likes` | REAL | |
| `shares` | INTEGER | `CHECK (shares >= 0)` |
| `comments` | INTEGER | `CHECK (comments >= 0)` |
| `platform_was_null` | INTEGER | Imputation flag retained |

### View: `v_post_engagement`
To centralize business logic and handle SQLite's strict `NULL` addition behavior, we created a virtual view used across all queries:
```sql
CREATE VIEW v_post_engagement AS
SELECT 
    p.*, 
    (COALESCE(p.likes, 0) + COALESCE(p.shares, 0) + COALESCE(p.comments, 0)) AS total_engagement
FROM posts p;
```

---

## 2. Q1 (Easy): Average Engagement by Platform (E3)

**Challenge:** Calculate average likes, shares, and comments for each platform. Which platform generates the highest average total engagement?

### Logic Explanation
- **Filter Applied**: `WHERE platform IS NOT NULL AND likes >= 0`
- **Exclusion Count**: 1,784 rows dropped due to `NULL` platforms. An additional 421 rows dropped due to negative likes (imputation artifacts from Phase 1). Total dataset evaluated: 9,795 posts.
- **Justification**: A platform average cannot include posts without a platform. Negative likes physically distort aggregations and represent missing data, not negative engagement.
- **Outcome**: YouTube generates the highest average total engagement (4026.89).

### SQL Query
```sql
SELECT
    platform,
    COUNT(post_id) AS post_count,
    ROUND(AVG(likes), 2)    AS avg_likes,
    ROUND(AVG(shares), 2)   AS avg_shares,
    ROUND(AVG(comments), 2) AS avg_comments,
    ROUND(AVG(total_engagement), 2) AS avg_total_engagement
FROM v_post_engagement
WHERE platform IS NOT NULL
  AND likes >= 0
GROUP BY platform
ORDER BY avg_total_engagement DESC;
```

### Output Screenshot
*(Insert Screenshot Here: Show Query, Result Grid, Tool UI, and Row Count)*

---

## 3. Q2 (Medium): Locations Generate Most Engagement (M1)

**Challenge:** Using both datasets, calculate total engagement by users from each location. Rank locations from highest to lowest engagement.

### Logic Explanation
- **Filter Applied**: `WHERE p.likes >= 0`
- **Exclusion Count**: 509 rows dropped globally due to negative likes. Total dataset evaluated: 11,491 posts.
- **Justification**: We retained `platform IS NULL` posts because they still represent valid geographic engagement. We split `location` into `city` and `country` during data load to allow for granular multi-level geographic grouping.
- **Outcome**: Tokyo, Japan ranks #1 for total engagement.

### SQL Query
```sql
SELECT
    u.city,
    u.country,
    COUNT(p.post_id) AS post_count,
    SUM(p.total_engagement) AS total_engagement,
    ROUND(AVG(p.total_engagement), 2) AS avg_engagement_per_post
FROM users u
JOIN v_post_engagement p ON u.user_id = p.user_id
WHERE p.likes >= 0
GROUP BY u.city, u.country
ORDER BY total_engagement DESC
LIMIT 10;
```

### Output Screenshot
*(Insert Screenshot Here: Show Query, Result Grid, Tool UI, and Row Count)*

---

## 4. Q3 (Hard): Platform Performance Compared With Its Own Average (H3)

**Challenge:** Identify posts whose engagement is significantly higher (>2x) than the average engagement of that platform.

### Logic Explanation & The "Zero Result" Insight
- **Filter Applied**: `WHERE platform IS NOT NULL AND likes >= 0`
- **Exclusion Count**: 2,205 rows dropped (same as Q1).
- **Result:** 0 rows returned for the >2x literal threshold.
- **Statistical Justification**: The underlying synthetic dataset follows a strict uniform distribution bounded by maximum values (Likes max 5000, Shares max 2000, Comments max 1000). The absolute mathematical maximum engagement a post can achieve is 8,000. The mean across all platforms is ~4,000. Therefore, it is statistically impossible for the maximum value to exceed twice the mean ($8000 < 2 \times 4000$).
- **Action Taken**: We provide the literal query (Part 1) to prove the mathematical constraint, and a supplementary `PERCENT_RANK()` query (Part 2) to identify the true top 5% performers relative to their platform.

### SQL Query (Part 1: Literal Requirement)
```sql
WITH platform_stats AS (
    SELECT
        post_id,
        platform,
        total_engagement,
        AVG(total_engagement) OVER (PARTITION BY platform) AS platform_avg_eng
    FROM v_post_engagement
    WHERE platform IS NOT NULL AND likes >= 0
)
SELECT *
FROM platform_stats
WHERE total_engagement >= 2 * platform_avg_eng;
```

### SQL Query (Part 2: Supplementary 95th Percentile Insight)
```sql
WITH ranked_posts AS (
    SELECT
        post_id,
        platform,
        total_engagement,
        PERCENT_RANK() OVER (PARTITION BY platform ORDER BY total_engagement ASC) as relative_rank
    FROM v_post_engagement
    WHERE platform IS NOT NULL AND likes >= 0
)
SELECT post_id, platform, total_engagement, ROUND(relative_rank, 4) AS relative_rank
FROM ranked_posts
WHERE relative_rank >= 0.95
ORDER BY platform, total_engagement DESC;
```

### Output Screenshot
*(Insert Screenshot Here: Show Query, Result Grid, Tool UI, and Row Count)*

---

## 5. Bonus Analyses

### Bonus 1: Trend Detection (MoM Growth)
**Logic**: Using SQLite's `strftime` to group by month, and a `LAG()` window function to calculate Month-over-Month percentage growth per platform.
```sql
WITH monthly_stats AS (
    SELECT 
        platform,
        strftime('%Y-%m', timestamp) AS month,
        SUM(total_engagement) as monthly_engagement
    FROM v_post_engagement
    WHERE platform IS NOT NULL AND likes >= 0
    GROUP BY platform, month
)
SELECT 
    platform, month, monthly_engagement,
    LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month) as prev_month,
    ROUND((monthly_engagement - LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month)) * 100.0 / 
          NULLIF(LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month), 0), 2) AS mom_growth_pct
FROM monthly_stats
ORDER BY platform, month;
```

### Bonus 2: Anomaly Discovery (H5)
**Logic**: Leveraging our deep Phase 1 audit knowledge, we exploit the corrupted dataset to flag specific anomalies without relying on manual observation.
```sql
SELECT 
    post_id,
    CASE
        WHEN likes < 0 THEN 'Negative Likes (Imputation Artifact)'
        WHEN platform IS NULL THEN 'Missing Platform'
        WHEN text_content LIKE '%&amp;%' OR text_content LIKE '%<%>%' THEN 'HTML/Entity Corruption'
        ELSE 'Other'
    END AS anomaly_type
FROM posts
WHERE likes < 0 OR platform IS NULL OR text_content LIKE '%&amp;%' OR text_content LIKE '%<%>%'
LIMIT 20;
```

---

## 6. Phase 2 Insight Report

### Formula Transition
In Phase 1, we utilized a weighted Engagement Score (`0.5*Likes + 0.3*Shares + 0.2*Comments`) to penalize click-farm inflation. In Phase 2, we transitioned to a simple sum (`Likes + Shares + Comments`). This decision was made to strictly adhere to the client's Phase 2 definition of engagement.

### Business Insights
1. **Platform Strategy**: YouTube and Instagram dominate pure engagement averages. However, as proven in H3, the engagement ceiling is artificially bounded. Growth must come from volume, not purely from chasing unicorn viral posts.
2. **Geographic Targeting**: Location analysis (M1) reveals that engagement is not tied solely to English-speaking hubs. Non-English primary regions (Tokyo, Paris, São Paulo) generate engagement sums equal to or greater than New York or London. 
3. **Data Quality Awareness**: 14.8% of platform data was missing, and imputation artifacts (negative likes) were present globally. SQL-level filtering (`IS NOT NULL`, `likes >= 0`) is mandatory for all future analytical pipelines on this dataset.

### Assumptions & Limitations
- **Uniform Distribution Limitation**: As detailed in H3, the data generation process capped maximum interactions, meaning statistically extreme outliers (like a post receiving 100x average engagement) physically do not exist in this dataset.
- **Negative Likes**: We assumed negative likes are a data-corruption artifact rather than a representation of "dislikes", and thus filtered them from aggregate math to prevent deflation of true engagement averages.

---

## 7. Appendix: Data Load Validation
To prove strict adherence to data integrity rules, we validated the SQL load against the raw CSV state.

```sql
SELECT 'users_count' as metric, COUNT(*) as value FROM users
UNION ALL
SELECT 'posts_count' as metric, COUNT(*) as value FROM posts
UNION ALL
SELECT 'duplicate_users', COUNT(user_id) - COUNT(DISTINCT user_id) FROM users
UNION ALL
SELECT 'duplicate_posts', COUNT(post_id) - COUNT(DISTINCT post_id) FROM posts
UNION ALL
SELECT 'null_platforms', COUNT(*) FROM posts WHERE platform IS NULL
UNION ALL
SELECT 'negative_likes', COUNT(*) FROM posts WHERE likes < 0;
```

**Validation Output:**
| metric | value |
|---|---|
| users_count | 1501 |
| posts_count | 12000 |
| duplicate_users | 0 |
| duplicate_posts | 0 |
| null_platforms | 1784 |
| negative_likes | 509 |

*(End of Report)*
