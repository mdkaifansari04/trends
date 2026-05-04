from __future__ import annotations

import hmac
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    # Cloudflare Python Workers runtime (main = "src/main.py")
    from routes.public import render_homepage, render_landing_page, render_post_detail, render_robots_txt, render_rss, render_sitemap

except ModuleNotFoundError:
    # Local test/runtime fallback.
    from src.routes.public import render_homepage, render_landing_page, render_post_detail, render_robots_txt, render_rss, render_sitemap

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
        base_url = f"{url.scheme}://{url.netloc}"
        request_id = self._request_id(request)

        def finish(response):
            return self._decorate_response(response, method, path, request_id)

        if path == "/favicon.ico":
            return finish(Response(""))

        if method == "GET" and path == "/robots.txt":
            return finish(self._text_response(render_robots_txt(base_url)))

        if path == "/":
            return finish(self._html_response(render_landing_page()))

        if self._route_requires_db(path) and not self._has_db_binding():
            return finish(self._db_binding_error_response(path))

        if method == "POST" and path == "/api/v1/posts/bulk":
            return finish(await self._handle_bulk_ingest(request))

        if method != "GET":
            return finish(self._json_response({"error": "Method Not Allowed"}, status=405))

        if path == "/api/v1/health":
            return finish(self._json_response({"status": "ok"}))

        if path == "/read":
            date_values = params.get("date")
            page_date = (
                date_values[0]
                if date_values and date_values[0]
                else (await self._query_latest_published_date() or self._today_iso())
            )
            trending = await self._query_trending(date_value=page_date, limit=10)
            latest = await self._query_posts(date_value=page_date, limit=20, offset=0)
            html = render_homepage(trending=trending, latest=latest, date_value=page_date, base_url=base_url)
            return finish(self._html_response(html))

        if path == "/sitemap.xml":
            posts = await self._query_recent_posts(limit=1000)
            return finish(self._xml_response(render_sitemap(posts, base_url)))

        if path == "/rss.xml":
            posts = await self._query_recent_posts(limit=50)
            return finish(self._xml_response(render_rss(posts, base_url), content_type="application/rss+xml"))

        date_value = params.get("date", [self._today_iso()])[0]
        limit = self._query_int(params, "limit", 20)
        offset = self._query_int(params, "offset", 0)

        if path == "/api/v1/posts":
            items = await self._query_posts(date_value=date_value, limit=limit, offset=offset)
            return finish(self._json_response({"items": items}))

        if path == "/api/v1/posts/trending":
            items = await self._query_trending(date_value=date_value, limit=limit)
            return finish(self._json_response({"items": items}))

        if path.startswith("/api/v1/posts/"):
            slug = path.replace("/api/v1/posts/", "", 1)
            post = await self._query_post_by_slug(slug)
            if post is None:
                return finish(self._json_response({"error": "Post Not Found"}, status=404))
            return finish(self._json_response({"item": post}))

        if path.startswith("/posts/"):
            slug = path.replace("/posts/", "", 1)
            post = await self._query_post_by_slug(slug)
            if post is None:
                return finish(self._html_response("<h1>Post Not Found</h1>", status=404))
            return finish(self._html_response(render_post_detail(post, base_url=base_url)))

        return finish(self._json_response({"error": "Not Found"}, status=404))

    async def _handle_bulk_ingest(self, request):
        ingest_api_key = getattr(self.env, "INGEST_API_KEY", "")
        if not ingest_api_key:
            return self._json_response({"error": "Ingest API key is not configured"}, status=500)

        auth_value = self._header_value(request, "Authorization")
        token = self._parse_bearer(auth_value)
        if not token or not hmac.compare_digest(token, ingest_api_key):
            return self._json_response({"error": "Unauthorized"}, status=401)

        raw_body = await request.text()
        if len(raw_body.encode("utf-8")) > 1_000_000:
            return self._json_response({"error": "Payload Too Large"}, status=413)

        try:
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            return self._json_response({"error": "Invalid JSON body"}, status=400)

        items = payload.get("items")
        if not isinstance(items, list):
            return self._json_response({"error": "`items` must be an array"}, status=400)
        if len(items) > 100:
            return self._json_response({"error": "`items` cannot exceed 100"}, status=400)

        inserted = 0
        updated = 0
        failed = 0
        errors: list[dict[str, Any]] = []
        seen_external_ids: set[str] = set()

        for index, item in enumerate(items):
            normalized, error = self._validate_ingest_item(index, item)
            if error is not None:
                failed += 1
                errors.append(error)
                continue
            assert normalized is not None

            external_id = normalized["external_id"]
            if external_id in seen_external_ids:
                failed += 1
                errors.append(
                    {
                        "index": index,
                        "external_id": external_id,
                        "error_code": "DUPLICATE_EXTERNAL_ID_IN_BATCH",
                        "reason": "duplicate external_id in payload",
                    }
                )
                continue
            seen_external_ids.add(external_id)

            try:
                action, post_id = await self._upsert_post(normalized)
                await self._replace_post_tags(post_id=post_id, tags=normalized["tags"])
                if action == "inserted":
                    inserted += 1
                else:
                    updated += 1
            except ValueError as exc:
                failed += 1
                code = str(exc)
                if code == "SLUG_CONFLICT":
                    errors.append(
                        {
                            "index": index,
                            "external_id": external_id,
                            "error_code": "SLUG_CONFLICT",
                            "reason": "slug already assigned to another post",
                        }
                    )
                else:
                    errors.append(
                        {
                            "index": index,
                            "external_id": external_id,
                            "error_code": "INGEST_VALIDATION_ERROR",
                            "reason": str(exc),
                        }
                    )

        return self._json_response(
            {"success": True, "inserted": inserted, "updated": updated, "failed": failed, "errors": errors}
        )

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

    async def _query_recent_posts(self, limit: int) -> list[dict[str, Any]]:
        sql = (
            "SELECT * FROM posts "
            "WHERE is_published = 1 "
            "ORDER BY published_at DESC, created_at DESC, id ASC "
            "LIMIT ?"
        )
        return await self._run_rows_query(sql, limit)

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

    async def _query_latest_published_date(self) -> str | None:
        rows = await self._run_rows_query(
            "SELECT published_date FROM posts WHERE is_published = 1 ORDER BY published_date DESC LIMIT 1"
        )
        if not rows:
            return None
        value = rows[0].get("published_date")
        if value is None:
            return None
        return str(value)

    async def _run_rows_query(self, sql: str, *bindings: Any) -> list[dict[str, Any]]:
        stmt = self._db_binding().prepare(sql)
        if bindings:
            stmt = stmt.bind(*bindings)
        result = await stmt.run()
        return _coerce_rows(result)

    async def _run_exec(self, sql: str, *bindings: Any) -> None:
        stmt = self._db_binding().prepare(sql)
        if bindings:
            stmt = stmt.bind(*bindings)
        await stmt.run()

    async def _upsert_post(self, payload: dict[str, Any]) -> tuple[str, str]:
        existing = await self._run_rows_query(
            "SELECT id, external_id, slug FROM posts WHERE external_id = ? LIMIT 1",
            payload["external_id"],
        )
        slug_owner = await self._run_rows_query(
            "SELECT id, external_id, slug FROM posts WHERE slug = ? LIMIT 1",
            payload["slug"],
        )

        existing_row = existing[0] if existing else None
        slug_owner_row = slug_owner[0] if slug_owner else None

        if existing_row is None and slug_owner_row is not None and slug_owner_row["external_id"] != payload["external_id"]:
            raise ValueError("SLUG_CONFLICT")

        now_iso = self._now_iso_datetime()
        if existing_row is not None:
            if slug_owner_row is not None and slug_owner_row["id"] != existing_row["id"]:
                raise ValueError("SLUG_CONFLICT")
            await self._run_exec(
                """
                UPDATE posts
                SET slug = ?, title = ?, excerpt = ?, content_markdown = ?,
                    cover_image_url = ?, topic = ?, weight = ?, published_date = ?,
                    published_at = ?, is_published = ?, updated_at = ?
                WHERE id = ?
                """,
                payload["slug"],
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
                existing_row["id"],
            )
            return ("updated", existing_row["id"])

        post_id = str(uuid.uuid4())
        await self._run_exec(
            """
            INSERT INTO posts (
                id, external_id, slug, title, excerpt, content_markdown,
                cover_image_url, topic, weight, published_date, published_at,
                is_published, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            post_id,
            payload["external_id"],
            payload["slug"],
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
        )
        return ("inserted", post_id)

    async def _replace_post_tags(self, post_id: str, tags: list[tuple[str, str]]) -> None:
        await self._run_exec("DELETE FROM post_tags WHERE post_id = ?", post_id)
        now_iso = self._now_iso_datetime()
        for tag_slug, tag_name in tags:
            rows = await self._run_rows_query("SELECT id FROM tags WHERE slug = ? LIMIT 1", tag_slug)
            if rows:
                tag_id = rows[0]["id"]
            else:
                tag_id = str(uuid.uuid4())
                await self._run_exec(
                    "INSERT INTO tags (id, slug, name, created_at) VALUES (?, ?, ?, ?)",
                    tag_id,
                    tag_slug,
                    tag_name,
                    now_iso,
                )
            await self._run_exec(
                "INSERT OR IGNORE INTO post_tags (post_id, tag_id, created_at) VALUES (?, ?, ?)",
                post_id,
                tag_id,
                now_iso,
            )

    @staticmethod
    def _today_iso() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    @staticmethod
    def _now_iso_datetime() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

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
    def _header_value(request: Any, key: str) -> str:
        headers = getattr(request, "headers", None)
        if headers is None:
            return ""
        if isinstance(headers, dict):
            return str(headers.get(key) or headers.get(key.lower()) or "")
        getter = getattr(headers, "get", None)
        if callable(getter):
            return str(getter(key) or getter(key.lower()) or "")
        return ""

    def _request_id(self, request: Any) -> str:
        return self._header_value(request, "X-Request-ID") or str(uuid.uuid4())

    @staticmethod
    def _cache_control(method: str, path: str, status: int) -> str:
        if method != "GET" or status >= 400:
            return "no-store"
        if path == "/robots.txt":
            return "public, max-age=3600"
        if path in {"/", "/read", "/sitemap.xml", "/rss.xml"} or path.startswith("/posts/") or path.startswith("/api/v1/posts"):
            return "public, max-age=60, s-maxage=300"
        return "no-store"

    def _decorate_response(self, response, method: str, path: str, request_id: str):
        headers = {}
        response_headers = getattr(response, "headers", None)
        if response_headers is not None:
            items = getattr(response_headers, "items", None)
            if callable(items):
                headers.update({str(key): str(value) for key, value in items()})

        headers.setdefault("X-Request-ID", request_id)
        headers.setdefault("Cache-Control", self._cache_control(method, path, response.status))
        return Response(getattr(response, "body", ""), status=response.status, headers=headers)

    @staticmethod
    def _parse_bearer(value: str) -> str:
        if not value.startswith("Bearer "):
            return ""
        return value[7:].strip()

    @staticmethod
    def _normalize_slug(value: str) -> str:
        return value.strip().lower()

    @staticmethod
    def _normalize_tag(value: str) -> tuple[str, str]:
        cleaned = value.strip()
        slug = re.sub(r"[^a-z0-9-]+", "-", cleaned.lower()).strip("-")
        slug = re.sub(r"-{2,}", "-", slug)
        return slug, cleaned

    def _has_db_binding(self) -> bool:
        env = getattr(self, "env", None)
        return env is not None and (hasattr(env, "DB") or hasattr(env, "trends"))

    def _db_binding(self):
        env = getattr(self, "env", None)
        if env is None:
            raise AttributeError("DB")
        if hasattr(env, "DB"):
            return getattr(env, "DB")
        if hasattr(env, "trends"):
            return getattr(env, "trends")
        raise AttributeError("DB")

    @staticmethod
    def _route_requires_db(path: str) -> bool:
        return path in {"/read", "/sitemap.xml", "/rss.xml"} or path.startswith("/posts/") or path.startswith("/api/v1/posts")

    def _db_binding_error_response(self, path: str):
        message = (
            "DB binding is missing. Add a D1 binding named 'DB' in wrangler.toml under [[d1_databases]] "
            "and apply migrations before running the Worker."
        )
        if path.startswith("/api/"):
            return self._json_response({"error": message}, status=500)
        return self._html_response(f"<h1>Configuration Error</h1><p>{message}</p>", status=500)

    def _validate_ingest_item(self, index: int, item: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        required_fields = ("external_id", "slug", "title", "content_markdown", "weight", "published_date")
        slug_re = re.compile(r"^[a-z0-9-]{1,180}$")
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        if not isinstance(item, dict):
            return None, {"index": index, "error_code": "INVALID_ITEM", "reason": "item must be an object"}

        missing = [name for name in required_fields if item.get(name) in (None, "")]
        if missing:
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "MISSING_FIELDS",
                "reason": f"missing required fields: {', '.join(missing)}",
            }

        try:
            weight = int(item["weight"])
        except (TypeError, ValueError):
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_WEIGHT",
                "reason": "weight must be an integer",
            }
        if weight < 0 or weight > 1000:
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_WEIGHT_RANGE",
                "reason": "weight must be between 0 and 1000",
            }

        slug = self._normalize_slug(str(item["slug"]))
        if not slug_re.fullmatch(slug):
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_SLUG",
                "reason": "slug must match [a-z0-9-] and be <= 180 chars",
            }

        published_date = str(item["published_date"]).strip()
        if not date_re.fullmatch(published_date):
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_PUBLISHED_DATE",
                "reason": "published_date must be YYYY-MM-DD",
            }

        tags = item.get("tags", [])
        if tags is None:
            tags = []
        if not isinstance(tags, list):
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_TAGS",
                "reason": "tags must be an array",
            }
        if len(tags) > 20:
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "TOO_MANY_TAGS",
                "reason": "tags cannot exceed 20",
            }

        normalized_tags: list[tuple[str, str]] = []
        seen_tag_slugs: set[str] = set()
        for raw_tag in tags:
            if not isinstance(raw_tag, str) or not raw_tag.strip():
                return None, {
                    "index": index,
                    "external_id": item.get("external_id"),
                    "error_code": "INVALID_TAG",
                    "reason": "each tag must be a non-empty string",
                }
            tag_slug, tag_name = self._normalize_tag(raw_tag)
            if not tag_slug:
                return None, {
                    "index": index,
                    "external_id": item.get("external_id"),
                    "error_code": "INVALID_TAG",
                    "reason": "tag contains no valid characters",
                }
            if tag_slug in seen_tag_slugs:
                continue
            seen_tag_slugs.add(tag_slug)
            normalized_tags.append((tag_slug, tag_name))

        normalized = {
            "external_id": str(item["external_id"]).strip(),
            "slug": slug,
            "title": str(item["title"]).strip(),
            "excerpt": item.get("excerpt"),
            "content_markdown": str(item["content_markdown"]),
            "cover_image_url": item.get("cover_image_url"),
            "topic": item.get("topic"),
            "weight": weight,
            "published_date": published_date,
            "published_at": item.get("published_at"),
            "is_published": 1 if item.get("is_published", True) else 0,
            "tags": normalized_tags,
        }
        return normalized, None

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

    @staticmethod
    def _xml_response(body: str, status: int = 200, content_type: str = "application/xml"):
        return Response(
            body,
            status=status,
            headers={"Content-Type": f"{content_type}; charset=utf-8"},
        )

    @staticmethod
    def _text_response(body: str, status: int = 200):
        return Response(
            body,
            status=status,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
