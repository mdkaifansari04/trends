from pathlib import Path
from string import Template


TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


def _read_template(name: str) -> Template:
    return Template((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def _render_post_cards(posts: list[dict]) -> str:
    if not posts:
        return '<p class="text-sm text-gray-500">No posts available.</p>'

    card_markup: list[str] = []
    for post in posts:
        card_markup.append(
            """
<article class="rounded-lg border border-gray-200 bg-white p-4">
  <a href="/posts/{slug}" class="text-lg font-semibold text-slate-900 hover:underline">{title}</a>
  <p class="mt-2 text-sm text-slate-600">{excerpt}</p>
  <p class="mt-3 text-xs text-slate-500">Topic: {topic} | Weight: {weight}</p>
</article>
            """.strip().format(
                slug=post["slug"],
                title=post["title"],
                excerpt=post.get("excerpt") or "No excerpt available.",
                topic=post.get("topic") or "General",
                weight=post["weight"],
            )
        )
    return "\n".join(card_markup)


def render_homepage(trending: list[dict], latest: list[dict], date_value: str) -> str:
    home_tpl = _read_template("home.html")
    base_tpl = _read_template("base.html")

    content = home_tpl.safe_substitute(
        date_value=date_value,
        trending_cards=_render_post_cards(trending),
        latest_cards=_render_post_cards(latest),
    )
    return base_tpl.safe_substitute(title="Trends", content=content)


def render_post_detail(post: dict) -> str:
    detail_tpl = _read_template("post_detail.html")
    base_tpl = _read_template("base.html")

    content = detail_tpl.safe_substitute(
        title=post["title"],
        topic=post.get("topic") or "General",
        published_date=post["published_date"],
        content_markdown=post["content_markdown"],
        excerpt=post.get("excerpt") or "No excerpt available.",
    )
    return base_tpl.safe_substitute(title=post["title"], content=content)
