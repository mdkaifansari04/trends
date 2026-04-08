CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY,
  external_id TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  excerpt TEXT,
  content_markdown TEXT NOT NULL,
  cover_image_url TEXT,
  topic TEXT,
  weight INTEGER NOT NULL DEFAULT 0 CHECK (weight >= 0 AND weight <= 1000),
  published_date TEXT NOT NULL,
  published_at TEXT,
  is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS post_tags (
  post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  PRIMARY KEY (post_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_date_trending
  ON posts (published_date, weight DESC, published_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_posts_date_latest
  ON posts (published_date, published_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_posts_topic_date_weight
  ON posts (topic, published_date, weight DESC);

CREATE INDEX IF NOT EXISTS idx_post_tags_tag_post
  ON post_tags (tag_id, post_id);
