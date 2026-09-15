PRAGMA foreign_keys = ON;

CREATE TABLE users (
    user_id                  TEXT PRIMARY KEY NOT NULL,
    city                     TEXT,
    country                  TEXT,
    language                 TEXT,
    account_created          TEXT,
    follower_count           REAL,
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
    (COALESCE(p.likes, 0) + COALESCE(p.shares, 0) + COALESCE(p.comments, 0)) AS total_engagement
FROM posts p;
