from pathlib import Path
from string import Template


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
FALLBACK_TEMPLATES = {
    "base.html": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>$title</title>
    <link rel="stylesheet" href="/static/css/output.css" />
  </head>
  <body class="min-h-screen bg-slate-50 text-slate-900">
    <main class="mx-auto max-w-5xl px-6 py-10">$content</main>
  </body>
</html>
""",
    "home.html": """<header class="mb-8">
  <h1 class="text-3xl font-bold tracking-tight">Trends</h1>
  <p class="mt-2 text-sm text-slate-600">Date: $date_value</p>
</header>

<section class="mb-8">
  <h2 class="mb-4 text-xl font-semibold">Trending Today</h2>
  <div class="space-y-3">$trending_cards</div>
</section>

<section>
  <h2 class="mb-4 text-xl font-semibold">Latest Today</h2>
  <div class="space-y-3">$latest_cards</div>
</section>
""",
    "post_detail.html": """<article class="rounded-lg border border-gray-200 bg-white p-6">
  <h1 class="text-3xl font-bold tracking-tight">$title</h1>
  <p class="mt-2 text-sm text-slate-500">$published_date | $topic</p>
  <p class="mt-5 text-slate-600">$excerpt</p>
  <pre class="mt-6 whitespace-pre-wrap rounded-md bg-slate-100 p-4 text-sm">$content_markdown</pre>
</article>
""",
    "landing.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Trends — Tech news for builders</title>
  </head>
  <body>
    <h1>Stop scrolling. Start shipping.</h1>
    <p>Tech news for builders</p>
  </body>
</html>
""",
}


def _template_roots() -> list[Path]:
    current = Path(__file__).resolve()
    return [
        TEMPLATE_DIR,
        current.parent / "templates",
        current.parent.parent / "templates",
        current.parent.parent.parent / "templates",
    ]


def _read_template_text(name: str) -> str:
    checked: set[Path] = set()
    for root in _template_roots():
        if root in checked:
            continue
        checked.add(root)
        candidate = root / name
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    fallback = FALLBACK_TEMPLATES.get(name)
    if fallback is not None:
        return fallback
    raise FileNotFoundError(f"Template '{name}' not found in roots: {', '.join(str(root) for root in checked)}")


def _read_template(name: str) -> Template:
    return Template(_read_template_text(name))


def render_landing_page() -> str:
    return _read_template_text("landing.html")


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
