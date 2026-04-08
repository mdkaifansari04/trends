import sqlite3
from typing import Any


class PostRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "external_id": row["external_id"],
            "slug": row["slug"],
            "title": row["title"],
            "excerpt": row["excerpt"],
            "content_markdown": row["content_markdown"],
            "cover_image_url": row["cover_image_url"],
            "topic": row["topic"],
            "weight": row["weight"],
            "published_date": row["published_date"],
            "published_at": row["published_at"],
            "is_published": row["is_published"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_posts_by_date(self, date_value: str, limit: int, offset: int) -> list[dict[str, Any]]:
        cursor = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE is_published = 1
              AND published_date = ?
            ORDER BY published_at DESC, created_at DESC, id ASC
            LIMIT ? OFFSET ?
            """,
            (date_value, limit, offset),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def list_trending_by_date(self, date_value: str, limit: int) -> list[dict[str, Any]]:
        cursor = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE is_published = 1
              AND published_date = ?
            ORDER BY weight DESC, published_at DESC, created_at DESC, id ASC
            LIMIT ?
            """,
            (date_value, limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_post_by_slug(self, slug: str) -> dict[str, Any] | None:
        cursor = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE is_published = 1
              AND slug = ?
            LIMIT 1
            """,
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)
