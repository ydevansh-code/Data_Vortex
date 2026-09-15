-- =====================================================================
-- H3 — Platform Performance vs Own Average
-- Question: find posts whose engagement is >= 2x their OWN platform's
--           average engagement.
--
-- This file contains three parts. Part 1 is the literal answer to the
-- question. Parts 2 and 3 exist because Part 1 legitimately returns
-- zero rows, and we prove why rather than leaving a blank grid.
-- =====================================================================

-- ---------------------------------------------------------------------
-- PART 1 of 3 — DIAGNOSTIC: is the 2x threshold mathematically reachable?
-- Run this FIRST. It is the evidence for Part 2's empty result.
-- ---------------------------------------------------------------------
SELECT
    platform,
    COUNT(*)                                        AS n_posts,
    ROUND(AVG(likes + shares + comments), 1)        AS avg_engagement,
    ROUND(2 * AVG(likes + shares + comments), 1)    AS threshold_2x,
    MAX(likes + shares + comments)                  AS max_engagement,
    ROUND(CAST(MAX(likes + shares + comments) AS REAL)
          / AVG(likes + shares + comments), 3)      AS max_to_mean_ratio
FROM posts
WHERE platform IS NOT NULL
  AND likes >= 0
GROUP BY platform
ORDER BY avg_engagement DESC;

-- ---------------------------------------------------------------------
-- PART 2 of 3 — THE LITERAL QUESTION (returns 0 rows; this is correct)
-- ---------------------------------------------------------------------
WITH post_engagement AS (
    SELECT
        post_id,
        platform,
        likes + shares + comments AS total_eng,
        AVG(likes + shares + comments) OVER (PARTITION BY platform)
            AS platform_avg_eng
    FROM posts
    WHERE platform IS NOT NULL
      AND likes >= 0
)
SELECT post_id, platform, total_eng,
       ROUND(platform_avg_eng, 2) AS platform_avg_eng
FROM post_engagement
WHERE total_eng >= 2 * platform_avg_eng
ORDER BY platform, total_eng DESC;

-- ---------------------------------------------------------------------
-- PART 3 of 3 — ANALYTICALLY MEANINGFUL ANSWER
-- Since no post can reach 2x its platform mean, we answer the question's
-- INTENT: which posts most outperform their own platform? Ranked
-- relatively, so the threshold adapts to the data instead of being fixed.
-- ---------------------------------------------------------------------
WITH post_engagement AS (
    SELECT
        post_id,
        platform,
        likes + shares + comments AS total_eng,
        AVG(likes + shares + comments) OVER (PARTITION BY platform)
            AS platform_avg_eng,
        PERCENT_RANK() OVER (
            PARTITION BY platform
            ORDER BY likes + shares + comments
        ) AS pct_rank_in_platform
    FROM posts
    WHERE platform IS NOT NULL
      AND likes >= 0
)
SELECT
    post_id,
    platform,
    total_eng,
    ROUND(platform_avg_eng, 2)                       AS platform_avg_eng,
    ROUND(total_eng / platform_avg_eng, 3)           AS ratio_to_platform_avg,
    ROUND(pct_rank_in_platform * 100, 2)             AS percentile_in_platform
FROM post_engagement
WHERE pct_rank_in_platform >= 0.99
ORDER BY platform, ratio_to_platform_avg DESC;
