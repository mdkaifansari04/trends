import json
import sqlite3
from pathlib import Path

from src.worker import handle_request


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "migrations" / "0001_create_posts.sql"


def test_trending_is_sorted_by_weight_desc(tmp_path: Path) -> None:
    db_path = tmp_path / "ranking.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(MIGRATION_PATH.read_text())
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
                    "low",
                    "Low",
                    "",
                    "# Low",
                    "AI",
                    10,
                    "2026-04-08",
                    "2026-04-08T01:00:00Z",
                    1,
                    "2026-04-08T01:00:00Z",
                    "2026-04-08T01:00:00Z",
                ),
                (
                    "p-2",
                    "ext-2",
                    "high",
                    "High",
                    "",
                    "# High",
                    "AI",
                    99,
                    "2026-04-08",
                    "2026-04-08T02:00:00Z",
                    1,
                    "2026-04-08T02:00:00Z",
                    "2026-04-08T02:00:00Z",
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    response = handle_request(
        method="GET",
        url="https://example.com/api/v1/posts/trending?date=2026-04-08&limit=10",
        db_path=str(db_path),
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert [item["slug"] for item in payload["items"]] == ["high", "low"]
