import json
import uuid
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urlparse

from src.db.client import get_connection
from src.db.repository import PostRepository
from src.routes.ingest import handle_bulk_ingest
from src.routes.public import render_homepage, render_landing_page, render_post_detail, render_robots_txt, render_rss, render_sitemap


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


def _xml_response(status_code: int, body: str, content_type: str = "application/xml") -> AppResponse:
    return AppResponse(
        status_code=status_code,
        headers={"content-type": f"{content_type}; charset=utf-8"},
        body=body,
    )


def _text_response(status_code: int, body: str) -> AppResponse:
    return AppResponse(
        status_code=status_code,
        headers={"content-type": "text/plain; charset=utf-8"},
        body=body,
    )


def _base_url(parsed_url) -> str:
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def _header_value(headers: dict[str, str] | None, name: str) -> str:
    if not headers:
        return ""
    return str(headers.get(name) or headers.get(name.lower()) or "")


def _request_id(headers: dict[str, str] | None) -> str:
    return _header_value(headers, "X-Request-ID") or str(uuid.uuid4())


def _cache_control(method: str, path: str, status_code: int) -> str:
    if method != "GET" or status_code >= 400:
        return "no-store"
    if path == "/robots.txt":
        return "public, max-age=3600"
    if path in {"/", "/read", "/sitemap.xml", "/rss.xml"} or path.startswith("/posts/") or path.startswith("/api/v1/posts"):
        return "public, max-age=60, s-maxage=300"
    return "no-store"


def _decorate_response(response: AppResponse, method: str, path: str, request_id: str) -> AppResponse:
    response.headers.setdefault("x-request-id", request_id)
    response.headers.setdefault("cache-control", _cache_control(method, path, response.status_code))
    return response


def _query_value(query: dict[str, list[str]], name: str, default: str) -> str:
    values = query.get(name)
    if not values:
        return default
    return values[0]


def _optional_query_value(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    if not values:
        return None
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
    base_url = _base_url(parsed_url)

    request_method = method.upper()
    req_id = _request_id(headers)

    def finish(response: AppResponse) -> AppResponse:
        return _decorate_response(response, request_method, path, req_id)

    if request_method == "GET" and path == "/":
        return finish(_html_response(200, render_landing_page()))
    if request_method == "GET" and path == "/robots.txt":
        return finish(_text_response(200, render_robots_txt(base_url)))

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
            return finish(_json_response(status_code, payload))

        if request_method != "GET":
            return finish(_json_response(405, {"error": "Method Not Allowed"}))

        if path == "/api/v1/health":
            return finish(_json_response(200, {"status": "ok"}))

        if path == "/read":
            explicit_date = _optional_query_value(query, "date")
            page_date = explicit_date or repo.latest_published_date() or date_value
            trending_items = repo.list_trending_by_date(date_value=page_date, limit=10)
            latest_items = repo.list_posts_by_date(date_value=page_date, limit=20, offset=0)
            page_html = render_homepage(trending=trending_items, latest=latest_items, date_value=page_date, base_url=base_url)
            return finish(_html_response(200, page_html))

        if path == "/sitemap.xml":
            return finish(_xml_response(200, render_sitemap(repo.list_recent_posts(limit=1000), base_url)))

        if path == "/rss.xml":
            return finish(_xml_response(200, render_rss(repo.list_recent_posts(limit=50), base_url), content_type="application/rss+xml"))

        if path == "/api/v1/posts":
            items = repo.list_posts_by_date(date_value=date_value, limit=limit, offset=offset)
            return finish(_json_response(200, {"items": items}))

        if path == "/api/v1/posts/trending":
            items = repo.list_trending_by_date(date_value=date_value, limit=limit)
            return finish(_json_response(200, {"items": items}))

        if path.startswith("/api/v1/posts/"):
            slug = path.replace("/api/v1/posts/", "", 1)
            post = repo.get_post_by_slug(slug)
            if post is None:
                return finish(_json_response(404, {"error": "Post Not Found"}))
            return finish(_json_response(200, {"item": post}))

        if path.startswith("/posts/"):
            slug = path.replace("/posts/", "", 1)
            post = repo.get_post_by_slug(slug)
            if post is None:
                return finish(_html_response(404, "<h1>Post Not Found</h1>"))
            return finish(_html_response(200, render_post_detail(post, base_url=base_url)))

        return finish(_json_response(404, {"error": "Not Found"}))
    finally:
        conn.close()
