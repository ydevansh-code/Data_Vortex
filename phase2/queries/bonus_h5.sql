-- Bonus 2: H5 (Identify Data Anomalies)
-- Goal: Identify potentially corrupted posts using specific conditions from Phase 1.

SELECT 
    post_id,
    CASE
        WHEN likes < 0 THEN 'Negative Likes (Imputation Artifact)'
        WHEN platform IS NULL THEN 'Missing Platform'
        WHEN text_content LIKE '%&amp;%' OR text_content LIKE '%<%>%' THEN 'HTML/Entity Corruption'
        ELSE 'Other'
    END AS anomaly_type
FROM posts
WHERE likes < 0 
   OR platform IS NULL 
   OR text_content LIKE '%&amp;%' 
   OR text_content LIKE '%<%>%'
LIMIT 20;
