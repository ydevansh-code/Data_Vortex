-- H3 Part 2: Fallback/Supplementary Insight (Top 5% Performers relative to platform)
WITH ranked_posts AS (
    SELECT
        post_id,
        platform,
        total_engagement,
        PERCENT_RANK() OVER (PARTITION BY platform ORDER BY total_engagement ASC) as relative_rank
    FROM v_post_engagement
    WHERE platform IS NOT NULL AND likes >= 0
)
SELECT 
    post_id, 
    platform, 
    total_engagement, 
    ROUND(relative_rank, 4) AS relative_rank
FROM ranked_posts
WHERE relative_rank >= 0.95
ORDER BY platform, total_engagement DESC;
