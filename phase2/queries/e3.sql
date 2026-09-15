-- E3: Average Engagement by Platform
-- Goal: Calculate average likes, shares, and comments for each platform. 
-- Return platform with highest average total engagement.

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
