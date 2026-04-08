from pathlib import Path
from string import Template


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
FALLBACK_TEMPLATES = {
    "base.html": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#D02020" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <title>$title — Trends</title>
    <link rel="apple-touch-icon" sizes="180x180" href="/logo/apple-touch-icon.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="/logo/favicon-32x32.png" />
    <link rel="icon" type="image/png" sizes="16x16" href="/logo/favicon-16x16.png" />
    <link rel="icon" type="image/x-icon" href="/logo/favicon.ico" />
    <link rel="manifest" href="/logo/site.webmanifest" />
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>* { font-family: "EB Garamond", serif; } ::selection { background: #D02020; color: #fff; } body { overscroll-behavior-y: none; }</style>
  </head>
  <body class="min-h-screen bg-stone-50 text-stone-900 antialiased">
    <nav class="sticky top-0 z-50 bg-white border-b border-stone-200 shadow-sm">
      <div class="max-w-2xl mx-auto px-4 h-12 flex items-center justify-between">
        <a href="/read" class="flex items-center gap-2">
          <img src="/images/logo.png" alt="Trends" class="w-5 h-5 rounded" />
          <span class="font-semibold text-sm tracking-tight">Trends</span>
        </a>
        <a href="/read" class="text-xs font-semibold tracking-wide text-stone-400 hover:text-[#D02020] transition-colors">Feed</a>
      </div>
    </nav>
    <main class="mx-auto max-w-2xl px-4 py-6">$content</main>
  </body>
</html>
""",
    "home.html": """<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-lg font-semibold tracking-tight">Your Feed</h1>
    <p class="text-xs text-stone-400 mt-0.5">$date_value</p>
  </div>
  <span class="text-[10px] font-bold tracking-widest uppercase bg-[#D02020] text-white px-2 py-0.5 rounded-full">Live</span>
</div>

<section class="mb-8">
  <p class="text-[10px] font-bold tracking-widest uppercase text-[#D02020] mb-3 flex items-center gap-1.5">
    <span class="w-1.5 h-1.5 bg-[#D02020] rounded-full inline-block"></span>
    Trending
  </p>
  <div class="space-y-2">$trending_cards</div>
</section>

<section>
  <p class="text-[10px] font-bold tracking-widest uppercase text-stone-400 mb-3 flex items-center gap-1.5">
    <span class="w-1.5 h-1.5 bg-stone-300 rounded-full inline-block"></span>
    Latest
  </p>
  <div class="space-y-2">$latest_cards</div>
</section>
""",
    "post_detail.html": """<div class="mb-4">
  <a href="/read" class="inline-flex items-center gap-1 text-xs font-semibold tracking-wide text-stone-400 hover:text-[#D02020] transition-colors">&larr; Back</a>
</div>
<article class="bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden">
  <div class="px-5 pt-5 pb-4 border-b border-stone-100">
    <span class="text-[10px] font-bold tracking-widest uppercase text-[#D02020]">$topic</span>
    <h1 class="text-xl font-semibold tracking-tight leading-snug mt-1.5">$title</h1>
    <p class="text-xs text-stone-400 mt-1.5">$published_date</p>
  </div>
  <div class="px-5 py-4">
    <p class="text-sm text-stone-500 leading-relaxed mb-4">$excerpt</p>
    <div class="whitespace-pre-wrap rounded-lg bg-stone-50 border border-stone-100 p-4 text-sm text-stone-700 leading-relaxed">$content_markdown</div>
  </div>
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
        return '<p class="text-sm text-stone-400">No posts available.</p>'

    card_markup: list[str] = []
    for post in posts:
        card_markup.append(
            """
<a href="/posts/{slug}" class="block bg-white rounded-lg border border-stone-200 p-4 hover:border-[#D02020]/40 hover:shadow-sm transition-all">
  <div class="flex items-start justify-between gap-3">
    <div class="min-w-0 flex-1">
      <p class="text-sm font-semibold text-stone-900 leading-snug">{title}</p>
      <p class="text-xs text-stone-400 mt-1 line-clamp-2">{excerpt}</p>
    </div>
  </div>
  <div class="mt-2.5 flex items-center gap-2">
    <span class="text-[10px] font-bold tracking-widest uppercase text-[#D02020]">{topic}</span>
    <span class="text-[10px] text-stone-300">\u00b7</span>
    <span class="text-[10px] text-stone-400">score {weight}</span>
  </div>
</a>
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
