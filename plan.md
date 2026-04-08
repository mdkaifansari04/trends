# Trends Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready Cloudflare Python Worker news site that reads posts from a relational schema and supports authenticated bulk ingest from an external daily posting agent.

**Architecture:** A Python Worker serves both HTML pages and JSON APIs. Relational storage is used for post records with `weight`-based ranking for trending output. Frontend is minimal HTML + Tailwind with client-only bookmarks in `localStorage`, then SEO hardening in the final phase.

**Tech Stack:** Cloudflare Python Worker, SQL relational database (Cloudflare relational service), HTML templates, Tailwind CSS, Pytest, Wrangler.

---

## Planned File Structure

- Create: `wrangler.toml`
- Create: `requirements.txt`
- Create: `src/worker.py`
- Create: `src/config.py`
- Create: `src/routes/public.py`
- Create: `src/routes/ingest.py`
- Create: `src/services/post_service.py`
- Create: `src/db/client.py`
- Create: `src/db/repository.py`
- Create: `migrations/0001_create_posts.sql`
- Create: `templates/base.html`
- Create: `templates/home.html`
- Create: `templates/post_detail.html`
- Create: `static/css/input.css`
- Create: `static/css/output.css`
- Create: `static/js/bookmarks.js`
- Create: `tests/test_public_routes.py`
- Create: `tests/test_ingest_bulk_api.py`
- Create: `tests/test_post_ranking.py`
- Create: `tests/test_bookmarks_ui.md` (manual test notes/checklist)
- Create: `README.md`

## Phase Dependency Contract

- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 2.
- Phase 4 depends on Phase 3.
- Each phase must be merged only after its phase checklist and human testing are complete.

---

### Task 1: Phase 1 - Foundation + Public Read Path

**Files:**
- Create: `wrangler.toml`
- Create: `src/worker.py`
- Create: `src/routes/public.py`
- Create: `src/db/client.py`
- Create: `src/db/repository.py`
- Create: `migrations/0001_create_posts.sql`
- Create: `templates/base.html`
- Create: `templates/home.html`
- Create: `templates/post_detail.html`
- Create: `static/css/input.css`
- Create: `static/css/output.css`
- Test: `tests/test_public_routes.py`
- Test: `tests/test_post_ranking.py`

- [ ] **Step 1: Write failing tests for public routes and ranking**
  - Add tests for:
    - `GET /api/v1/posts` returns posts for date
    - `GET /api/v1/posts/trending` sorts by `weight desc`
    - `GET /api/v1/posts/:slug` returns 200 for valid slug and 404 for invalid slug
    - homepage HTML renders trending + latest blocks

- [ ] **Step 2: Run tests and confirm failure**
  - Run: `uv run --extra dev pytest tests/test_public_routes.py tests/test_post_ranking.py -v`
  - Expected: failures due to missing app/routes/repository

- [ ] **Step 3: Implement minimal schema, repository, read routes, and HTML pages**
  - Add SQL migration for `posts`, `tags`, and `post_tags` tables with indexes
  - Add repository query methods:
    - `list_posts_by_date(date, limit, offset)`
    - `list_trending_by_date(date, limit)`
    - `get_post_by_slug(slug)`
  - Add HTML routes for home and post detail
  - Add Tailwind baseline + minimal clean layout

- [ ] **Step 4: Run tests and confirm pass**
  - Run: `uv run --extra dev pytest tests/test_public_routes.py tests/test_post_ranking.py -v`
  - Expected: all pass

- [ ] **Step 5: Human testing for Phase 1**
  1. Start local app and open homepage.
  2. Verify trending cards ordered by `weight`.
  3. Open detail page and verify content renders.
  4. Verify empty-state message when DB has no rows.
  5. Check desktop and mobile layout for no broken UI.

- [ ] **Step 6: Commit**
  - Commit message: `feat(phase-1): scaffold worker with read APIs and base UI`

**Phase 1 Exit Criteria**
- Public read APIs and pages are stable and reviewable.
- No broken navigation or missing baseline states.

---

### Task 2: Phase 2 - Bulk Ingest API + Data Integrity

**Files:**
- Create: `src/routes/ingest.py`
- Modify: `src/worker.py`
- Modify: `src/config.py`
- Modify: `src/services/post_service.py`
- Modify: `src/db/repository.py`
- Test: `tests/test_ingest_bulk_api.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests for authenticated bulk ingest**
  - Add tests for:
    - valid bulk payload inserts records
    - duplicate `external_id` is upserted (not duplicated)
    - missing API key returns 401/403
    - mixed valid/invalid items returns partial success structure
    - oversized payload returns 413 or validation error

- [ ] **Step 2: Run tests and confirm failure**
  - Run: `uv run --extra dev pytest tests/test_ingest_bulk_api.py -v`
  - Expected: failures due to missing endpoint/auth/validation

- [ ] **Step 3: Implement bulk ingest endpoint and validation**
  - Add `POST /api/v1/posts/bulk`
  - Authenticate using API key from Worker environment secret
  - Validate required fields and types
  - Normalize slug/date/tag payload fields
  - Upsert by `external_id`
  - Upsert/resolve tags and maintain `post_tags` relation
  - Return `inserted`, `updated`, `failed`, `errors[]`
  - Add API key auth guard and basic rate limiting

- [ ] **Step 4: Run tests and confirm pass**
  - Run: `uv run --extra dev pytest tests/test_ingest_bulk_api.py -v`
  - Expected: all pass

- [ ] **Step 5: Human testing for Phase 2**
  1. Send valid bulk request with API key and verify homepage updates.
  2. Replay same payload and verify no duplicate posts.
  3. Send request without API key and verify rejection.
  4. Send malformed item and verify error payload includes item index.
  5. Send mixed payload and verify partial success counts are accurate.

- [ ] **Step 6: Commit**
  - Commit message: `feat(phase-2): add authenticated bulk ingest with upsert and validation`

**Phase 2 Exit Criteria**
- External posting agent can safely bulk ingest daily content.
- Ingest is idempotent and resilient to malformed inputs.

---

### Task 3: Phase 3 - Reader UX Completion + Local Bookmarks

**Files:**
- Modify: `templates/home.html`
- Modify: `templates/post_detail.html`
- Create: `static/js/bookmarks.js`
- Modify: `static/css/input.css`
- Modify: `static/css/output.css`
- Modify: `src/routes/public.py`
- Create: `tests/test_bookmarks_ui.md` (manual checklist + evidence notes)

- [ ] **Step 1: Add bookmark behavior and UI hooks**
  - Add bookmark button on post cards/detail
  - Persist bookmarked slugs/ids in `localStorage`
  - Render bookmarked state consistently on refresh

- [ ] **Step 2: Add daily/fallback UX rules**
  - Display "today" content by default
  - If no posts for today, show clear fallback/empty message
  - Keep response and UI behavior deterministic at day boundaries

- [ ] **Step 3: Improve responsive polish and integrate selected Google font**
  - Apply finalized minimal style direction
  - Ensure text hierarchy and spacing are consistent
  - Verify mobile readability and interaction touch targets

- [ ] **Step 4: Verify no regressions**
  - Run: `uv run --extra dev pytest tests/test_public_routes.py tests/test_post_ranking.py tests/test_ingest_bulk_api.py -v`
  - Expected: all pass

- [ ] **Step 5: Human testing for Phase 3**
  1. Bookmark and unbookmark posts from both home and detail pages.
  2. Reload browser and verify bookmark persistence.
  3. Confirm bookmarks remain local to that browser.
  4. Validate behavior when there are no posts today.
  5. Validate desktop and mobile UX quality.

- [ ] **Step 6: Commit**
  - Commit message: `feat(phase-3): add local bookmarks and refine reader UX`

**Phase 3 Exit Criteria**
- Reader experience is complete for MVP usage.
- Bookmark feature works reliably without server state.

---

### Task 4: Phase 4 - SEO + Production Hardening

**Files:**
- Modify: `src/routes/public.py`
- Modify: `templates/base.html`
- Create: `templates/rss.xml`
- Create: `templates/sitemap.xml`
- Create: `public/robots.txt`
- Modify: `wrangler.toml`
- Modify: `README.md`
- Optional: `src/middleware/request_logging.py`

- [ ] **Step 1: Add SEO output routes and metadata**
  - Implement `GET /sitemap.xml`
  - Implement `GET /rss.xml`
  - Add canonical link tags on post pages
  - Add OG/Twitter meta tags
  - Serve `robots.txt`

- [ ] **Step 2: Add caching and observability**
  - Add cache headers for hot read routes/pages
  - Add structured request logging and basic request IDs
  - Add clear operational error logging for ingest and read paths

- [ ] **Step 3: Validate final regression suite**
  - Run: `uv run --extra dev pytest -v`
  - Expected: all pass

- [ ] **Step 4: Human testing for Phase 4**
  1. Open `/sitemap.xml` and verify valid URL list.
  2. Open `/rss.xml` and verify parseable feed.
  3. Inspect page source for canonical + OG tags.
  4. Open `/robots.txt` and verify expected directives.
  5. Perform end-to-end smoke test for home, detail, and ingest APIs.

- [ ] **Step 5: Commit**
  - Commit message: `feat(phase-4): add seo routes and production hardening`

**Phase 4 Exit Criteria**
- SEO baseline is complete and validated.
- App is launch-ready with logging and cache strategy in place.

---

## Global Quality Gates

- No phase completion without human testing evidence.
- No unresolved failing automated tests before phase handoff.
- No phase may break functionality shipped in earlier phases.

## Delivery Flow

1. Complete one phase.
2. Run automated + human tests for that phase.
3. Review and sign off.
4. Start next phase.
