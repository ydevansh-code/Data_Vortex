-- Bonus 1: Trend Detection (MoM Growth)
-- Goal: Calculate monthly engagement trend per platform using strftime.

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
    platform,
    month,
    monthly_engagement,
    LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month) as prev_month_engagement,
    ROUND((monthly_engagement - LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month)) * 100.0 / 
          NULLIF(LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month), 0), 2) AS mom_growth_pct
FROM monthly_stats
ORDER BY platform, month;
