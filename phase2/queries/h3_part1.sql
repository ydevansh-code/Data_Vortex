-- H3 Part 1: The Literal 2x Requirement (Returns 0 due to synthetic distribution limits)
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
