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
    (p.likes + p.shares + p.comments) AS total_engagement,
    CASE WHEN p.likes IS NULL OR p.shares IS NULL OR p.comments IS NULL
         THEN 1 ELSE 0 END AS has_null_component
FROM posts p;
```
**Design choice:** No `COALESCE` is used. If any engagement component is NULL, `total_engagement` will also be NULL, which is the truthful representation of "unknown". Queries filter explicitly using `WHERE has_null_component = 0` or `WHERE likes >= 0` rather than substituting zero for missing values, which would fabricate data.

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
![e3_avg_engagement_by_platform.jpeg](./screenshots/e3_avg_engagement_by_platform.jpeg)

---

## 3. Q2 (Medium): Locations Generate Most Engagement (M1)

**Challenge:** Using both datasets, calculate total engagement by users from each location. Rank locations from highest to lowest engagement.

### Logic Explanation
- **Filter Applied**: `WHERE p.likes >= 0`
- **Exclusion Count**: 509 rows dropped globally due to negative likes. Total dataset evaluated: 11,491 posts.
- **Justification**: We retained `platform IS NULL` posts because they still represent valid geographic engagement. We split `location` into `city` and `country` during data load to allow for granular multi-level geographic grouping.
- **Outcome**: Munich, Germany ranks #1 for total engagement (1,753,727 total engagement, 439 posts, avg 3,994.82 per post).

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
![m1_location_engagement.jpeg](./screenshots/m1_location_engagement.jpeg)

---

## 4. Q3 (Hard): Platform Performance Compared With Its Own Average (H3)

**Challenge:** Identify posts whose engagement is significantly higher (>2x) than the average engagement of that platform.

### Why H3 Returns Zero Rows (And Why That Is The Finding)

**1. Diagnostic Evidence**
The requirement asks for posts exceeding 2x their platform's average engagement. As proven by the diagnostic query below, no platform's maximum engagement reaches the 2x threshold.

| platform | n_posts | avg_engagement | threshold_2x | max_engagement | max_to_mean_ratio |
|---|---|---|---|---|---|
| YouTube | 1990 | 4026.9 | 8053.8 | 7755.0 | 1.926 |
| Instagram | 1893 | 4023.9 | 8047.7 | 7893.0 | 1.962 |
| Facebook | 2004 | 3996.2 | 7992.4 | 7764.0 | 1.943 |
| Reddit | 1952 | 3984.1 | 7968.3 | 7793.0 | 1.956 |
| Twitter | 1956 | 3946.6 | 7893.2 | 7628.0 | 1.933 |

**2. Statistical Justification**
The synthetic dataset uses a bounded uniform distribution (Likes max 5000, Shares max 2000, Comments max 1000). The absolute maximum possible engagement is 8,000. Because the mean across platforms sits near ~4,000, it is mathematically impossible for the maximum value (e.g., 7,893 for Instagram) to exceed twice the mean (7893 < 2 * 4023.9). 

**3. Literal Result**
The literal query asking for >2x platform average correctly returns 0 rows. The query logic is completely correct, but the data itself is the constraint.
*(Screenshot: `h3_literal_empty_result.jpeg` showing 0 rows)*

**4. Meaningful Answer (Relative Outperformers)**
Since no post can reach the 2x absolute threshold, we answer the question's true intent by finding posts that most outperform their own platform. We use `PERCENT_RANK()` to dynamically identify the top 1% (99th percentile) of performers relative to their own platform.

**5. Business Interpretation**
The near-uniform engagement across posts implies the platform's distribution mechanics are not producing viral outliers — which is itself a meaningful finding about a synthetic or algorithmically-flattened feed.

### Output Screenshots
![h3_diagnostic_threshold.jpeg](./screenshots/h3_diagnostic_threshold.jpeg)
![h3_literal_empty_result.jpeg](./screenshots/h3_literal_empty_result.jpeg)
![h3_relative_outperformers.jpeg](./screenshots/h3_relative_outperformers.jpeg)

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

### Output Screenshot
![validation_checks.jpeg](./screenshots/validation_checks.jpeg)

*(End of Report)*
