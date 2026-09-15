# Screenshot Checklist

For each screenshot, save the file using the exact filename provided into the `phase2/screenshots/` folder. Use **DB Browser for SQLite** for all screenshots. Zoom the UI so SQL text is legible at print resolution, include the window chrome and the row-count status bar. Target 100–400 KB each. Save as JPEG.

| # | Filename | Query to run | Must be visible in frame |
|---|---|---|---|
| 1 | `e3_avg_engagement_by_platform.jpg` | contents of `queries/e3.sql` | full SQL + all 5 result rows + row-count indicator |
| 2 | `m1_location_engagement.jpg` | contents of `queries/m1.sql` | full SQL + top 10 rows + row count |
| 3 | `h3_diagnostic_threshold.jpg` | H3 Part 1 | full SQL + 5-row table showing max_to_mean_ratio < 2 |
| 4 | `h3_literal_empty_result.jpg` | H3 Part 2 | full SQL + the **empty** grid + "0 rows returned" clearly legible |
| 5 | `h3_relative_outperformers.jpg` | H3 Part 3 | full SQL + populated results + row count |
| 6 | `validation_checks.jpg` | `queries/validation.sql` | full SQL + all check rows |
| 7 | `bonus_trend.jpg` (Optional) | `queries/bonus_trend.sql` | full SQL + rows + row count |
| 8 | `bonus_h5_anomalies.jpg` (Optional)| `queries/bonus_h5.sql` | full SQL + rows + row count |
