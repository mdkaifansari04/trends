from pathlib import Path
from string import Template


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
FALLBACK_TEMPLATES = {
    "base.html": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>$title — Trends</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>* { font-family: "EB Garamond", serif; } ::selection { background: #D02020; color: #fff; }</style>
  </head>
  <body class="min-h-screen bg-white text-stone-900 antialiased">
    <nav class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-stone-100">
      <div class="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <a href="/" class="flex items-center gap-2">
          <img src="/images/logo.png" alt="Trends" class="w-6 h-6 rounded-md" />
          <span class="font-semibold text-base tracking-tight">Trends</span>
        </a>
        <a href="/" class="text-xs font-semibold tracking-widest uppercase text-stone-500 hover:text-[#D02020] transition-colors">Home</a>
      </div>
    </nav>
    <main class="mx-auto max-w-3xl px-6 py-10">$content</main>
    <footer class="border-t border-stone-100 py-8">
      <div class="max-w-5xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="flex items-center gap-2">
          <img src="/images/logo.png" alt="Trends" class="w-5 h-5 rounded-md" />
          <span class="text-sm font-semibold tracking-tight text-stone-400">Trends</span>
        </div>
        <p class="text-xs text-stone-300">&copy; 2026 Trends. All rights reserved.</p>
      </div>
    </footer>
  </body>
</html>
""",
    "home.html": """<header class="mb-10">
  <div class="flex items-center gap-3 mb-1">
    <h1 class="text-4xl font-semibold tracking-tight">Trends</h1>
    <span class="text-xs font-bold tracking-widest uppercase bg-[#D02020] text-white px-2 py-0.5 rounded-full">Live</span>
  </div>
  <p class="text-sm text-stone-400">$date_value</p>
</header>

<section class="mb-12">
  <div class="flex items-center gap-2 mb-5">
    <div class="w-1.5 h-1.5 bg-[#D02020] rounded-full"></div>
    <h2 class="text-xs font-bold tracking-widest uppercase text-stone-400">Trending Today</h2>
  </div>
  <div class="space-y-4">$trending_cards</div>
</section>

<section>
  <div class="flex items-center gap-2 mb-5">
    <div class="w-1.5 h-1.5 bg-stone-300 rounded-full"></div>
    <h2 class="text-xs font-bold tracking-widest uppercase text-stone-400">Latest Today</h2>
  </div>
  <div class="space-y-4">$latest_cards</div>
</section>
""",
    "post_detail.html": """<a href="/" class="inline-flex items-center gap-1 text-sm text-[#D02020] hover:text-stone-900 transition-colors mb-6">
  &larr; Back to feed
</a>
<article>
  <header class="mb-8 pb-6 border-b border-stone-100">
    <p class="text-xs font-bold tracking-widest uppercase text-[#D02020] mb-3">$topic</p>
    <h1 class="text-3xl md:text-4xl font-semibold tracking-tight leading-tight mb-3">$title</h1>
    <p class="text-sm text-stone-400">$published_date</p>
  </header>
  <p class="text-lg text-stone-600 font-light leading-relaxed mb-8">$excerpt</p>
  <div class="prose prose-stone max-w-none">
    <pre class="whitespace-pre-wrap rounded-xl bg-stone-50 border border-stone-100 p-6 text-sm text-stone-700 leading-relaxed">$content_markdown</pre>
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
<article class="rounded-xl border border-stone-100 bg-white p-5 hover:border-[#D02020]/30 transition-colors">
  <a href="/posts/{slug}" class="text-lg font-semibold text-stone-900 hover:text-[#D02020] transition-colors">{title}</a>
  <p class="mt-2 text-sm text-stone-500 font-light leading-relaxed">{excerpt}</p>
  <div class="mt-3 flex items-center gap-3">
    <span class="text-xs font-bold tracking-widest uppercase text-[#D02020]">{topic}</span>
    <span class="text-xs text-stone-300">·</span>
    <span class="text-xs text-stone-400">Weight: {weight}</span>
  </div>
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
