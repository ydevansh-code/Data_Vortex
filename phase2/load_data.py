import pandas as pd
import sqlite3
import os

# Ensure we are in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=== Starting Data Load Process for Phase 2 ===")

# 1. Connect and initialize schema
db_path = 'social_engine.db'
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)

with open('schema.sql', 'r') as f:
    conn.executescript(f.read())
print("Schema initialized.")

# 2. Load and process Users
print("Processing users...")
users = pd.read_csv('../data/cleaned/users_clean.csv')

# Split location into city and country. Standard format in data is 'City, Country'
def split_location(loc):
    if pd.isna(loc):
        return pd.Series({'city': None, 'country': None})
    parts = [p.strip() for p in str(loc).split(',', 1)]
    if len(parts) == 2:
        return pd.Series({'city': parts[0], 'country': parts[1]})
    else:
        return pd.Series({'city': parts[0], 'country': None})

location_split = users['location'].apply(split_location)
users['city'] = location_split['city']
users['country'] = location_split['country']

# Drop original location and reorder to match schema
users = users.drop(columns=['location'])
users = users[['user_id', 'city', 'country', 'language', 'account_created', 'follower_count', 
               'location_was_null', 'language_was_null', 'account_created_was_null']]

# Load to DB
users.to_sql('users', conn, if_exists='append', index=False)
print(f"Loaded {len(users)} users.")


# 3. Load and process Posts
print("Processing posts...")
posts = pd.read_csv('../data/cleaned/posts_clean.csv')

# Note: We do NOT clip negative likes here. That will be handled dynamically in SQL queries.
# Ensure schema match
posts = posts[['post_id', 'user_id', 'platform', 'text_content', 'timestamp', 'likes', 'shares', 'comments', 'platform_was_null']]

# Load to DB
posts.to_sql('posts', conn, if_exists='append', index=False)
print(f"Loaded {len(posts)} posts.")


# 4. Verification
print("\n=== Data Load Validation ===")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM users")
print(f"DB users count: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM posts")
print(f"DB posts count: {cursor.fetchone()[0]}")

conn.close()
print("Process complete. Database 'social_engine.db' is ready.")
