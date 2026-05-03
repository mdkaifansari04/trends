(() => {
  const BOOKMARK_KEY = "trends-bookmarks";

  function readBookmarks() {
    try {
      const raw = localStorage.getItem(BOOKMARK_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function writeBookmarks(bookmarks) {
    localStorage.setItem(BOOKMARK_KEY, JSON.stringify(bookmarks));
  }

  function bookmarkSlug(bookmark) {
    return typeof bookmark === "string" ? bookmark : bookmark.slug;
  }

  function syncButtons() {
    const bookmarks = readBookmarks();
    const bookmarkedSlugs = new Set(bookmarks.map(bookmarkSlug));

    document.querySelectorAll("[data-bookmark-slug]").forEach((button) => {
      const slug = button.getAttribute("data-bookmark-slug");
      const isBookmarked = bookmarkedSlugs.has(slug);
      const label = button.querySelector("[data-bookmark-label]");

      button.setAttribute("aria-pressed", isBookmarked ? "true" : "false");
      button.style.borderColor = isBookmarked ? "#D02020" : "";
      button.style.color = isBookmarked ? "#D02020" : "";
      if (label) {
        label.textContent = isBookmarked ? "Saved" : "Save bookmark";
      }
    });
  }

  function toggleBookmark(button) {
    const slug = button.getAttribute("data-bookmark-slug");
    if (!slug) {
      return;
    }

    const title = button.getAttribute("data-bookmark-title") || slug;
    const bookmarks = readBookmarks();
    const existingIndex = bookmarks.findIndex((bookmark) => bookmarkSlug(bookmark) === slug);

    if (existingIndex >= 0) {
      bookmarks.splice(existingIndex, 1);
    } else {
      bookmarks.push({ slug, title, savedAt: new Date().toISOString() });
    }

    writeBookmarks(bookmarks);
    syncButtons();
  }

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target ? target.closest("[data-bookmark-slug]") : null;
    if (!button) {
      return;
    }
    toggleBookmark(button);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncButtons);
  } else {
    syncButtons();
  }
})();
