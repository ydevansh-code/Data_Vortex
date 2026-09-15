import sqlite3
import os

db_path = 'phase2/social_engine.db'
if not os.path.exists(db_path):
    print("FAIL: social_engine.db missing")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("--- PHASE 2 AUTOMATED AUDIT ---")

# 1. H3 Diagnostic
cur.execute("""
SELECT platform, COUNT(*) post_count,
       MIN(likes+shares+comments) min_eng,
       ROUND(AVG(likes+shares+comments), 2) avg_eng,
       MAX(likes+shares+comments) max_eng,
       ROUND(2*AVG(likes+shares+comments), 2) threshold_2x
FROM posts
WHERE platform IS NOT NULL AND likes >= 0
GROUP BY platform;
""")
rows = cur.fetchall()
h3_pass = True
for r in rows:
    if r[4] >= r[5]:
        h3_pass = False
print(f"[1.1] H3 2x Threshold Viable (>0 rows)? {'YES' if not h3_pass else 'NO (0 rows expected - mathematically capped)'}")

# 1.2 Null & Negative Counts
cur.execute("""
SELECT COUNT(*) total, 
       SUM(CASE WHEN platform IS NULL THEN 1 ELSE 0 END) null_platform,
       SUM(CASE WHEN likes < 0 THEN 1 ELSE 0 END) negative_likes
FROM posts;
""")
tot, null_p, neg_l = cur.fetchone()
print(f"[1.2] Total: {tot} | Null Platforms: {null_p} | Negative Likes: {neg_l}")

# 1.3 Orphan Posts
cur.execute("""
SELECT COUNT(*) FROM posts p
LEFT JOIN users u ON p.user_id = u.user_id
WHERE u.user_id IS NULL;
""")
orphans = cur.fetchone()[0]
print(f"[1.3] Orphan Posts Count: {orphans} ({'PASS' if orphans == 0 else 'FAIL'})")

# 1.4 PK Duplicate Check
cur.execute("SELECT COUNT(user_id) - COUNT(DISTINCT user_id) FROM users;")
dup_users = cur.fetchone()[0]
cur.execute("SELECT COUNT(post_id) - COUNT(DISTINCT post_id) FROM posts;")
dup_posts = cur.fetchone()[0]
print(f"[1.4] Duplicate User PKs: {dup_users} | Duplicate Post PKs: {dup_posts} ({'PASS' if dup_users == 0 and dup_posts == 0 else 'FAIL'})")

# 1.5 Timestamp Check
cur.execute("SELECT COUNT(CASE WHEN strftime('%Y-%m-%d %H:%M:%S', timestamp) IS NULL THEN 1 END) FROM posts;")
bad_dates = cur.fetchone()[0]
print(f"[1.5] Unparseable Timestamps: {bad_dates} ({'PASS' if bad_dates == 0 else 'FAIL'})")

# 2. Schema Checks
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
cur.execute("SELECT name FROM sqlite_master WHERE type='view';")
views = [v[0] for v in cur.fetchall()]
print(f"[2.1] Tables Present: {tables} ({'PASS' if 'users' in tables and 'posts' in tables else 'FAIL'})")
print(f"[2.2] Views Present: {views} ({'PASS' if 'v_post_engagement' in views else 'FAIL'})")

# File structure check
required_files = [
    'phase2/schema.sql',
    'phase2/load_data.py',
    'phase2/decisions.md',
    'phase2/README.md',
    'phase2/Phase2_Submission.md',
    'phase2/queries/e3.sql',
    'phase2/queries/m1.sql',
    'phase2/queries/h3_part1.sql',
    'phase2/queries/h3_part2.sql',
    'phase2/queries/bonus_trend.sql',
    'phase2/queries/bonus_h5.sql',
    'phase2/queries/validation.sql'
]

missing = [f for f in required_files if not os.path.exists(f)]
print(f"[8.1] Required Files Present: {'PASS' if not missing else f'FAIL (Missing: {missing})'}")

conn.close()
print("--- AUDIT COMPLETE ---")
