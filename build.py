"""Static site builder for bou-thakuranir_haat.

Reads all/{bn,bn-gemini,hi-gemini,en-gemini,ja-gemini}.md, questions-{en,ja}.jsonl, docs/*.md
and generates:
- dist/chapter-{NN}.html  per-chapter page with a 5-language tab switcher
                          (original, modern Bengali, Hindi, English, Japanese)
- dist/qa-en.html         English QA list (with links to referenced chapters)
- dist/qa-ja.html         Japanese QA list (with links to referenced chapters)
- dist/docs/{stem}.html   pages converted from docs/*.md
- dist/summary-{lang}.html  per-chapter summaries for one language on a single page
- dist/index.html         landing page (chapter list + links to QA and docs)
"""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = TEMPLATES_DIR / "static"
DIST_DIR = ROOT / "dist"

NUM_CHAPTERS = 37

TEXTS: dict[str, dict] = {
    "bn": {"file": "all/bn.md", "label": "Classical Bengali", "lang": "bn"},
    "bn-gemini": {"file": "all/bn-gemini.md", "label": "Bengali", "lang": "bn"},
    "hi-gemini": {"file": "all/hi-gemini.md", "label": "Hindi", "lang": "hi"},
    "en-gemini": {"file": "all/en-gemini.md", "label": "English", "lang": "en"},
    "ja-gemini": {"file": "all/ja-gemini.md", "label": "Japanese", "lang": "ja"},
}

SUMMARIES: dict[str, dict] = {
    "bn-gemini": {"file": "all/bn-gemini-summary.md", "label": "Bengali", "lang": "bn"},
    "hi-gemini": {"file": "all/hi-gemini-summary.md", "label": "Hindi", "lang": "hi"},
    "en-gemini": {"file": "all/en-gemini-summary.md", "label": "English", "lang": "en"},
    "ja-gemini": {"file": "all/ja-gemini-summary.md", "label": "Japanese", "lang": "ja"},
}

TITLES: dict[str, dict] = {
    "en": {"file": "all/en-gemini.tsv"},
    "ja": {"file": "all/ja-gemini.tsv"},
}

DOCS: list[dict] = [
    {
        "id": "bhasha",
        "label": "Bengali Language Analysis",
        "en": "bhasha-en",
        "ja": "bhasha-ja",
    },
    {
        "id": "shadhu",
        "label": "Close Reading: Shadhu vs. Modern Bengali (Ch.1)",
        "en": "shadhu-en",
        "ja": "shadhu-ja",
    },
    {
        "id": "flow",
        "label": "Story Flow Diagram",
        "en": "flow-en",
        "ja": "flow-ja",
    },
]


@dataclass
class Chapter:
    number: int
    texts: dict[str, str] = field(default_factory=dict)  # key -> HTML paragraphs
    titles: list[tuple[str, str]] = field(default_factory=list)  # (title_en, title_ja)


def split_chapters(filepath: Path) -> list[str]:
    """Split the body at each `## ...` heading (only the order is used, not the heading text)."""
    text = filepath.read_text(encoding="utf-8")
    parts = re.split(r"^## .*$", text, flags=re.MULTILINE)
    # parts[0] is the leading `# Title` section; the rest are the chapter bodies.
    bodies = [p.strip("\n") for p in parts[1:]]
    return bodies


def paragraphs_to_html(body: str) -> str:
    """Convert blank-line-separated paragraphs to `<p>` tags. `*text*` becomes `<em>`."""
    out = []
    for para in re.split(r"\n\s*\n", body.strip()):
        para = para.strip()
        if not para:
            continue
        escaped = html.escape(para)
        escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
        escaped = escaped.replace("\n", "<br>\n")
        out.append(f"<p>{escaped}</p>")
    return "\n".join(out)


def load_titles(lang: str) -> dict[int, list[str]]:
    """Return a dict mapping chapter -> [segment title, ...]."""
    path = ROOT / TITLES[lang]["file"]
    result: dict[int, list[str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        chapter_s, _segment_s, title = line.split("\t", 2)
        chapter = int(chapter_s)
        result.setdefault(chapter, []).append(title)
    return result


def load_chapters() -> list[Chapter]:
    chapters = [Chapter(number=i) for i in range(1, NUM_CHAPTERS + 1)]

    for key, cfg in TEXTS.items():
        bodies = split_chapters(ROOT / cfg["file"])
        if len(bodies) != NUM_CHAPTERS:
            raise ValueError(f"{cfg['file']}: expected {NUM_CHAPTERS} chapters, got {len(bodies)}")
        for chapter, body in zip(chapters, bodies):
            chapter.texts[key] = paragraphs_to_html(body)

    titles_en = load_titles("en")
    titles_ja = load_titles("ja")
    for chapter in chapters:
        chapter.titles = list(zip(
            titles_en.get(chapter.number, []),
            titles_ja.get(chapter.number, []),
        ))

    return chapters


def load_summaries() -> list[dict]:
    """Return a list of {number, texts: {key: html}} for each chapter's summary."""
    summaries = [{"number": i, "texts": {}} for i in range(1, NUM_CHAPTERS + 1)]

    for key, cfg in SUMMARIES.items():
        bodies = split_chapters(ROOT / cfg["file"])
        if len(bodies) != NUM_CHAPTERS:
            raise ValueError(f"{cfg['file']}: expected {NUM_CHAPTERS} chapters, got {len(bodies)}")
        for summary, body in zip(summaries, bodies):
            summary["texts"][key] = paragraphs_to_html(body)

    return summaries


def load_questions(lang: str) -> list[dict]:
    path = ROOT / f"questions-{lang}.jsonl"
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            questions.append(json.loads(line))
    return questions


def chapter_href(number: int) -> str:
    return f"chapter-{number:02d}.html"


def build_chapter_rows(chapters: list[Chapter]) -> list[dict]:
    """Build the (number, href, title_summary) list for the sidebar's chapter grid."""
    return [
        {
            "number": chapter.number,
            "href": chapter_href(chapter.number),
            "title_summary": " / ".join(title_en for title_en, _ in chapter.titles),
        }
        for chapter in chapters
    ]


def build_doc_rows() -> list[dict]:
    """Build the (label, en_href, ja_href) list for the sidebar's Docs list."""
    return [
        {
            "label": group["label"],
            "en_href": f"docs/{group['en']}.html",
            "ja_href": f"docs/{group['ja']}.html",
        }
        for group in DOCS
    ]


def convert_doc(md_text: str) -> tuple[str, str, bool]:
    """Convert a docs/*.md file to HTML. Returns (title, html, has_mermaid)."""
    title_match = re.search(r"^#\s+(.+)$", md_text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    if title_match:
        # Strip the leading heading line since it would duplicate the page's <h1>.
        md_text = md_text[:title_match.start()] + md_text[title_match.end():]

    converter = markdown.Markdown(extensions=["tables", "fenced_code"])
    body_html = converter.convert(md_text)

    has_mermaid = 'class="language-mermaid"' in body_html
    body_html = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\1</pre>',
        body_html,
        flags=re.S,
    )
    # Rewrite links to other docs/*.md files in the same directory to .html.
    body_html = re.sub(r'href="([^"/]+)\.md"', r'href="\1.html"', body_html)

    return title, body_html, has_mermaid


def build_docs(env: Environment, sidebar_chapters: list[dict], sidebar_docs: list[dict]) -> None:
    docs_dir = DIST_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)
    template = env.get_template("doc.html")

    for group in DOCS:
        for lang in ("en", "ja"):
            stem = group[lang]
            other_lang = "ja" if lang == "en" else "en"
            md_text = (ROOT / "docs" / f"{stem}.md").read_text(encoding="utf-8")
            title, body_html, has_mermaid = convert_doc(md_text)
            html_out = template.render(
                lang=lang,
                title=title,
                body_html=body_html,
                has_mermaid=has_mermaid,
                other_href=f"{group[other_lang]}.html",
                other_lang=other_lang,
                base="../",
                sidebar_chapters=sidebar_chapters,
                sidebar_docs=sidebar_docs,
            )
            (docs_dir / f"{stem}.html").write_text(html_out, encoding="utf-8")
    print(f"  wrote {len(DOCS) * 2} doc pages")


def build_chapters(
    env: Environment,
    chapters: list[Chapter],
    sidebar_chapters: list[dict],
    sidebar_docs: list[dict],
) -> None:
    template = env.get_template("chapter.html")
    text_tabs = [{"key": key, "label": cfg["label"], "lang": cfg["lang"]} for key, cfg in TEXTS.items()]
    for chapter in chapters:
        prev_href = chapter_href(chapter.number - 1) if chapter.number > 1 else None
        next_href = chapter_href(chapter.number + 1) if chapter.number < NUM_CHAPTERS else None
        html_out = template.render(
            chapter=chapter,
            text_tabs=text_tabs,
            prev_href=prev_href,
            next_href=next_href,
            base="",
            sidebar_chapters=sidebar_chapters,
            sidebar_docs=sidebar_docs,
            current_chapter=chapter.number,
        )
        out = DIST_DIR / chapter_href(chapter.number)
        out.write_text(html_out, encoding="utf-8")
    print(f"  wrote {NUM_CHAPTERS} chapter pages")


def build_qa(
    env: Environment,
    lang: str,
    sidebar_chapters: list[dict],
    sidebar_docs: list[dict],
) -> None:
    questions = load_questions(lang)
    other_lang = "ja" if lang == "en" else "en"
    for q in questions:
        q["chapter_links"] = [
            {"number": n, "href": chapter_href(n)} for n in q["chapters"]
        ]
    template = env.get_template("qa.html")
    html_out = template.render(
        lang=lang,
        other_lang=other_lang,
        other_href=f"qa-{other_lang}.html",
        questions=questions,
        num_single=sum(1 for q in questions if q["type"] == "single"),
        num_cross=sum(1 for q in questions if q["type"] == "cross"),
        base="",
        sidebar_chapters=sidebar_chapters,
        sidebar_docs=sidebar_docs,
    )
    out = DIST_DIR / f"qa-{lang}.html"
    out.write_text(html_out, encoding="utf-8")
    print(f"  wrote {out.relative_to(ROOT)} ({len(questions)} questions)")


def build_summary(env: Environment, sidebar_chapters: list[dict], sidebar_docs: list[dict]) -> None:
    summaries = load_summaries()
    template = env.get_template("summary.html")
    for key, cfg in SUMMARIES.items():
        chapters = [
            {"number": s["number"], "href": chapter_href(s["number"]), "text": s["texts"][key]}
            for s in summaries
        ]
        html_out = template.render(
            label=cfg["label"],
            lang=cfg["lang"],
            chapters=chapters,
            base="",
            sidebar_chapters=sidebar_chapters,
            sidebar_docs=sidebar_docs,
        )
        out = DIST_DIR / f"summary-{cfg['lang']}.html"
        out.write_text(html_out, encoding="utf-8")
    print(f"  wrote {len(SUMMARIES)} summary pages")


def build_index(env: Environment, sidebar_chapters: list[dict], sidebar_docs: list[dict]) -> None:
    template = env.get_template("index.html")
    html_out = template.render(
        base="",
        sidebar_chapters=sidebar_chapters,
        sidebar_docs=sidebar_docs,
    )
    out = DIST_DIR / "index.html"
    out.write_text(html_out, encoding="utf-8")
    print(f"  wrote {out.relative_to(ROOT)}")


def copy_static() -> None:
    assets = DIST_DIR / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    shutil.copytree(STATIC_DIR, assets)
    print(f"  copied static -> {assets.relative_to(ROOT)}")


def main() -> None:
    DIST_DIR.mkdir(exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )

    print("Loading chapters...")
    chapters = load_chapters()
    sidebar_chapters = build_chapter_rows(chapters)
    sidebar_docs = build_doc_rows()

    print("Building chapter pages...")
    build_chapters(env, chapters, sidebar_chapters, sidebar_docs)

    print("Building QA pages...")
    build_qa(env, "en", sidebar_chapters, sidebar_docs)
    build_qa(env, "ja", sidebar_chapters, sidebar_docs)

    print("Building doc pages...")
    build_docs(env, sidebar_chapters, sidebar_docs)

    print("Building summary page...")
    build_summary(env, sidebar_chapters, sidebar_docs)

    print("Building index...")
    build_index(env, sidebar_chapters, sidebar_docs)

    print("Copying static assets...")
    copy_static()

    print("Done.")


if __name__ == "__main__":
    main()
