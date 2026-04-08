import json
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urlparse

from src.db.client import get_connection
from src.db.repository import PostRepository
from src.routes.ingest import handle_bulk_ingest
from src.routes.public import render_landing_page, render_post_detail


@dataclass
class AppResponse:
    status_code: int
    headers: dict[str, str]
    body: str


def _json_response(status_code: int, payload: dict) -> AppResponse:
    return AppResponse(
        status_code=status_code,
        headers={"content-type": "application/json; charset=utf-8"},
        body=json.dumps(payload),
    )


def _html_response(status_code: int, body: str) -> AppResponse:
    return AppResponse(
        status_code=status_code,
        headers={"content-type": "text/html; charset=utf-8"},
        body=body,
    )


def _query_value(query: dict[str, list[str]], name: str, default: str) -> str:
    values = query.get(name)
    if not values:
        return default
    return values[0]


def _query_int(query: dict[str, list[str]], name: str, default: int) -> int:
    raw_value = _query_value(query, name, str(default))
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(0, parsed)


def handle_request(
    method: str,
    url: str,
    db_path: str,
    today: str | None = None,
    headers: dict[str, str] | None = None,
    body: str | None = None,
    ingest_api_key: str = "",
    max_items: int = 100,
    max_body_bytes: int = 1_000_000,
) -> AppResponse:
    parsed_url = urlparse(url)
    path = parsed_url.path
    query = parse_qs(parsed_url.query)

    request_method = method.upper()
    if request_method == "GET" and path == "/":
        return _html_response(200, render_landing_page())

    date_value = _query_value(query, "date", today or date.today().isoformat())
    limit = _query_int(query, "limit", 20)
    offset = _query_int(query, "offset", 0)

    conn = get_connection(db_path)
    repo = PostRepository(conn)
    try:
        if request_method == "POST" and path == "/api/v1/posts/bulk":
            status_code, payload = handle_bulk_ingest(
                repo=repo,
                headers=headers,
                body=body,
                ingest_api_key=ingest_api_key,
                max_items=max_items,
                max_body_bytes=max_body_bytes,
            )
            return _json_response(status_code, payload)

        if request_method != "GET":
            return _json_response(405, {"error": "Method Not Allowed"})

        if path == "/api/v1/health":
            return _json_response(200, {"status": "ok"})

        if path == "/api/v1/posts":
            items = repo.list_posts_by_date(date_value=date_value, limit=limit, offset=offset)
            return _json_response(200, {"items": items})

        if path == "/api/v1/posts/trending":
            items = repo.list_trending_by_date(date_value=date_value, limit=limit)
            return _json_response(200, {"items": items})

        if path.startswith("/api/v1/posts/"):
            slug = path.replace("/api/v1/posts/", "", 1)
            post = repo.get_post_by_slug(slug)
            if post is None:
                return _json_response(404, {"error": "Post Not Found"})
            return _json_response(200, {"item": post})

        if path.startswith("/posts/"):
            slug = path.replace("/posts/", "", 1)
            post = repo.get_post_by_slug(slug)
            if post is None:
                return _html_response(404, "<h1>Post Not Found</h1>")
            return _html_response(200, render_post_detail(post))

        return _json_response(404, {"error": "Not Found"})
    finally:
        conn.close()
