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
