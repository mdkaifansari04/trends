# Trends News Platform Specification

## 1. Purpose

Build a clean, production-ready news/article website on Cloudflare:

- Backend: Cloudflare Python Worker
- Frontend: HTML + Tailwind CSS
- Data: relational SQL schema for posts

Content is created outside this project. An external automation agent sends bulk posts daily via API.

## 2. Scope

### In Scope

- Homepage with today's trending and latest posts
- Post detail page by slug
- Bulk POST API for external ingestion
- Trending sort using `weight`
- Client-side bookmarks in `localStorage`
- Single language: English
- SEO features in last phase (`sitemap.xml`, `rss.xml`, canonical tags)

### Out of Scope

- AI generation/summarization in this project
- Scraping/crawling logic in this project
- User accounts, server-side bookmarks, comments
- Admin moderation and approval dashboard

## 3. Product Behavior

### 3.1 Publishing

- Any valid post inserted through bulk API is visible immediately.
- No admin approval flow.

### 3.2 Trending

- Sort rule: `weight DESC`
- Tie-breakers:
  1. `published_at DESC` (if provided)
  2. `created_at DESC`
  3. `id ASC` (stable order)

### 3.3 Homepage

- Trending list for current day
- Latest list for current day
- If no rows for today, show clear empty state
- Optional later behavior: fallback to latest available date

### 3.4 Bookmarks

- Stored only in browser `localStorage`
- No backend state or user profile

## 4. Technical Architecture

### 4.1 Runtime

- Python Worker serves both API JSON and HTML pages.

### 4.2 Database

- Use Cloudflare SQL database service (recommended: D1).
- Cloudflare R2 is object storage and can be used later for media assets.

### 4.3 Auth for Ingest API

- Use environment secret(s), not DB tables:
  - `INGEST_API_KEY`
- External agent sends key in request header (for example `Authorization: Bearer <key>`).

This keeps schema simple while still securing the write endpoint.

## 5. Data Model (Simple v2)

The schema is intentionally minimal and clean.

### 5.1 `posts`

- `id` TEXT PRIMARY KEY (UUID)
- `external_id` TEXT NOT NULL UNIQUE
- `slug` TEXT NOT NULL UNIQUE
- `title` TEXT NOT NULL
- `excerpt` TEXT NULL
- `content_markdown` TEXT NOT NULL
- `cover_image_url` TEXT NULL
- `topic` TEXT NULL
- `weight` INTEGER NOT NULL DEFAULT 0 CHECK (`weight` >= 0 AND `weight` <= 1000)
- `published_date` TEXT NOT NULL
- `published_at` TEXT NULL
- `is_published` INTEGER NOT NULL DEFAULT 1 CHECK (`is_published` IN (0, 1))
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

Notes:

- `external_id` is the idempotent upsert key from external agent.
- `slug` is used for post route lookup.
- `published_date` format: `YYYY-MM-DD`.

### 5.2 `tags`

- `id` TEXT PRIMARY KEY (UUID)
- `slug` TEXT NOT NULL UNIQUE
- `name` TEXT NOT NULL UNIQUE
- `created_at` TEXT NOT NULL

### 5.3 `post_tags`

- `post_id` TEXT NOT NULL REFERENCES `posts(id)` ON DELETE CASCADE
- `tag_id` TEXT NOT NULL REFERENCES `tags(id)` ON DELETE CASCADE
- `created_at` TEXT NOT NULL
- PRIMARY KEY (`post_id`, `tag_id`)

## 6. Indexes

- UNIQUE `posts(external_id)`
- UNIQUE `posts(slug)`
- `posts(published_date, weight DESC, published_at DESC, created_at DESC)`
- `posts(published_date, published_at DESC, created_at DESC)`
- `posts(topic, published_date, weight DESC)`
- `post_tags(tag_id, post_id)`

## 7. Reference SQL (Initial Migration)

```sql
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
```

## 8. API Specification

Base prefix: `/api/v1`

### 8.1 Bulk Ingest Endpoint

- `POST /posts/bulk`
- Auth: API key from Worker secret
- Purpose: insert/update many posts in one request

Request body:

```json
{
  "items": [
    {
      "external_id": "agent-2026-04-08-001",
      "slug": "open-source-ai-roundup-april-8",
      "title": "Open Source AI Roundup",
      "excerpt": "Daily ecosystem snapshot.",
      "content_markdown": "# Roundup ...",
      "topic": "AI",
      "tags": ["ai", "open-source"],
      "cover_image_url": "https://cdn.example.com/a.jpg",
      "weight": 92,
      "published_date": "2026-04-08",
      "published_at": "2026-04-08T06:00:00Z",
      "is_published": true
    }
  ]
}
```

Behavior:

- Validate fields and types
- Normalize slug and tags
- Upsert by `external_id`
- Resolve tags and maintain `post_tags`
- Return partial-success summary

Response example:

```json
{
  "success": true,
  "inserted": 8,
  "updated": 3,
  "failed": 1,
  "errors": [
    {
      "index": 4,
      "external_id": "agent-2026-04-08-005",
      "error_code": "SLUG_CONFLICT",
      "reason": "slug already assigned to another post"
    }
  ]
}
```

### 8.2 Public Read Endpoints

- `GET /posts?date=YYYY-MM-DD&limit=20&offset=0`
- `GET /posts/trending?date=YYYY-MM-DD&limit=10`
- `GET /posts/:slug`
- `GET /health`

## 9. Query Contracts

Trending:

```sql
SELECT p.*
FROM posts p
WHERE p.is_published = 1
  AND p.published_date = :date
ORDER BY p.weight DESC, p.published_at DESC, p.created_at DESC, p.id ASC
LIMIT :limit;
```

Latest:

```sql
SELECT p.*
FROM posts p
WHERE p.is_published = 1
  AND p.published_date = :date
ORDER BY p.published_at DESC, p.created_at DESC, p.id ASC
LIMIT :limit OFFSET :offset;
```

## 10. Validation Rules

- Required: `external_id`, `slug`, `title`, `content_markdown`, `weight`, `published_date`
- `weight` range: `0..1000`
- `published_date`: `YYYY-MM-DD`
- `published_at`: ISO-8601 UTC if provided
- `slug`: lowercase, `[a-z0-9-]`, max 180 chars
- `title`: max 300 chars
- max tags per post: 20
- max item count and payload size per request

## 11. Security Requirements

- Shared API key auth on bulk endpoint
- Key stored only in Worker secret
- Constant-time compare for auth token
- Rate limiting for ingest and read APIs
- Sanitize markdown-to-HTML output before render

## 12. Performance Requirements

- Indexed queries for today trending/latest
- Pagination on list endpoints
- Cache headers for hot routes
- p95 response target within edge runtime budget

## 13. SEO Requirements (Phase 4)

- `sitemap.xml`
- `rss.xml`
- canonical tags
- Open Graph and Twitter metadata
- `robots.txt`

## 14. Edge Cases

- Duplicate `external_id` in same request
- `slug` conflict with another post
- Invalid/missing date fields
- Negative/overflow weight values
- Empty dataset for today
- Future-dated posts incorrectly shown in today
- Partial item failures in bulk request
- Tag casing normalization (`AI`, `ai`, `Ai`)
- Day-boundary timezone mismatch

## 15. Observability

- Structured logs for:
  - bulk ingest start/finish
  - per-item validation failures
  - query latency and failures
- Correlation request IDs in logs and responses

## 16. Acceptance Criteria

- External agent can bulk post daily with API key.
- Upserts are idempotent by `external_id`.
- Homepage shows today's trending and latest.
- Post detail routes resolve by slug.
- Bookmarks persist in browser `localStorage`.
- SEO endpoints are available in phase 4.
