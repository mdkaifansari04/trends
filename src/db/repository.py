import sqlite3
import uuid
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

    def latest_published_date(self) -> str | None:
        cursor = self.conn.execute(
            """
            SELECT published_date
            FROM posts
            WHERE is_published = 1
            ORDER BY published_date DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row["published_date"]

    def list_recent_posts(self, limit: int) -> list[dict[str, Any]]:
        cursor = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE is_published = 1
            ORDER BY published_at DESC, created_at DESC, id ASC
            LIMIT ?
            """,
            (limit,),
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

    def get_post_by_external_id(self, external_id: str) -> dict[str, Any] | None:
        cursor = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE external_id = ?
            LIMIT 1
            """,
            (external_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_post_by_slug_any(self, slug: str) -> dict[str, Any] | None:
        cursor = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE slug = ?
            LIMIT 1
            """,
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def upsert_post(self, payload: dict[str, Any], now_iso: str) -> tuple[str, str]:
        external_id = payload["external_id"]
        slug = payload["slug"]
        existing = self.get_post_by_external_id(external_id)
        slug_owner = self.get_post_by_slug_any(slug)

        if existing is None and slug_owner is not None and slug_owner["external_id"] != external_id:
            raise ValueError("SLUG_CONFLICT")

        if existing is not None:
            if slug_owner is not None and slug_owner["id"] != existing["id"]:
                raise ValueError("SLUG_CONFLICT")

            self.conn.execute(
                """
                UPDATE posts
                SET slug = ?,
                    title = ?,
                    excerpt = ?,
                    content_markdown = ?,
                    cover_image_url = ?,
                    topic = ?,
                    weight = ?,
                    published_date = ?,
                    published_at = ?,
                    is_published = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    slug,
                    payload["title"],
                    payload.get("excerpt"),
                    payload["content_markdown"],
                    payload.get("cover_image_url"),
                    payload.get("topic"),
                    payload["weight"],
                    payload["published_date"],
                    payload.get("published_at"),
                    payload["is_published"],
                    now_iso,
                    existing["id"],
                ),
            )
            return ("updated", existing["id"])

        post_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO posts (
                id, external_id, slug, title, excerpt, content_markdown,
                cover_image_url, topic, weight, published_date, published_at,
                is_published, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                external_id,
                slug,
                payload["title"],
                payload.get("excerpt"),
                payload["content_markdown"],
                payload.get("cover_image_url"),
                payload.get("topic"),
                payload["weight"],
                payload["published_date"],
                payload.get("published_at"),
                payload["is_published"],
                now_iso,
                now_iso,
            ),
        )
        return ("inserted", post_id)

    def _get_tag_id_by_slug(self, slug: str) -> str | None:
        cursor = self.conn.execute(
            """
            SELECT id
            FROM tags
            WHERE slug = ?
            LIMIT 1
            """,
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row["id"]

    def ensure_tag(self, slug: str, name: str, created_at: str) -> str:
        existing_id = self._get_tag_id_by_slug(slug)
        if existing_id is not None:
            return existing_id

        tag_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO tags (id, slug, name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (tag_id, slug, name, created_at),
        )
        return tag_id

    def replace_post_tags(self, post_id: str, tags: list[tuple[str, str]], created_at: str) -> None:
        self.conn.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        for slug, name in tags:
            tag_id = self.ensure_tag(slug=slug, name=name, created_at=created_at)
            self.conn.execute(
                """
                INSERT OR IGNORE INTO post_tags (post_id, tag_id, created_at)
                VALUES (?, ?, ?)
                """,
                (post_id, tag_id, created_at),
            )
