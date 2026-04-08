import json
import sqlite3
from pathlib import Path

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


def _count_rows(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return count
    finally:
        conn.close()


def _get_title_by_external_id(db_path: Path, external_id: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT title FROM posts WHERE external_id = ? LIMIT 1",
            (external_id,),
        ).fetchone()
        assert row is not None
        return row[0]
    finally:
        conn.close()


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer secret-token"}


def test_bulk_ingest_inserts_valid_items(tmp_path: Path) -> None:
    db_path = tmp_path / "ingest_valid.db"
    _init_db(db_path)

    payload = {
        "items": [
            {
                "external_id": "ext-1",
                "slug": "ai-roundup-apr-08",
                "title": "AI Roundup",
                "excerpt": "Daily AI",
                "content_markdown": "# AI",
                "topic": "AI",
                "tags": ["ai", "open-source"],
                "weight": 90,
                "published_date": "2026-04-08",
                "published_at": "2026-04-08T10:00:00Z",
            },
            {
                "external_id": "ext-2",
                "slug": "cloud-roundup-apr-08",
                "title": "Cloud Roundup",
                "excerpt": "Daily Cloud",
                "content_markdown": "# Cloud",
                "topic": "Cloud",
                "tags": ["cloud"],
                "weight": 80,
                "published_date": "2026-04-08",
                "published_at": "2026-04-08T11:00:00Z",
            },
        ]
    }

    response = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers=_auth_headers(),
        body=json.dumps(payload),
        ingest_api_key="secret-token",
    )

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["inserted"] == 2
    assert data["updated"] == 0
    assert data["failed"] == 0
    assert _count_rows(db_path, "posts") == 2
    assert _count_rows(db_path, "tags") == 3
    assert _count_rows(db_path, "post_tags") == 3


def test_bulk_ingest_upserts_duplicate_external_id(tmp_path: Path) -> None:
    db_path = tmp_path / "ingest_upsert.db"
    _init_db(db_path)

    first_payload = {
        "items": [
            {
                "external_id": "ext-1",
                "slug": "ai-roundup-apr-08",
                "title": "AI Roundup v1",
                "content_markdown": "# AI",
                "weight": 60,
                "published_date": "2026-04-08",
            }
        ]
    }
    second_payload = {
        "items": [
            {
                "external_id": "ext-1",
                "slug": "ai-roundup-apr-08",
                "title": "AI Roundup v2",
                "content_markdown": "# AI Updated",
                "weight": 99,
                "published_date": "2026-04-08",
            }
        ]
    }

    first = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers=_auth_headers(),
        body=json.dumps(first_payload),
        ingest_api_key="secret-token",
    )
    second = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers=_auth_headers(),
        body=json.dumps(second_payload),
        ingest_api_key="secret-token",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    second_data = json.loads(second.body)
    assert second_data["inserted"] == 0
    assert second_data["updated"] == 1
    assert _count_rows(db_path, "posts") == 1
    assert _get_title_by_external_id(db_path, "ext-1") == "AI Roundup v2"


def test_bulk_ingest_requires_api_key(tmp_path: Path) -> None:
    db_path = tmp_path / "ingest_auth.db"
    _init_db(db_path)

    response = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers={},
        body=json.dumps({"items": []}),
        ingest_api_key="secret-token",
    )

    assert response.status_code == 401


def test_bulk_ingest_partial_success_for_mixed_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "ingest_partial.db"
    _init_db(db_path)

    mixed_payload = {
        "items": [
            {
                "external_id": "ext-bad",
                "slug": "bad-item",
                "content_markdown": "# missing title",
                "weight": 10,
                "published_date": "2026-04-08",
            },
            {
                "external_id": "ext-good",
                "slug": "good-item",
                "title": "Good Item",
                "content_markdown": "# good",
                "weight": 50,
                "published_date": "2026-04-08",
            },
        ]
    }

    response = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers=_auth_headers(),
        body=json.dumps(mixed_payload),
        ingest_api_key="secret-token",
    )

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["inserted"] == 1
    assert data["updated"] == 0
    assert data["failed"] == 1
    assert data["errors"][0]["index"] == 0
    assert _count_rows(db_path, "posts") == 1


def test_bulk_ingest_rejects_oversized_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "ingest_size.db"
    _init_db(db_path)

    payload = {"items": [{"external_id": "ext-1", "slug": "big", "title": "Big", "content_markdown": "x" * 500}]}

    response = handle_request(
        method="POST",
        url="https://example.com/api/v1/posts/bulk",
        db_path=str(db_path),
        headers=_auth_headers(),
        body=json.dumps(payload),
        ingest_api_key="secret-token",
        max_body_bytes=128,
    )

    assert response.status_code == 413
