PRAGMA foreign_keys = ON;

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
CREATE INDEX idx_posts_platform ON posts(platform);

-- View to abstract engagement calculation and enforce strict non-NULL math
CREATE VIEW v_post_engagement AS
SELECT 
    p.*,
    -- No default coalescing. If any component is NULL the total is NULL, which is
    -- the truthful representation of "unknown". Queries must filter
    -- explicitly rather than have a zero substituted for them.
    (p.likes + p.shares + p.comments) AS total_engagement,
    CASE WHEN p.likes IS NULL OR p.shares IS NULL OR p.comments IS NULL
         THEN 1 ELSE 0 END            AS has_null_component
FROM posts p;
