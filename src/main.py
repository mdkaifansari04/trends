from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    # Cloudflare Python Workers runtime (main = "src/main.py")
    from routes.public import render_homepage, render_post_detail
except ModuleNotFoundError:
    # Local test/runtime fallback.
    from src.routes.public import render_homepage, render_post_detail

try:
    from workers import Response, WorkerEntrypoint
except ModuleNotFoundError:
    # Local test fallback when Cloudflare runtime package is unavailable.
    class Response:  # type: ignore[override]
        def __init__(
            self,
            body: str = "",
            status: int = 200,
            headers: dict[str, str] | None = None,
        ) -> None:
            self.body = body
            self.status = status
            self.headers = headers or {}

        @staticmethod
        def json(payload: dict[str, Any], status: int = 200) -> "Response":
            return Response(
                body=json.dumps(payload),
                status=status,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

    class WorkerEntrypoint:  # type: ignore[override]
        def __init__(self, env: Any | None = None) -> None:
            self.env = env


def _coerce_rows(result: Any) -> list[dict[str, Any]]:
    rows: Any = None
    if isinstance(result, dict):
        rows = result.get("results")
    else:
        rows = getattr(result, "results", None)
        if rows is None:
            to_py = getattr(result, "to_py", None)
            if callable(to_py):
                python_value = to_py()
                if isinstance(python_value, dict):
                    rows = python_value.get("results")

    if not isinstance(rows, list):
        return []

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(row)
            continue

        row_to_py = getattr(row, "to_py", None)
        if callable(row_to_py):
            converted = row_to_py()
            if isinstance(converted, dict):
                normalized.append(converted)
    return normalized


class Default(WorkerEntrypoint):
    async def fetch(self, request):  # pragma: no cover - Cloudflare runtime signature
        url = urlparse(request.url)
        params = parse_qs(url.query)
        path = url.path
        method = getattr(request, "method", "GET").upper()

        if path == "/favicon.ico":
            return Response("")

        if method != "GET":
            return self._json_response({"error": "Method Not Allowed"}, status=405)

        if path == "/api/v1/health":
            return self._json_response({"status": "ok"})

        date_value = params.get("date", [self._today_iso()])[0]
        limit = self._query_int(params, "limit", 20)
        offset = self._query_int(params, "offset", 0)

        if path == "/api/v1/posts":
            items = await self._query_posts(date_value=date_value, limit=limit, offset=offset)
            return self._json_response({"items": items})

        if path == "/api/v1/posts/trending":
            items = await self._query_trending(date_value=date_value, limit=limit)
            return self._json_response({"items": items})

        if path.startswith("/api/v1/posts/"):
            slug = path.replace("/api/v1/posts/", "", 1)
            post = await self._query_post_by_slug(slug)
            if post is None:
                return self._json_response({"error": "Post Not Found"}, status=404)
            return self._json_response({"item": post})

        if path == "/":
            trending = await self._query_trending(date_value=date_value, limit=10)
            latest = await self._query_posts(date_value=date_value, limit=20, offset=0)
            html = render_homepage(trending=trending, latest=latest, date_value=date_value)
            return self._html_response(html)

        if path.startswith("/posts/"):
            slug = path.replace("/posts/", "", 1)
            post = await self._query_post_by_slug(slug)
            if post is None:
                return self._html_response("<h1>Post Not Found</h1>", status=404)
            return self._html_response(render_post_detail(post))

        return self._json_response({"error": "Not Found"}, status=404)

    async def _query_posts(self, date_value: str, limit: int, offset: int) -> list[dict[str, Any]]:
        sql = (
            "SELECT * FROM posts "
            "WHERE is_published = 1 AND published_date = ? "
            "ORDER BY published_at DESC, created_at DESC, id ASC "
            "LIMIT ? OFFSET ?"
        )
        return await self._run_rows_query(sql, date_value, limit, offset)

    async def _query_trending(self, date_value: str, limit: int) -> list[dict[str, Any]]:
        sql = (
            "SELECT * FROM posts "
            "WHERE is_published = 1 AND published_date = ? "
            "ORDER BY weight DESC, published_at DESC, created_at DESC, id ASC "
            "LIMIT ?"
        )
        return await self._run_rows_query(sql, date_value, limit)

    async def _query_post_by_slug(self, slug: str) -> dict[str, Any] | None:
        sql = (
            "SELECT * FROM posts "
            "WHERE is_published = 1 AND slug = ? "
            "LIMIT 1"
        )
        rows = await self._run_rows_query(sql, slug)
        if not rows:
            return None
        return rows[0]

    async def _run_rows_query(self, sql: str, *bindings: Any) -> list[dict[str, Any]]:
        stmt = self.env.DB.prepare(sql)
        if bindings:
            stmt = stmt.bind(*bindings)
        result = await stmt.run()
        return _coerce_rows(result)

    @staticmethod
    def _today_iso() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    @staticmethod
    def _query_int(params: dict[str, list[str]], key: str, default: int) -> int:
        values = params.get(key)
        if not values:
            return default
        try:
            parsed = int(values[0])
        except ValueError:
            return default
        return max(0, parsed)

    @staticmethod
    def _json_response(payload: dict[str, Any], status: int = 200):
        return Response(
            json.dumps(payload),
            status=status,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    @staticmethod
    def _html_response(body: str, status: int = 200):
        return Response(
            body,
            status=status,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
