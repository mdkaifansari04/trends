# Trends

Minimal Cloudflare Python Worker-based news reader.

## Phase 1 Status

- Public read APIs for posts and trending
- Landing page (`/`), reader page (`/read`), and post detail page (`/posts/:slug`)
- Client-side bookmarks backed by `localStorage`
- SEO routes (`/sitemap.xml`, `/rss.xml`, `/robots.txt`) and post metadata
- Cache headers and request ID response headers on runtime routes
- SQL migration for posts, tags, and post_tags
- Pytest coverage for routing, ranking, ingest, bookmarks, SEO, and headers

## Run tests

```bash
uv sync
uv run --extra dev pytest -v
```

## D1 setup for `wrangler dev`

The Worker expects a D1 binding named `DB`.

1. Create a D1 database:

```bash
wrangler d1 create trends
```

2. Copy the returned `database_id` and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "trends"
database_id = "<your-database-id>"
migrations_dir = "migrations"
```

3. Apply migrations:

```bash
wrangler d1 migrations apply trends --local
```

## Quick local demo (reading page + sample entries)

1. Add a local ingest key for `wrangler dev` in `.dev.vars`:

```bash
echo "INGEST_API_KEY=dev-secret" > .dev.vars
```

2. Start the Worker:

```bash
wrangler dev
```

3. In another terminal, ingest demo posts:

```bash
curl -X POST "http://127.0.0.1:8787/api/v1/posts/bulk" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  --data-binary @demo/demo_posts.json
```

4. Open:

- `http://127.0.0.1:8787/` (landing page)
- `http://127.0.0.1:8787/read` (reader feed with trending/latest cards)
- `http://127.0.0.1:8787/posts/cloudflare-python-workers-update` (post detail page)

## Internal flow

1. `POST /api/v1/posts/bulk` validates payload and auth (`INGEST_API_KEY`), then upserts rows in `posts` and related tags.
2. `GET /read` reads the latest available `published_date` when `?date=` is not provided, then queries both:
   - trending list: weight desc + recency
   - latest list: recency
3. Clicking a card opens `GET /posts/:slug`, which loads one published row and renders the detail template.
