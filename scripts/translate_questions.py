"""
Translate the English RAG question set into Japanese.

Translates the ``question``, ``answer`` and ``rationale`` fields of each record in
``questions-en.jsonl`` using Gemini, keeping proper nouns consistent with
``proper_nouns/all.tsv``. ``chapters`` (and ``anchor_id``) are language-independent
and copied as-is so the two files stay parallel.

Resumable: records whose ``anchor_id`` (or line index) is already present in the
output are skipped.
"""
import argparse
import json
from pathlib import Path

from pydantic import BaseModel, Field
from llm7shi import create_json_descriptions_prompt

from translate_segments import (
    load_proper_nouns_dictionary,
    create_translation_context,
    generate,
)

ROOT = Path(__file__).resolve().parent.parent


class QuestionTranslation(BaseModel):
    """Japanese translation of a single RAG question record."""
    translation_notes: str = Field(
        description="Key translation choices, difficult phrases, or proper-noun handling."
    )
    question: str = Field(description="Japanese translation of the question.")
    answer: str = Field(description="Japanese translation of the answer.")
    rationale: str = Field(description="Japanese translation of the rationale.")


def load_chapter_translations(path: Path) -> dict:
    """Map chapter number -> its full target-language translation text.

    Reads the segment translation JSONL (e.g. ``all/ja-gemini.jsonl``) produced by
    ``translate_segments.py`` and concatenates each chapter's segment translations in
    order, so the rationale's quotations can be matched against the existing official
    translation instead of being re-translated divergently.
    """
    segments: dict[int, list[tuple[int, str]]] = {}
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            chapter = int(rec["chapter"])
            segment = int(rec["segment"])
            if chapter == 0:  # title marker
                continue
            text = rec.get("response", {}).get("translation", "")
            if text:
                segments.setdefault(chapter, []).append((segment, text))
    return {ch: "\n".join(t for _, t in sorted(segs)) for ch, segs in segments.items()}


def build_reference_context(chapters, chapter_texts, target_lang) -> str:
    """Reference block with the official translation of the cited chapters."""
    if not chapter_texts:
        return ""
    parts = [f"[Reference {target_lang.title()} Translation of Cited Chapters]"]
    for ch in chapters:
        text = chapter_texts.get(int(ch))
        if text:
            parts.append(f"--- Chapter {ch} ---\n{text}")
    if len(parts) == 1:
        return ""
    parts.append("")
    return "\n".join(parts)


def translate_record(record, proper_nouns_dict, chapter_texts, source_lang, target_lang, model, show_params):
    context = create_translation_context(proper_nouns_dict, [], source_lang, target_lang)
    reference = build_reference_context(record.get("chapters", []), chapter_texts, target_lang)
    prompt = f"""Please translate the following {source_lang} RAG evaluation question record into {target_lang}.

{reference}
[{source_lang.title()} Question]
{record['question']}

[{source_lang.title()} Answer]
{record['answer']}

[{source_lang.title()} Rationale]
{record['rationale']}

[Translation Instructions]
1. Maintain consistency with the proper nouns dictionary above - use the exact same transliterations
2. Translate the question, answer, and rationale faithfully; do not add or drop information
3. Ensure the translation flows naturally in {target_lang}
4. When translating into Japanese, write in the plain/literary style (だ・である調) consistently
   across the question, answer, and rationale; do not use the polite です・ます style
5. The rationale quotes the source text. When it does, copy the wording verbatim from the
   reference translation of the cited chapters above so the quotations match the existing
   translation exactly; do not paraphrase the quoted passages
6. Provide translation notes explaining key choices"""

    json_descriptions = create_json_descriptions_prompt(QuestionTranslation)
    return generate(
        [context, prompt, json_descriptions],
        schema=QuestionTranslation,
        model=model,
        show_params=show_params,
    )


def load_done(output_path: Path):
    done = set()
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if line.strip():
                    rec = json.loads(line)
                    done.add(rec.get("anchor_id", i))
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-m", "--model", default="gemini-3.5-flash",
                        help="Gemini model for translation.")
    parser.add_argument("-i", "--input", type=Path, default=ROOT / "questions-en.jsonl",
                        help="English questions JSONL.")
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "questions-ja.jsonl",
                        help="Output Japanese questions JSONL.")
    parser.add_argument("-f", "--from_lang", default="english", help="Source language.")
    parser.add_argument("-t", "--to_lang", default="japanese", help="Target language.")
    parser.add_argument("--proper-nouns", type=Path, default=ROOT / "proper_nouns" / "all.tsv",
                        help="Proper nouns dictionary TSV.")
    parser.add_argument("--ja-text", type=Path, default=ROOT / "all" / "ja-gemini.jsonl",
                        help="Segment translation JSONL used as quotation reference for the rationale.")
    args = parser.parse_args()

    proper_nouns_dict = load_proper_nouns_dictionary(
        str(args.proper_nouns), args.from_lang, args.to_lang
    )
    print(f"Proper nouns loaded: {len(proper_nouns_dict)} entries")

    chapter_texts = load_chapter_translations(args.ja_text)
    print(f"Reference chapters loaded: {len(chapter_texts)} from {args.ja_text}")

    records = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    print(f"Loaded {len(records)} English questions from {args.input}")

    done = load_done(args.output)
    if done:
        print(f"Resuming: {len(done)} already translated")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    for i, record in enumerate(records):
        key = record.get("anchor_id", i)
        if key in done:
            print(f"Q{i + 1} (anchor {key}) → skipped")
            continue
        print(f"Q{i + 1} (anchor {key}) → translating...")
        result = translate_record(
            record, proper_nouns_dict, chapter_texts, args.from_lang, args.to_lang, args.model, False
        )
        if not result:
            print("  failed")
            continue
        out = {k: record[k] for k in ("anchor_id",) if k in record}
        out["question"] = result["question"]
        out["answer"] = result["answer"]
        out["chapters"] = record["chapters"]
        out["rationale"] = result["rationale"]
        with open(args.output, "a", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        done.add(key)

    print(f"\nDone. Output: {args.output}")


if __name__ == "__main__":
    main()
