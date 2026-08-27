# Site templates

Jinja2 templates and static assets used by [build.py](build.py) to
generate the static site published at
[7shi.github.io/bou-thakuranir_haat](https://7shi.github.io/bou-thakuranir_haat/).

file|description
----|----
[chapter.html](chapter.html) | per-chapter page with a 5-language tab switcher (original, modern Bengali, Hindi, English, Japanese)
[qa.html](qa.html) | QA list page (English/Japanese, with links to referenced chapters)
[doc.html](doc.html) | page for a converted `docs/*.md` file
[summary.html](summary.html) | per-chapter summaries for one language on a single page
[index.html](index.html) | landing page (chapter list + links to QA and docs)
[_sidebar.html](_sidebar.html) | shared sidebar/navigation include
[static/](static/) | CSS/JS/assets copied as-is into `dist/`

## Build and Deploy

The [online reader](https://7shi.github.io/bou-thakuranir_haat/) is a static site generated from these templates and published to GitHub Pages.

### Local build

```bash
# Generate chapter pages, QA pages, index.html, and assets into dist/
make build

# Serve dist/ locally for a preview (localhost:8000)
make serve

# Remove build artifacts
make clean
```

### Deploying to GitHub Pages

```bash
# Build, then push dist/ to the gh-pages branch
make deploy
```

`deploy.sh` checks out the `gh-pages` branch into `.gh-pages-worktree/` via `git worktree`, replaces its contents with `dist/`, and commits and pushes. It is a no-op when there is nothing to deploy.

### First-time setup

The `gh-pages` branch is created automatically on the first `make deploy`.

In the GitHub UI:

1. Open **Settings → Pages** on the repository
2. Set **Source** to `Deploy from a branch`
3. Set **Branch** to `gh-pages` / `/ (root)` and **Save**
