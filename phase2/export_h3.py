import sqlite3
import pandas as pd
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
conn = sqlite3.connect('social_engine.db')

# Generate the 3 h3 CSVs
with open('queries/h3.sql', 'r') as f:
    sql = f.read()

parts = sql.split('-- ---------------------------------------------------------------------')
part1 = parts[2]
part2 = parts[4]
part3 = parts[6]

df1 = pd.read_sql_query(part1, conn)
df1.to_csv('outputs/h3_diagnostic.csv', index=False)

df2 = pd.read_sql_query(part2, conn)
df2.to_csv('outputs/h3_literal.csv', index=False)

df3 = pd.read_sql_query(part3, conn)
df3.to_csv('outputs/h3_relative.csv', index=False)

# Also do validation counts
queries = [
    "SELECT COUNT(*) FROM users;",
    "SELECT COUNT(*) FROM posts;",
    "SELECT COUNT(*) FROM posts WHERE platform IS NULL;",
    "SELECT COUNT(*) FROM posts WHERE likes < 0;",
    "SELECT COUNT(*) FROM posts WHERE likes IS NULL;",
    "SELECT COUNT(*) FROM posts p LEFT JOIN users u ON p.user_id=u.user_id WHERE u.user_id IS NULL;",
    "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%';"
]
for q in queries:
    print(f"Query: {q}")
    for row in conn.execute(q).fetchall():
        print(row)
    print()
    
# v_post_engagement check
q = "SELECT COUNT(*) AS null_component_rows FROM v_post_engagement WHERE has_null_component = 1;"
print(f"Query: {q}")
print(conn.execute(q).fetchone())

conn.close()
