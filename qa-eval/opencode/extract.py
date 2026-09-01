#!/usr/bin/env python3
"""Extract chapter text from all/<lang>-gemini.jsonl into per-chapter .txt files.

For each language in LANGS, reads all/<lang>-gemini.jsonl (chapter/segment
records with the translated text in response.translation), concatenates the
segments of each chapter in order, and writes the result to
<lang>/<chapter:02d>.txt (e.g. en/01.txt, ja/01.txt, ...).

Some segments run past 4000 characters on a single line (their existing
internal "\n" breaks, e.g. between dialogue paragraphs, are already up to a
few hundred characters apart). Each line is wrapped to WRAP_WIDTH columns
before writing, since opencode's file-attachment reader truncates any single
line past 2000 characters (`packages/opencode/src/tool/read.ts`,
`MAX_LINE_LENGTH = 2000`), silently dropping content past the cut — see
../../MEMO.md for how this was found. WRAP_WIDTH sits with a safety margin
below that 2000-char limit; only English crosses it (Japanese's longest line
is 1326 chars, per MEMO.md), so Japanese chapters end up unwrapped, unlike
English's, which wrap at whatever point is nearest to the width and at or
before an existing space. Wrapping line-by-line — instead of the whole
segment at once — keeps existing "\n" breaks intact instead of flattening
them into the wrapped block.
"""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from answer import ROOT, LANGS, load_chapters

CHAPTER_HEADER = {
    "en": "## Chapter {}",
    "ja": "## 第{}章",
}

WRAP_WIDTH = 1800


def wrap_text(text: str) -> str:
    return "\n".join(
        textwrap.fill(line, WRAP_WIDTH, break_on_hyphens=False) if line.strip() else line
        for line in text.split("\n")
    )


def main():
    out_root = Path(__file__).resolve().parent
    for lang in LANGS:
        src = ROOT / "all" / f"{lang}-gemini.jsonl"
        chapters = load_chapters(src)
        lang_dir = out_root / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        header = CHAPTER_HEADER[lang]
        for ch, scenes in sorted(chapters.items()):
            body = "\n\n".join(wrap_text(s["text"]) for s in scenes)
            text = f"{header.format(ch)}\n\n{body}"
            (lang_dir / f"{ch:02d}.txt").write_text(text + "\n", encoding="utf-8")
        print(f"{lang}: {len(chapters)} chapters -> {lang_dir}")


if __name__ == "__main__":
    main()
