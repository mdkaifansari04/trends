import json
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urlparse

from src.db.client import get_connection
from src.db.repository import PostRepository
from src.routes.public import render_homepage, render_post_detail


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


def handle_request(method: str, url: str, db_path: str, today: str | None = None) -> AppResponse:
    parsed_url = urlparse(url)
    path = parsed_url.path
    query = parse_qs(parsed_url.query)

    if method.upper() != "GET":
        return _json_response(405, {"error": "Method Not Allowed"})

    date_value = _query_value(query, "date", today or date.today().isoformat())
    limit = _query_int(query, "limit", 20)
    offset = _query_int(query, "offset", 0)

    conn = get_connection(db_path)
    repo = PostRepository(conn)
    try:
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

        if path == "/":
            trending_items = repo.list_trending_by_date(date_value=date_value, limit=10)
            latest_items = repo.list_posts_by_date(date_value=date_value, limit=20, offset=0)
            page_html = render_homepage(trending=trending_items, latest=latest_items, date_value=date_value)
            return _html_response(200, page_html)

        if path.startswith("/posts/"):
            slug = path.replace("/posts/", "", 1)
            post = repo.get_post_by_slug(slug)
            if post is None:
                return _html_response(404, "<h1>Post Not Found</h1>")
            return _html_response(200, render_post_detail(post))

        return _json_response(404, {"error": "Not Found"})
    finally:
        conn.close()
