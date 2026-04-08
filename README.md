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
