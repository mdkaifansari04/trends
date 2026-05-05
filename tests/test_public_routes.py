import json
import sqlite3
from pathlib import Path

import pytest

from src.routes import public
from src.worker import handle_request


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "migrations" / "0001_create_posts.sql"


def _init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(MIGRATION_PATH.read_text())
        conn.commit()
    finally:
        conn.close()


def _seed_posts(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executemany(
            """
            INSERT INTO posts (
                id, external_id, slug, title, excerpt, content_markdown,
                topic, weight, published_date, published_at,
                is_published, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "p-1",
                    "ext-1",
                    "ai-roundup",
                    "AI Roundup",
                    "Daily AI roundup",
                    "# AI Roundup",
                    "AI",
                    70,
                    "2026-04-08",
                    "2026-04-08T04:00:00Z",
                    1,
                    "2026-04-08T04:00:00Z",
                    "2026-04-08T04:00:00Z",
                ),
                (
                    "p-2",
                    "ext-2",
                    "cloud-news",
                    "Cloud News",
                    "Cloud update",
                    "# Cloud News",
                    "Cloud",
                    95,
                    "2026-04-08",
                    "2026-04-08T05:00:00Z",
                    1,
                    "2026-04-08T05:00:00Z",
                    "2026-04-08T05:00:00Z",
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "phase1.db"
    _init_db(db_path)
    _seed_posts(db_path)
    return db_path


def test_get_posts_returns_rows_for_date(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/api/v1/posts?date=2026-04-08&limit=20&offset=0",
        db_path=str(seeded_db),
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert len(payload["items"]) == 2
    assert payload["items"][0]["slug"] in {"ai-roundup", "cloud-news"}


def test_get_post_by_slug_success_and_404(seeded_db: Path) -> None:
    ok_response = handle_request(
        method="GET",
        url="https://example.com/api/v1/posts/ai-roundup",
        db_path=str(seeded_db),
    )
    missing_response = handle_request(
        method="GET",
        url="https://example.com/api/v1/posts/not-found",
        db_path=str(seeded_db),
    )

    assert ok_response.status_code == 200
    ok_payload = json.loads(ok_response.body)
    assert ok_payload["item"]["slug"] == "ai-roundup"

    assert missing_response.status_code == 404


def test_homepage_renders_trending_and_latest_sections(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/",
        db_path=str(seeded_db),
        today="2026-04-08",
    )

    assert response.status_code == 200
    assert "Stop scrolling." in response.body
    assert "Start shipping." in response.body


def test_read_page_renders_trending_and_latest_sections(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/read",
        db_path=str(seeded_db),
        today="2026-04-09",
    )

    assert response.status_code == 200
    assert "Trending Today" in response.body
    assert "Latest Today" in response.body
    assert "Cloud News" in response.body


def test_read_page_includes_bookmark_controls(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/read",
        db_path=str(seeded_db),
        today="2026-04-09",
    )

    assert response.status_code == 200
    assert '/js/bookmarks.js' in response.body
    assert 'data-bookmark-slug="cloud-news"' in response.body
    assert 'aria-pressed="false"' in response.body
    assert "Save bookmark" in response.body


def test_post_detail_includes_bookmark_control(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/posts/cloud-news",
        db_path=str(seeded_db),
    )

    assert response.status_code == 200
    assert 'data-bookmark-slug="cloud-news"' in response.body
    assert 'data-bookmark-title="Cloud News"' in response.body
    assert "Save bookmark" in response.body


def test_post_detail_includes_seo_metadata(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/posts/cloud-news",
        db_path=str(seeded_db),
    )

    assert response.status_code == 200
    assert '<link rel="canonical" href="https://example.com/posts/cloud-news" />' in response.body
    assert '<meta property="og:title" content="Cloud News" />' in response.body
    assert '<meta property="og:type" content="article" />' in response.body
    assert '<meta name="twitter:card" content="summary_large_image" />' in response.body


def test_sitemap_includes_read_page_and_posts(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/sitemap.xml",
        db_path=str(seeded_db),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml; charset=utf-8"
    assert "<urlset" in response.body
    assert "<loc>https://example.com/read</loc>" in response.body
    assert "<loc>https://example.com/posts/cloud-news</loc>" in response.body


def test_rss_includes_recent_posts(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/rss.xml",
        db_path=str(seeded_db),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/rss+xml; charset=utf-8"
    assert "<rss version=\"2.0\">" in response.body
    assert "<title>Trends</title>" in response.body
    assert "<guid>https://example.com/posts/cloud-news</guid>" in response.body


def test_robots_txt_does_not_require_database(tmp_path: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/robots.txt",
        db_path=str(tmp_path / "missing.db"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "User-agent: *" in response.body
    assert "Sitemap: https://example.com/sitemap.xml" in response.body


def test_read_api_sets_cache_and_request_id_headers(seeded_db: Path) -> None:
    response = handle_request(
        method="GET",
        url="https://example.com/api/v1/posts?date=2026-04-08",
        db_path=str(seeded_db),
        headers={"X-Request-ID": "req-test"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=60, s-maxage=300"
    assert response.headers["x-request-id"] == "req-test"


def test_write_api_sets_no_store_and_request_id(tmp_path: Path) -> None:
    db_path = tmp_path / "headers.db"
    _init_db(db_path)

    response = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers={"Authorization": "Bearer secret-token", "X-Request-ID": "req-write"},
        body='{"items": []}',
        ingest_api_key="secret-token",
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "req-write"


def test_landing_route_works_without_opening_database(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.db"
    response = handle_request(
        method="GET",
        url="https://example.com/",
        db_path=str(db_path),
        today="2026-04-08",
    )
    assert response.status_code == 200
    assert "Tech news for builders" in response.body


def test_render_homepage_falls_back_when_template_directory_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(public, "TEMPLATE_DIR", Path("/tmp/non-existent-template-dir"))
    html = public.render_homepage(trending=[], latest=[], date_value="2026-04-08")
    assert "Trending Today" in html
