-- M1: Which Locations Generate the Most Engagement?
-- Goal: Calculate total engagement by users from each location.
-- Rank locations from highest to lowest.

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
