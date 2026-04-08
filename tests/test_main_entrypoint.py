import asyncio
import json
from dataclasses import dataclass

from src.main import Default


def _seed_posts() -> list[dict]:
    return [
        {
            "id": "p-1",
            "external_id": "ext-1",
            "slug": "ai-roundup",
            "title": "AI Roundup",
            "excerpt": "Daily AI roundup",
            "content_markdown": "# AI Roundup",
            "cover_image_url": None,
            "topic": "AI",
            "weight": 70,
            "published_date": "2026-04-08",
            "published_at": "2026-04-08T04:00:00Z",
            "is_published": 1,
            "created_at": "2026-04-08T04:00:00Z",
            "updated_at": "2026-04-08T04:00:00Z",
        },
        {
            "id": "p-2",
            "external_id": "ext-2",
            "slug": "cloud-news",
            "title": "Cloud News",
            "excerpt": "Cloud update",
            "content_markdown": "# Cloud News",
            "cover_image_url": None,
            "topic": "Cloud",
            "weight": 95,
            "published_date": "2026-04-08",
            "published_at": "2026-04-08T05:00:00Z",
            "is_published": 1,
            "created_at": "2026-04-08T05:00:00Z",
            "updated_at": "2026-04-08T05:00:00Z",
        },
    ]


class FakeStmt:
    def __init__(self, db: "FakeDB", sql: str) -> None:
        self.db = db
        self.sql = sql
        self._bindings: tuple = ()

    def bind(self, *bindings):
        self._bindings = bindings
        return self

    async def run(self):
        return self.db.run(self.sql, self._bindings)


class FakeDB:
    def __init__(self, posts: list[dict]) -> None:
        self.posts = posts

    def prepare(self, sql: str) -> FakeStmt:
        return FakeStmt(self, sql)

    def run(self, sql: str, bindings: tuple) -> dict:
        if "slug = ?" in sql:
            slug = bindings[0]
            matches = [p for p in self.posts if p["slug"] == slug and p["is_published"] == 1]
            return {"results": matches[:1]}

        if "ORDER BY weight DESC" in sql:
            date_value, limit = bindings
            rows = [p for p in self.posts if p["published_date"] == date_value and p["is_published"] == 1]
            rows.sort(key=lambda p: (p["weight"], p["published_at"], p["created_at"]), reverse=True)
            return {"results": rows[:limit]}

        if "ORDER BY published_at DESC" in sql:
            date_value, limit, offset = bindings
            rows = [p for p in self.posts if p["published_date"] == date_value and p["is_published"] == 1]
            rows.sort(key=lambda p: (p["published_at"], p["created_at"]), reverse=True)
            return {"results": rows[offset : offset + limit]}

        return {"results": []}


@dataclass
class FakeEnv:
    DB: FakeDB


@dataclass
class FakeRequest:
    url: str
    method: str = "GET"


def test_health_endpoint_returns_ok_json() -> None:
    worker = Default(env=FakeEnv(DB=FakeDB(posts=[])))
    response = asyncio.run(worker.fetch(FakeRequest(url="https://example.com/api/v1/health")))

    assert response.status == 200
    assert json.loads(response.body) == {"status": "ok"}


def test_posts_endpoint_and_homepage_render_with_entrypoint() -> None:
    worker = Default(env=FakeEnv(DB=FakeDB(posts=_seed_posts())))

    posts_response = asyncio.run(
        worker.fetch(FakeRequest(url="https://example.com/api/v1/posts?date=2026-04-08&limit=20&offset=0"))
    )
    home_response = asyncio.run(worker.fetch(FakeRequest(url="https://example.com/?date=2026-04-08")))

    posts_payload = json.loads(posts_response.body)
    assert posts_response.status == 200
    assert len(posts_payload["items"]) == 2
    assert posts_payload["items"][0]["slug"] == "cloud-news"

    assert home_response.status == 200
    assert "Trending Today" in home_response.body
    assert "Latest Today" in home_response.body
