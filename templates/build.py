"""Static site builder for bou-thakuranir_haat.

Reads all/{bn,bn-gemini,hi-gemini,en-gemini,ja-gemini}.md, all/captions.jsonl,
questions-{en,ja}.jsonl, docs/*.md and, for the segment boundaries alone,
segmentations.jsonl and all/aligned/*-gemini-terra.jsonl (unpacked from the
committed deltas by `make build`), and generates:
- dist/chapter-{NN}.html  per-chapter page with a 5-language tab switcher
                          (original, modern Bengali, Hindi, English, Japanese),
                          each language's text split into its segments and
                          headed by that segment's caption in that language
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

ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = TEMPLATES_DIR / "static"
DIST_DIR = ROOT / "dist"
ALIGNED_DIR = ROOT / "all" / "aligned"
CAPTIONS_FILE = ROOT / "all" / "captions.jsonl"
SEGMENTATIONS_FILE = ROOT / "segmentations.jsonl"

NUM_CHAPTERS = 37

# `caption` is which of all/captions.jsonl's four languages heads this text's
# segments. The original is captioned in modern Bengali, there being no
# classical-Bengali caption to pair with it.
TEXTS: dict[str, dict] = {
    "bn": {"file": "all/bn.md", "label": "Classical Bengali", "lang": "bn", "caption": "bn"},
    "bn-gemini": {"file": "all/bn-gemini.md", "label": "Bengali", "lang": "bn", "caption": "bn"},
    "hi-gemini": {"file": "all/hi-gemini.md", "label": "Hindi", "lang": "hi", "caption": "hi"},
    "en-gemini": {"file": "all/en-gemini.md", "label": "English", "lang": "en", "caption": "en"},
    "ja-gemini": {"file": "all/ja-gemini.md", "label": "Japanese", "lang": "ja", "caption": "ja"},
}

SUMMARIES: dict[str, dict] = {
    "bn-gemini": {"file": "all/bn-gemini-summary.md", "label": "Bengali", "lang": "bn"},
    "hi-gemini": {"file": "all/hi-gemini-summary.md", "label": "Hindi", "lang": "hi"},
    "en-gemini": {"file": "all/en-gemini-summary.md", "label": "English", "lang": "en"},
    "ja-gemini": {"file": "all/ja-gemini-summary.md", "label": "Japanese", "lang": "ja"},
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
class Segment:
    number: int  # 1-based, within its chapter
    captions: dict[str, str] = field(default_factory=dict)  # caption language -> caption
    texts: dict[str, str] = field(default_factory=dict)  # TEXTS key -> HTML paragraphs


@dataclass
class Chapter:
    number: int
    segments: list[Segment] = field(default_factory=list)


def split_chapters(filepath: Path) -> list[str]:
    """Split the body at each `## ...` heading (only the order is used, not the heading text)."""
    text = filepath.read_text(encoding="utf-8")
    parts = re.split(r"^## .*$", text, flags=re.MULTILINE)
    # parts[0] is the leading `# Title` section; the rest are the chapter bodies.
    bodies = [p.strip("\n") for p in parts[1:]]
    return bodies


def split_paragraphs(body: str) -> list[str]:
    """Split a chapter body into its blank-line-separated paragraphs."""
    return [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]


def paragraphs_to_html(paragraphs: list[str] | str) -> str:
    """Convert paragraphs to `<p>` tags. `*text*` becomes `<em>`."""
    if isinstance(paragraphs, str):
        paragraphs = split_paragraphs(paragraphs)
    out = []
    for para in paragraphs:
        escaped = html.escape(para)
        escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
        escaped = escaped.replace("\n", "<br>\n")
        out.append(f"<p>{escaped}</p>")
    return "\n".join(out)


def load_captions() -> dict[int, list[dict[str, str]]]:
    """Return chapter -> [{caption language: caption}, ...], one entry per segment."""
    if not CAPTIONS_FILE.exists():
        raise SystemExit(
            f"Missing {CAPTIONS_FILE.relative_to(ROOT)}. Run 'make captions' to generate it."
        )
    records: dict[int, list[tuple[int, dict[str, str]]]] = {}
    for line in CAPTIONS_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            records.setdefault(entry["chapter"], []).append((entry["segment"], entry["captions"]))
    return {
        chapter: [captions for _, captions in sorted(entries)]
        for chapter, entries in records.items()
    }


def load_translation_segment_sizes(key: str) -> dict[int, list[int]]:
    """Return chapter -> [paragraph count per segment, ...] for one translation.

    The `all/*-gemini.md` files concatenate their segments without marking the
    boundaries, so the sizes come from the aligned JSONL the Markdown was built
    from: one paragraph per aligned line, in segment order.
    """
    lang = key.split("-")[0]
    path = ALIGNED_DIR / f"{lang}-gemini-terra.jsonl"
    if not path.exists():
        raise SystemExit(
            f"Missing {path.relative_to(ROOT)}. "
            f"Run 'make -C all/aligned unpack' to regenerate it from the committed delta."
        )
    sizes: dict[int, list[tuple[int, int]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            lines = [x for x in entry["response"]["translation"].split("\n") if x.strip()]
            sizes.setdefault(entry["chapter"], []).append((entry["segment"], len(lines)))
    return {chapter: [n for _, n in sorted(entries)] for chapter, entries in sizes.items()}


def load_original_segment_sizes() -> dict[int, list[int]]:
    """Return chapter -> [paragraph count per segment, ...] for all/bn.md.

    The original is segmented by line range rather than by translation record,
    so the sizes come from `segmentations.jsonl`. A chapter with no entry there
    was never split, and is left for the caller to treat as one segment.
    """
    lines = (ROOT / "all" / "bn.md").read_text(encoding="utf-8").splitlines()
    sizes: dict[int, list[int]] = {}
    for line in SEGMENTATIONS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        sizes[entry["chapter"]] = [
            sum(
                1
                for i in range(b["start_line"] - 1, min(b["end_line"], len(lines)))
                if lines[i].strip() and not lines[i].startswith("##")
            )
            for b in entry["boundaries"]
        ]
    return sizes


def split_into_segments(
    filename: str, chapter: int, paragraphs: list[str], sizes: list[int]
) -> list[str]:
    """Group a chapter's paragraphs into its segments, as HTML."""
    if sum(sizes) != len(paragraphs):
        raise SystemExit(
            f"{filename}: chapter {chapter} has {len(paragraphs)} paragraphs, "
            f"but its segments account for {sum(sizes)} ({sizes})."
        )
    out = []
    start = 0
    for size in sizes:
        out.append(paragraphs_to_html(paragraphs[start:start + size]))
        start += size
    return out


def load_chapters() -> list[Chapter]:
    chapters = [Chapter(number=i) for i in range(1, NUM_CHAPTERS + 1)]

    captions = load_captions()
    for chapter in chapters:
        chapter.segments = [
            Segment(number=i, captions=c)
            for i, c in enumerate(captions.get(chapter.number, []), 1)
        ]

    original_sizes = load_original_segment_sizes()
    for key, cfg in TEXTS.items():
        bodies = split_chapters(ROOT / cfg["file"])
        if len(bodies) != NUM_CHAPTERS:
            raise ValueError(f"{cfg['file']}: expected {NUM_CHAPTERS} chapters, got {len(bodies)}")
        sizes = original_sizes if key == "bn" else load_translation_segment_sizes(key)
        for chapter, body in zip(chapters, bodies):
            paragraphs = split_paragraphs(body)
            # A chapter absent from segmentations.jsonl is a single segment.
            chapter_sizes = sizes.get(chapter.number) or [len(paragraphs)]
            if len(chapter_sizes) != len(chapter.segments):
                raise SystemExit(
                    f"{cfg['file']}: chapter {chapter.number} has {len(chapter_sizes)} segments, "
                    f"but all/captions.jsonl has {len(chapter.segments)}."
                )
            texts = split_into_segments(cfg["file"], chapter.number, paragraphs, chapter_sizes)
            for segment, text in zip(chapter.segments, texts):
                segment.texts[key] = text

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
    """Build the (number, href, title_summary) list for the sidebar's chapter grid.

    The tooltip is English throughout, whichever language the reader is on, so
    it takes the English captions rather than the ones the page is showing.
    """
    return [
        {
            "number": chapter.number,
            "href": chapter_href(chapter.number),
            "title_summary": " / ".join(
                segment.captions["en"] for segment in chapter.segments
            ),
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
    text_tabs = [
        {"key": key, "label": cfg["label"], "lang": cfg["lang"], "caption": cfg["caption"]}
        for key, cfg in TEXTS.items()
    ]
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
