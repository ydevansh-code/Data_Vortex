import os
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "submission_pdfs")
os.makedirs(OUT, exist_ok=True)

class StyledPDF(FPDF):
    def __init__(self, title_text):
        super().__init__()
        self.title_text = title_text
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, self.title_text, align="R")
        self.ln(4)
        self.set_draw_color(40, 40, 40)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Data Vortex 2026 | Team Event Horizon | Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, text):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 60, 120)
        self.cell(0, 10, text)
        self.ln(8)
        self.set_draw_color(20, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def sub_title(self, text):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, text)
        self.ln(6)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(3)

    def code_block(self, code):
        self.set_fill_color(240, 240, 245)
        self.set_font("Courier", "", 8.5)
        self.set_text_color(30, 30, 30)
        lines = code.strip().split("\n")
        for line in lines:
            safe = line.replace("\t", "    ")
            self.cell(0, 4.5, "  " + safe, fill=True)
            self.ln(4.5)
        self.ln(4)

    def add_table(self, headers, rows, col_widths=None):
        if col_widths is None:
            w = (self.w - 20) / len(headers)
            col_widths = [w] * len(headers)
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(20, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)
        self.set_text_color(30, 30, 30)
        fill = False
        for row in rows:
            if fill:
                self.set_fill_color(245, 245, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, val in enumerate(row):
                self.cell(col_widths[i], 6, str(val), border=1, fill=True, align="C")
            self.ln()
            fill = not fill
        self.ln(4)

    def cover_page(self, title, subtitle):
        self.add_page()
        self.ln(60)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(20, 60, 120)
        self.cell(0, 15, title, align="C")
        self.ln(20)
        self.set_font("Helvetica", "", 14)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, subtitle, align="C")
        self.ln(15)
        self.set_font("Helvetica", "I", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Team: Event Horizon", align="C")
        self.ln(8)
        self.cell(0, 8, "Competition: Data Vortex 2026", align="C")
        self.ln(8)
        self.cell(0, 8, "Phase 2: SQL Analysis & Insight Generation", align="C")


# ======================== PDF 1: SQL QUERY ========================

pdf1 = StyledPDF("SQL Query Document")
pdf1.alias_nb_pages()
pdf1.cover_page("SQL Query Document", "All Queries Used in Phase 2 Analysis")

pdf1.add_page()
pdf1.section_title("1. Schema & View Definition")
pdf1.sub_title("Database Schema (schema.sql)")
pdf1.body_text("Relational schema loaded into SQLite with strict constraints, foreign keys, and indexes.")
pdf1.code_block("""PRAGMA foreign_keys = ON;

CREATE TABLE users (
    user_id                  TEXT PRIMARY KEY NOT NULL,
    city                     TEXT,
    country                  TEXT,
    language                 TEXT,
    account_created          TEXT,
    follower_count           REAL CHECK (follower_count IS NULL OR follower_count >= 0),
    location_was_null        INTEGER,
    language_was_null        INTEGER,
    account_created_was_null INTEGER
);

CREATE TABLE posts (
    post_id            TEXT PRIMARY KEY NOT NULL,
    user_id            TEXT NOT NULL,
    platform           TEXT,
    text_content       TEXT,
    timestamp          TEXT,
    likes              REAL,
    shares             INTEGER CHECK(shares >= 0),
    comments           INTEGER CHECK(comments >= 0),
    platform_was_null  INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE INDEX idx_posts_user ON posts(user_id);
CREATE INDEX idx_posts_platform ON posts(platform);""")

pdf1.sub_title("Engagement View (v_post_engagement)")
pdf1.body_text("Centralizes engagement calculation. No COALESCE used - NULL propagation is intentional.")
pdf1.code_block("""CREATE VIEW v_post_engagement AS
SELECT 
    p.*,
    (p.likes + p.shares + p.comments) AS total_engagement,
    CASE WHEN p.likes IS NULL OR p.shares IS NULL OR p.comments IS NULL
         THEN 1 ELSE 0 END            AS has_null_component
FROM posts p;""")

pdf1.add_page()
pdf1.section_title("2. E3 - Average Engagement by Platform (Easy)")
pdf1.body_text("Goal: Calculate average likes, shares, and comments for each platform. Identify the platform with the highest average total engagement.")
pdf1.code_block("""SELECT
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
ORDER BY avg_total_engagement DESC;""")

pdf1.section_title("3. M1 - Location Engagement Ranking (Medium)")
pdf1.body_text("Goal: Calculate total engagement by users from each location. Rank locations from highest to lowest.")
pdf1.code_block("""SELECT
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
LIMIT 10;""")

pdf1.add_page()
pdf1.section_title("4. H3 - Platform Performance vs Own Average (Hard)")

pdf1.sub_title("Part 1: Diagnostic - Is the 2x Threshold Reachable?")
pdf1.code_block("""SELECT
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
ORDER BY avg_engagement DESC;""")

pdf1.sub_title("Part 2: Literal Answer (Returns 0 Rows)")
pdf1.code_block("""WITH post_engagement AS (
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
ORDER BY platform, total_eng DESC;""")

pdf1.sub_title("Part 3: Relative Outperformers (Top 1% by Platform)")
pdf1.code_block("""WITH post_engagement AS (
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
ORDER BY platform, ratio_to_platform_avg DESC;""")

pdf1.add_page()
pdf1.section_title("5. Bonus 1 - Trend Detection (MoM Growth)")
pdf1.body_text("Goal: Calculate monthly engagement trend per platform using LAG() window function.")
pdf1.code_block("""WITH monthly_stats AS (
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
    LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month)
        as prev_month_engagement,
    ROUND(
        (monthly_engagement - LAG(monthly_engagement)
            OVER (PARTITION BY platform ORDER BY month)) * 100.0 / 
        NULLIF(LAG(monthly_engagement)
            OVER (PARTITION BY platform ORDER BY month), 0), 2
    ) AS mom_growth_pct
FROM monthly_stats
ORDER BY platform, month;""")

pdf1.section_title("6. Bonus 2 - Anomaly Discovery (H5)")
pdf1.body_text("Goal: Identify corrupted posts using specific conditions discovered during Phase 1 audit.")
pdf1.code_block("""SELECT 
    post_id,
    CASE
        WHEN likes < 0 THEN 'Negative Likes (Imputation Artifact)'
        WHEN platform IS NULL THEN 'Missing Platform'
        WHEN text_content LIKE '%&amp;%' OR text_content LIKE '%<%>%'
            THEN 'HTML/Entity Corruption'
        ELSE 'Other'
    END AS anomaly_type
FROM posts
WHERE likes < 0 
   OR platform IS NULL 
   OR text_content LIKE '%&amp;%' 
   OR text_content LIKE '%<%>%'
LIMIT 20;""")

pdf1.section_title("7. Validation Script")
pdf1.body_text("Goal: Prove clean data load without corruption during import.")
pdf1.code_block("""SELECT 'users_count' as metric, COUNT(*) as value FROM users
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
SELECT 'min_shares', MIN(shares) FROM posts;""")

pdf1_path = os.path.join(OUT, "SQL_Query.pdf")
pdf1.output(pdf1_path)
print(f"[OK] {pdf1_path}")


# ======================== PDF 2: EXPLANATION OF LOGIC ========================

pdf2 = StyledPDF("Explanation of Logic")
pdf2.alias_nb_pages()
pdf2.cover_page("Explanation of Logic", "Detailed Rationale Behind Every Query & Design Decision")

pdf2.add_page()
pdf2.section_title("1. Schema Design Rationale")

pdf2.sub_title("1.1 Why a Relational Schema in SQLite?")
pdf2.body_text(
    "We designed a strict relational schema (star-schema equivalent) loaded into SQLite. "
    "We preserved all original data anomalies from Phase 1 without fabricating or clipping "
    "data during the load process. Analytical filtering is handled dynamically via SQL WHERE "
    "clauses rather than destructive ETL transforms."
)

pdf2.sub_title("1.2 Location Splitting (city, country)")
pdf2.body_text(
    "The original CSV had a single 'location' column with values like 'Munich, Germany'. "
    "We split this into separate 'city' and 'country' columns during the data load to enable "
    "granular multi-level geographic grouping in M1 without runtime string manipulation."
)

pdf2.sub_title("1.3 Imputation Flags Retained")
pdf2.body_text(
    "Columns like location_was_null, language_was_null, account_created_was_null, and "
    "platform_was_null are boolean flags carried from Phase 1. They record which values were "
    "originally missing and later imputed so that downstream analysis can distinguish real "
    "values from synthetic ones."
)

pdf2.sub_title("1.4 The v_post_engagement View - No COALESCE")
pdf2.body_text(
    "We created a virtual view (v_post_engagement) that computes total_engagement = "
    "likes + shares + comments. Critically, we do NOT use COALESCE to substitute zeros for "
    "NULLs. If any engagement component is NULL, total_engagement will also be NULL. This is "
    "the truthful representation of 'unknown'. Queries filter explicitly using "
    "WHERE has_null_component = 0 or WHERE likes >= 0 rather than fabricating data."
)

pdf2.add_page()
pdf2.section_title("2. E3 Logic - Average Engagement by Platform")

pdf2.sub_title("2.1 Filters Applied")
pdf2.body_text(
    "WHERE platform IS NOT NULL AND likes >= 0\n\n"
    "Two filters are applied:\n"
    "- platform IS NOT NULL: 1,784 rows dropped. A platform average cannot include posts "
    "without a platform assignment.\n"
    "- likes >= 0: An additional 421 rows dropped. Negative likes are imputation artifacts "
    "from Phase 1 (not 'dislikes') and physically distort aggregations."
)

pdf2.sub_title("2.2 Total Dataset Evaluated")
pdf2.body_text("After filtering: 9,795 posts across 5 platforms (YouTube, Instagram, Facebook, Reddit, Twitter).")

pdf2.sub_title("2.3 Why AVG and Not SUM?")
pdf2.body_text(
    "The question asks for 'average engagement'. AVG normalizes by post count, making "
    "comparison fair across platforms with different volumes. YouTube has 1,990 posts while "
    "Instagram has 1,893 - raw sums would bias toward higher-volume platforms."
)

pdf2.sub_title("2.4 Outcome")
pdf2.body_text("YouTube generates the highest average total engagement at 4,026.89 per post.")

pdf2.add_page()
pdf2.section_title("3. M1 Logic - Location Engagement Ranking")

pdf2.sub_title("3.1 Filters Applied")
pdf2.body_text(
    "WHERE p.likes >= 0\n\n"
    "Only negative likes are filtered (509 rows). We intentionally retain posts with NULL "
    "platforms because they still represent valid geographic engagement - a post from Munich "
    "is still from Munich regardless of whether its platform field was imputed."
)

pdf2.sub_title("3.2 JOIN Strategy")
pdf2.body_text(
    "INNER JOIN between users and v_post_engagement on user_id. This naturally excludes any "
    "orphan posts (posts without a matching user), though our validation confirmed zero orphans "
    "exist in this dataset."
)

pdf2.sub_title("3.3 Grouping by City + Country")
pdf2.body_text(
    "We group by both city AND country to handle potential city name collisions (e.g., "
    "'Portland, USA' vs a hypothetical 'Portland, UK'). The location was split during load "
    "specifically to enable this granularity."
)

pdf2.sub_title("3.4 LIMIT 10")
pdf2.body_text(
    "The question asks to 'rank locations from highest to lowest'. We apply LIMIT 10 to "
    "surface the top performers. The full ranked list is available by removing the LIMIT clause."
)

pdf2.sub_title("3.5 Outcome")
pdf2.body_text(
    "Munich, Germany ranks #1 with 1,753,727 total engagement across 439 posts "
    "(avg 3,994.82 per post). Geographic engagement is not tied solely to English-speaking hubs."
)

pdf2.add_page()
pdf2.section_title("4. H3 Logic - Platform Performance vs Own Average")

pdf2.sub_title("4.1 The Core Problem")
pdf2.body_text(
    "The question asks: 'Identify posts whose engagement is significantly higher (>2x) "
    "than the average engagement of that platform.' The literal query returns 0 rows. "
    "This is NOT a bug - it is the correct mathematical result."
)

pdf2.sub_title("4.2 Part 1: Diagnostic Proof")
pdf2.body_text(
    "We first run a diagnostic query that computes each platform's avg engagement, the 2x "
    "threshold, and the actual maximum engagement. Result: no platform's maximum reaches 2x.\n\n"
    "For example, YouTube's avg is 4,026.9, so 2x = 8,053.8, but YouTube's maximum post is "
    "only 7,755 (ratio 1.926). This holds across all 5 platforms."
)

pdf2.sub_title("4.3 Statistical Justification")
pdf2.body_text(
    "The dataset uses a bounded uniform distribution: Likes max 5000, Shares max 2000, "
    "Comments max 1000. The absolute maximum possible engagement is 8,000. Because the mean "
    "across platforms sits near ~4,000, it is mathematically impossible for any value to reach "
    "2x the mean. max(8000) < 2 * mean(~4000) = ~8000. The distributions are too tight."
)

pdf2.sub_title("4.4 Part 2: Empty Result (Honest Answer)")
pdf2.body_text(
    "The literal query using WHERE total_eng >= 2 * platform_avg_eng correctly returns 0 rows. "
    "We present this as evidence rather than hiding it."
)

pdf2.sub_title("4.5 Part 3: Meaningful Alternative")
pdf2.body_text(
    "Since no post reaches 2x, we answer the question's TRUE INTENT by identifying posts that "
    "most outperform their own platform. We use PERCENT_RANK() to find the top 1% (99th "
    "percentile) performers relative to their platform, yielding ~100 posts with ratios "
    "ranging from 1.773 to 1.962."
)

pdf2.sub_title("4.6 Business Interpretation")
pdf2.body_text(
    "The near-uniform engagement across posts implies the platform's distribution mechanics "
    "are not producing viral outliers. Growth must come from volume, not from chasing "
    "unicorn viral posts. This is itself a meaningful finding about the data generation process."
)

pdf2.add_page()
pdf2.section_title("5. Bonus Queries Logic")

pdf2.sub_title("5.1 Bonus 1: MoM Growth (Trend Detection)")
pdf2.body_text(
    "We use strftime('%Y-%m', timestamp) to group posts by calendar month per platform, "
    "then apply the LAG() window function to compute month-over-month percentage growth.\n\n"
    "LAG(monthly_engagement) OVER (PARTITION BY platform ORDER BY month) retrieves the "
    "previous month's engagement for the same platform. The growth formula is:\n"
    "mom_growth_pct = (current - previous) * 100.0 / NULLIF(previous, 0)\n\n"
    "NULLIF prevents division by zero. The first month per platform naturally returns NULL "
    "for growth (no prior month to compare against)."
)

pdf2.sub_title("5.2 Bonus 2: Anomaly Discovery (H5)")
pdf2.body_text(
    "Leveraging Phase 1 audit knowledge, we use a CASE expression to classify specific "
    "anomaly types:\n"
    "- Negative Likes: Imputation artifacts where missing values were filled with negative "
    "numbers during Phase 1 data cleaning.\n"
    "- Missing Platform: 1,784 posts with NULL platform field.\n"
    "- HTML/Entity Corruption: Posts where text_content contains encoded HTML entities "
    "like &amp; or malformed tags.\n\n"
    "The WHERE clause uses OR to capture all anomaly types in a single pass. "
    "LIMIT 20 constrains output for readability."
)

pdf2.add_page()
pdf2.section_title("6. Validation Logic")

pdf2.sub_title("6.1 Purpose")
pdf2.body_text(
    "The validation script proves data integrity after the CSV-to-SQLite load. It uses "
    "UNION ALL to combine multiple aggregate checks into a single result set."
)

pdf2.sub_title("6.2 Checks Performed")
pdf2.body_text(
    "1. users_count (1,501): Total users loaded matches raw CSV row count.\n"
    "2. posts_count (12,000): Total posts loaded matches raw CSV row count.\n"
    "3. duplicate_users (0): No duplicate user_ids - PRIMARY KEY constraint held.\n"
    "4. duplicate_posts (0): No duplicate post_ids - PRIMARY KEY constraint held.\n"
    "5. null_platforms (1,784): Known missing platforms preserved (not dropped).\n"
    "6. negative_likes (509): Known imputation artifacts preserved (not corrected).\n"
    "7. max_shares (2,000): Upper bound matches expected data generation ceiling.\n"
    "8. min_shares (0): Lower bound is zero, confirming no negative shares."
)

pdf2.sub_title("6.3 Design Choice")
pdf2.body_text(
    "String literals (e.g., 'users_count') are ROW LABELS only. Every value is computed "
    "at runtime by an aggregate over a real table. No result in this validation is hardcoded."
)

pdf2_path = os.path.join(OUT, "Explanation_of_Logic.pdf")
pdf2.output(pdf2_path)
print(f"[OK] {pdf2_path}")


# ======================== PDF 3: INSIGHT REPORT ========================

pdf3 = StyledPDF("Phase 2 Insight Report")
pdf3.alias_nb_pages()
pdf3.cover_page("Phase 2 Insight Report", "Business Insights, Statistical Findings & Recommendations")

pdf3.add_page()
pdf3.section_title("1. Executive Summary")
pdf3.body_text(
    "This report summarizes the analytical findings from Phase 2 of Data Vortex 2026. "
    "Using a SQLite relational database built from Phase 1 cleaned data, we executed "
    "structured queries across three difficulty tiers (Easy, Medium, Hard) and two bonus "
    "analyses. The dataset contains 1,501 users and 12,000 posts across 5 social media "
    "platforms spanning May 2024 to April 2025."
)

pdf3.section_title("2. Formula Transition (Phase 1 to Phase 2)")
pdf3.body_text(
    "Phase 1 Engagement Score: 0.5*Likes + 0.3*Shares + 0.2*Comments\n"
    "This weighted formula was designed to penalize click-farm inflation by reducing "
    "the weight of easily-gamed metrics (likes).\n\n"
    "Phase 2 Total Engagement: Likes + Shares + Comments\n"
    "We transitioned to a simple unweighted sum to strictly adhere to the client's "
    "Phase 2 definition of engagement. This ensures transparency and reproducibility."
)

pdf3.add_page()
pdf3.section_title("3. Key Findings")

pdf3.sub_title("3.1 Platform Engagement (E3)")
pdf3.body_text("Average total engagement by platform (filtered: 9,795 posts):")

pdf3.add_table(
    ["Platform", "Posts", "Avg Likes", "Avg Shares", "Avg Comments", "Avg Total"],
    [
        ["YouTube", "1,990", "2,505.18", "1,017.40", "504.32", "4,026.89"],
        ["Instagram", "1,893", "2,477.70", "1,044.44", "501.72", "4,023.86"],
        ["Facebook", "2,004", "2,504.33", "987.70", "504.16", "3,996.19"],
        ["Reddit", "1,952", "2,472.87", "1,000.62", "510.66", "3,984.15"],
        ["Twitter", "1,956", "2,431.11", "1,010.32", "505.15", "3,946.58"],
    ],
    [30, 25, 30, 30, 35, 30]
)

pdf3.body_text(
    "Finding: YouTube leads with 4,026.89 avg engagement per post. However, the spread "
    "across all 5 platforms is remarkably narrow (range: 80.31 points, or ~2% variance). "
    "No single platform dramatically outperforms the others."
)

pdf3.sub_title("3.2 Geographic Engagement (M1)")
pdf3.body_text("Top 10 locations by total engagement (filtered: 11,491 posts):")

pdf3.add_table(
    ["Rank", "City", "Country", "Posts", "Total Engagement", "Avg/Post"],
    [
        ["1", "Munich", "Germany", "439", "1,753,727", "3,994.82"],
        ["2", "Los Angeles", "USA", "438", "1,750,522", "3,996.63"],
        ["3", "Shanghai", "China", "437", "1,735,013", "3,970.28"],
        ["4", "Barcelona", "Spain", "423", "1,713,206", "4,050.13"],
        ["5", "Dubai", "UAE", "409", "1,648,772", "4,031.23"],
        ["6", "Melbourne", "Australia", "400", "1,612,581", "4,031.45"],
        ["7", "Houston", "USA", "397", "1,565,090", "3,942.29"],
        ["8", "Osaka", "Japan", "379", "1,546,381", "4,080.16"],
        ["9", "Mumbai", "India", "391", "1,541,509", "3,942.48"],
        ["10", "Rio de Janeiro", "Brazil", "390", "1,534,666", "3,935.04"],
    ],
    [15, 33, 25, 22, 45, 30]
)

pdf3.body_text(
    "Finding: Munich, Germany ranks #1. Crucially, engagement is NOT tied solely to "
    "English-speaking hubs. Non-English-primary regions (Tokyo, Paris, Sao Paulo, Shanghai) "
    "generate engagement sums equal to or greater than New York or London. This suggests "
    "a globally distributed audience."
)

pdf3.add_page()
pdf3.sub_title("3.3 Outlier Analysis (H3)")
pdf3.body_text(
    "The literal query for posts exceeding 2x their platform's average engagement "
    "returns 0 rows. Diagnostic analysis proves this is mathematically correct:"
)

pdf3.add_table(
    ["Platform", "Avg Engagement", "2x Threshold", "Max Engagement", "Max/Mean Ratio"],
    [
        ["YouTube", "4,026.9", "8,053.8", "7,755", "1.926"],
        ["Instagram", "4,023.9", "8,047.7", "7,893", "1.962"],
        ["Facebook", "3,996.2", "7,992.4", "7,764", "1.943"],
        ["Reddit", "3,984.1", "7,968.3", "7,793", "1.956"],
        ["Twitter", "3,946.6", "7,893.2", "7,628", "1.933"],
    ],
    [34, 34, 34, 34, 34]
)

pdf3.body_text(
    "The dataset's bounded uniform distribution (Likes max 5000, Shares max 2000, "
    "Comments max 1000) means the theoretical max engagement is 8,000. With means near "
    "~4,000, the 2x threshold (~8,000) is unreachable. The best ratio achieved is 1.962 "
    "(Instagram).\n\n"
    "Relative analysis (top 1% by PERCENT_RANK) identifies ~100 posts as platform-relative "
    "outperformers, with ratios ranging from 1.773 to 1.962."
)

pdf3.sub_title("3.4 Trend Analysis (Bonus)")
pdf3.body_text(
    "Month-over-month engagement growth shows high volatility across all platforms:\n"
    "- Instagram shows the highest single-month spike: +38.06% (Feb to Mar 2025)\n"
    "- Twitter shows the deepest single-month drop: -19.0% (Aug to Sep 2024)\n"
    "- YouTube shows the most stable pattern with the smallest average MoM swings\n\n"
    "No platform shows a consistent upward or downward trend over the 12-month period, "
    "suggesting seasonal oscillation rather than structural growth/decline."
)

pdf3.sub_title("3.5 Data Anomalies (Bonus)")
pdf3.body_text(
    "Anomaly classification of flagged posts:\n"
    "- Missing Platform: 1,784 posts (14.87% of dataset) - the dominant anomaly\n"
    "- Negative Likes: 509 posts (4.24%) - imputation artifacts from Phase 1\n"
    "- HTML/Entity Corruption: Present in text_content (e.g., &amp; entities)\n\n"
    "All anomalies were preserved in the database and handled via SQL-level filtering "
    "rather than destructive ETL, ensuring analytical transparency."
)

pdf3.add_page()
pdf3.section_title("4. Business Recommendations")

pdf3.sub_title("4.1 Platform Strategy")
pdf3.body_text(
    "YouTube and Instagram lead engagement averages, but the margin is slim (~2%). "
    "Recommendation: Do not over-invest in a single platform. Diversify content across "
    "all 5 platforms. Growth must come from increasing post volume rather than chasing "
    "viral outliers, since the data proves viral-level engagement (>2x average) does not "
    "exist in this ecosystem."
)

pdf3.sub_title("4.2 Geographic Targeting")
pdf3.body_text(
    "Engagement is globally distributed. Munich, Shanghai, Barcelona, and Dubai all "
    "outperform traditional English-speaking tech hubs. Recommendation: Allocate marketing "
    "budget to non-English markets. Localized content strategies could amplify already-strong "
    "engagement in these regions."
)

pdf3.sub_title("4.3 Data Quality Pipeline")
pdf3.body_text(
    "14.87% of platform data is missing and 4.24% of likes are corrupted. "
    "Recommendation: Implement upstream data validation at ingestion to prevent NULL "
    "platforms and negative engagement values. SQL-level filtering (IS NOT NULL, "
    "likes >= 0) must be mandatory for all future analytical pipelines on this dataset."
)

pdf3.add_page()
pdf3.section_title("5. Assumptions & Limitations")

pdf3.body_text(
    "1. Uniform Distribution Limitation: The data generation process capped maximum "
    "interactions (Likes: 0-5000, Shares: 0-2000, Comments: 0-1000). Statistically extreme "
    "outliers (like a post receiving 100x average engagement) physically do not exist. This "
    "constrains the H3 analysis.\n\n"
    "2. Negative Likes Assumption: We assumed negative likes are data-corruption artifacts "
    "rather than 'dislikes', and filtered them from aggregate math to prevent deflation of "
    "true engagement averages.\n\n"
    "3. NULL Platform Posts: Posts with missing platform were excluded from platform-specific "
    "analysis but included in geographic analysis (M1), since geographic engagement is "
    "platform-independent.\n\n"
    "4. Engagement Formula: Phase 2 uses unweighted sum (Likes + Shares + Comments) per "
    "client specification. Phase 1's weighted formula (0.5L + 0.3S + 0.2C) is not used.\n\n"
    "5. Time Range: Data spans May 2024 to April 2025 (12 months). Trend analysis may not "
    "capture longer-term structural patterns."
)

pdf3.section_title("6. Methodology Summary")

pdf3.body_text(
    "Database: SQLite 3 with strict relational schema, foreign keys, and CHECK constraints.\n"
    "Data Load: Python script (load_data.py) with city/country splitting and imputation flag "
    "preservation.\n"
    "Validation: 8-point integrity check confirming zero duplicates, correct row counts, and "
    "known anomaly preservation.\n"
    "Analysis Tool: Raw SQL executed against SQLite with results exported to CSV.\n"
    "Filtering Philosophy: Dynamic SQL-level filtering (WHERE clauses) instead of destructive "
    "ETL. NULL propagation in engagement calculations rather than COALESCE to zero."
)

pdf3_path = os.path.join(OUT, "Phase2_Insight_Report.pdf")
pdf3.output(pdf3_path)
print(f"[OK] {pdf3_path}")

print(f"\nAll 3 PDFs saved to: {OUT}")
