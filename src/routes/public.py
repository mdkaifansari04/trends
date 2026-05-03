from pathlib import Path
from html import escape
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
    $head_extra
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="/js/bookmarks.js" defer></script>
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
    Trending Today
  </p>
  <div class="space-y-2">$trending_cards</div>
</section>

<section>
  <p class="text-[10px] font-bold tracking-widest uppercase text-stone-400 mb-3 flex items-center gap-1.5">
    <span class="w-1.5 h-1.5 bg-stone-300 rounded-full inline-block"></span>
    Latest Today
  </p>
  <div class="space-y-2">$latest_cards</div>
</section>
""",
    "post_detail.html": """<div class="mb-4">
  <a href="/read" class="inline-flex items-center gap-1 text-xs font-semibold tracking-wide text-stone-400 hover:text-[#D02020] transition-colors">&larr; Back</a>
</div>
<article class="bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden">
  <div class="px-5 pt-5 pb-4 border-b border-stone-100">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <span class="text-[10px] font-bold tracking-widest uppercase text-[#D02020]">$topic</span>
        <h1 class="text-xl font-semibold tracking-tight leading-snug mt-1.5">$title</h1>
        <p class="text-xs text-stone-400 mt-1.5">$published_date</p>
      </div>
      <button type="button" class="shrink-0 rounded-md border border-stone-200 px-2.5 py-1 text-[11px] font-semibold text-stone-500 hover:border-[#D02020]/50 hover:text-[#D02020] transition-colors" data-bookmark-slug="$slug" data-bookmark-title="$bookmark_title" aria-pressed="false">
        <span data-bookmark-label>Save bookmark</span>
      </button>
    </div>
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


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _xml(value: object) -> str:
    return escape(str(value), quote=False)


def _post_url(base_url: str, post: dict) -> str:
    return f"{base_url.rstrip('/')}/posts/{post['slug']}"


def _seo_head(title: str, description: str, url: str, page_type: str = "website", image_url: str | None = None) -> str:
    image_markup = ""
    if image_url:
        escaped_image_url = _html(image_url)
        image_markup = (
            f'\n    <meta property="og:image" content="{escaped_image_url}" />'
            f'\n    <meta name="twitter:image" content="{escaped_image_url}" />'
        )

    return (
        f'<link rel="canonical" href="{_html(url)}" />\n'
        f'    <meta property="og:title" content="{_html(title)}" />\n'
        f'    <meta property="og:description" content="{_html(description)}" />\n'
        f'    <meta property="og:type" content="{_html(page_type)}" />\n'
        f'    <meta property="og:url" content="{_html(url)}" />\n'
        f'    <meta name="twitter:card" content="summary_large_image" />\n'
        f'    <meta name="twitter:title" content="{_html(title)}" />\n'
        f'    <meta name="twitter:description" content="{_html(description)}" />'
        f"{image_markup}"
    )


def render_landing_page() -> str:
    return _read_template_text("landing.html")


def _render_post_cards(posts: list[dict]) -> str:
    if not posts:
        return '<p class="text-sm text-stone-400">No posts available.</p>'

    card_markup: list[str] = []
    for post in posts:
        slug = _html(post["slug"])
        title = _html(post["title"])
        excerpt = _html(post.get("excerpt") or "No excerpt available.")
        topic = _html(post.get("topic") or "General")
        weight = _html(post["weight"])
        card_markup.append(
            """
<article class="bg-white rounded-lg border border-stone-200 p-4 hover:border-[#D02020]/40 hover:shadow-sm transition-all">
  <div class="flex items-start justify-between gap-3">
    <a href="/posts/{slug}" class="block min-w-0 flex-1">
      <p class="text-sm font-semibold text-stone-900 leading-snug">{title}</p>
      <p class="text-xs text-stone-400 mt-1 line-clamp-2">{excerpt}</p>
    </a>
    <button type="button" class="shrink-0 rounded-md border border-stone-200 px-2.5 py-1 text-[11px] font-semibold text-stone-500 hover:border-[#D02020]/50 hover:text-[#D02020] transition-colors" data-bookmark-slug="{slug}" data-bookmark-title="{title}" aria-pressed="false">
      <span data-bookmark-label>Save bookmark</span>
    </button>
  </div>
  <div class="mt-2.5 flex items-center gap-2">
    <span class="text-[10px] font-bold tracking-widest uppercase text-[#D02020]">{topic}</span>
    <span class="text-[10px] text-stone-300">\u00b7</span>
    <span class="text-[10px] text-stone-400">score {weight}</span>
  </div>
</article>
            """.strip().format(
                slug=slug,
                title=title,
                excerpt=excerpt,
                topic=topic,
                weight=weight,
            )
        )
    return "\n".join(card_markup)


def render_homepage(trending: list[dict], latest: list[dict], date_value: str, base_url: str = "") -> str:
    home_tpl = _read_template("home.html")
    base_tpl = _read_template("base.html")
    head_extra = ""
    if base_url:
        head_extra = _seo_head(
            title="Trends",
            description="Tech news for builders.",
            url=f"{base_url.rstrip('/')}/read",
        )

    content = home_tpl.safe_substitute(
        date_value=_html(date_value),
        trending_cards=_render_post_cards(trending),
        latest_cards=_render_post_cards(latest),
    )
    return base_tpl.safe_substitute(title="Trends", head_extra=head_extra, content=content)


def render_post_detail(post: dict, base_url: str = "") -> str:
    detail_tpl = _read_template("post_detail.html")
    base_tpl = _read_template("base.html")
    url = _post_url(base_url, post) if base_url else f"/posts/{post['slug']}"
    description = post.get("excerpt") or "Read this story on Trends."
    head_extra = _seo_head(
        title=str(post["title"]),
        description=str(description),
        url=url,
        page_type="article",
        image_url=post.get("cover_image_url"),
    )

    content = detail_tpl.safe_substitute(
        slug=_html(post["slug"]),
        bookmark_title=_html(post["title"]),
        title=_html(post["title"]),
        topic=_html(post.get("topic") or "General"),
        published_date=_html(post["published_date"]),
        content_markdown=_html(post["content_markdown"]),
        excerpt=_html(post.get("excerpt") or "No excerpt available."),
    )
    return base_tpl.safe_substitute(title=_html(post["title"]), head_extra=head_extra, content=content)


def render_sitemap(posts: list[dict], base_url: str) -> str:
    root = base_url.rstrip("/")
    urls = [f"  <url><loc>{_xml(root)}/read</loc></url>"]
    for post in posts:
        urls.append(f"  <url><loc>{_xml(_post_url(root, post))}</loc></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"


def render_rss(posts: list[dict], base_url: str) -> str:
    root = base_url.rstrip("/")
    items: list[str] = []
    for post in posts:
        url = _post_url(root, post)
        description = post.get("excerpt") or "Read this story on Trends."
        pub_date = post.get("published_at") or post.get("published_date") or ""
        items.append(
            "    <item>\n"
            f"      <title>{_xml(post['title'])}</title>\n"
            f"      <link>{_xml(url)}</link>\n"
            f"      <guid>{_xml(url)}</guid>\n"
            f"      <description>{_xml(description)}</description>\n"
            f"      <pubDate>{_xml(pub_date)}</pubDate>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>Trends</title>\n"
        f"    <link>{_xml(root)}/read</link>\n"
        "    <description>Tech news for builders.</description>\n"
        f"{chr(10).join(items)}\n"
        "  </channel>\n"
        "</rss>\n"
    )


def render_robots_txt(base_url: str) -> str:
    root = base_url.rstrip("/")
    return f"User-agent: *\nAllow: /\nSitemap: {root}/sitemap.xml\n"
