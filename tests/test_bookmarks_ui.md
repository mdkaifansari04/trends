# Bookmarks UI Manual Checklist

Automated coverage verifies that `/read` and `/posts/:slug` render bookmark controls
and load `/js/bookmarks.js`.

Manual browser pass:

- Open `/read`, click "Save bookmark" on a post, and verify the label changes to
  "Saved".
- Reload `/read` and verify the saved state persists.
- Open the same post detail page and verify the saved state is reflected there.
- Click "Saved" on the detail page, reload, and verify it returns to "Save bookmark".
- Confirm bookmarks are stored only in browser `localStorage` under
  `trends-bookmarks`.

Latest automated run: `uv run --extra dev pytest -v` passed locally.
