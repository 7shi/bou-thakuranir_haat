"""Shared helpers for the answer_* scripts (vector / extract / filter).

Holds what is common across the answering strategies: paths, language names,
the per-chapter scene loader, the questions loader, and the answer-question
helper with its retry-on-empty loop. Retrieval machinery (index embedding,
top-k search, expand-and-merge) is vector-specific and stays in answer_vector.py;
the summarization prompt is Extract-specific and stays in answer_extract.py.
"""

import json
from pathlib import Path

from llm7shi.compat import generate_with_schema

ROOT = Path(__file__).resolve().parent.parent

LANGS = {"en": "English", "ja": "Japanese"}

PART_RANGES = {1: (1, 10), 2: (11, 20), 3: (21, 30), 4: (31, 37)}


def print_banner(label: str) -> None:
    """Print a separator banner with the given label.

    The label is fully formed by the caller (e.g. ``f"[Q{qid}/{total} Ch{ch}] {question}"``);
    this just standardizes the surrounding ``=`` rules so every answer script
    prints visually identical progress markers.
    """
    print(f"\n{'='*60}")
    print(label)
    print('='*60)


def print_answer_banner(qid: int, total: int, chapters: list[int], question: str) -> None:
    """Phase 2 banner for extract/filter: ``[Q{qid}/{total}: ch, ch, ...] question``.

    When ``chapters`` is empty, the colon-list is dropped so the banner reads
    ``[Q{qid}/{total}] question`` rather than ``[Q{qid}/{total}: ] question``.
    """
    if chapters:
        label = f"[Q{qid}/{total}: {', '.join(str(c) for c in chapters)}] {question}"
    else:
        label = f"[Q{qid}/{total}] {question}"
    print_banner(label)


def load_questions(path: Path) -> list[dict]:
    questions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def load_chapters(path: Path) -> dict[int, list[dict]]:
    chapters: dict[int, list[dict]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            ch, seg = rec.get("chapter", 0), rec.get("segment", 0)
            if ch == 0 or seg == 0:
                continue
            chapters.setdefault(ch, []).append({
                "chapter": ch,
                "segment": seg,
                "text": rec["response"]["translation"],
            })
    for scenes in chapters.values():
        scenes.sort(key=lambda s: s["segment"])
    return chapters


def answer_question(
    question: str,
    context: str,
    model: str,
    lang_name: str,
    *,
    preamble: str,
    context_prefix: str = "",
) -> str:
    """Answer a question using the provided context.

    The prompt is built as `{preamble}\n\nQuestion: {question}\n\n{context_prefix}{context}`,
    where `preamble` carries the full first paragraph (answer instruction +
    "do not use outside knowledge" + "answer only" clauses) and may use
    `{lang_name}` as a format placeholder. This keeps each caller's prompt
    wording verbatim — RAG ("context provided"), Extract ("chapter excerpts
    below"), Filter — without duplicating the retry-on-empty loop.

    The model occasionally returns an empty answer; retry up to 3 times
    (4 attempts total), then keep the empty result rather than loop forever.
    """
    prompt = (
        f"{preamble.format(lang_name=lang_name)}\n\n"
        f"Question: {question}\n\n"
        f"{context_prefix}{context}"
    )
    max_retries = 3
    answer = ""
    for attempt in range(max_retries + 1):
        result = generate_with_schema([prompt], model=model, show_params=False)
        answer = result.text.strip()
        if answer:
            return answer
        if attempt < max_retries:
            print(f"  empty answer — retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  answer still empty after {max_retries} retries — keeping as is")
    return answer
