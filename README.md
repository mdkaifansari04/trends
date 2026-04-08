# Trends

Minimal Cloudflare Python Worker-based news reader.

## Phase 1 Status

- Public read APIs for posts and trending
- Homepage and post detail HTML rendering
- SQL migration for posts, tags, and post_tags
- Pytest coverage for routing and ranking behavior

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
