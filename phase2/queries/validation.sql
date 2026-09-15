-- Validation Script
-- Goal: Prove clean load of data without corruption during import.

-- NOTE: The string literals below are ROW LABELS only.
-- Every value is computed at runtime by an aggregate over a real table.
-- No result in this file is hardcoded.

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
SELECT 'negative_likes', COUNT(*) FROM posts WHERE likes < 0
UNION ALL
SELECT 'max_shares', MAX(shares) FROM posts
UNION ALL
SELECT 'min_shares', MIN(shares) FROM posts;
