#!/usr/bin/env python3
"""
Re-flow existing segment translations onto the source's line structure.

translate_segments.py asks for a segment translation as a single free-form
string, so the source's one-line-per-utterance structure is lost. This pass
does not re-translate and does not proofread: it takes the translation that
already exists and puts the line breaks back, moving a word or two at a seam
only where the split makes it necessary. Results go to a separate JSONL so the
originals that qa-eval/ is built on stay untouched.
See all/aligned/README.md for the full rationale.
"""

import argparse
import difflib
import json
import re
import sys
from typing import Dict, List, Tuple

from llm7shi import Client
from utils import load_chapter_blocks


# The numbering is the alignment protocol, not decoration: it is what makes a
# broken response detectable and what stops the model from silently merging
# two source lines into one flowing sentence.
#
# Inserting line breaks is the whole job; proofreading is not asked for. Once
# the model is invited to correct the text, real fixes arrive mixed with edits
# that cannot be accepted and cannot be separated out - a segment-wide register
# shift (every contraction expanded), or a vocative rendered against the rest of
# the corpus ("Dada" to "Brother" in one segment while another kept "Ma"). The
# originals' own mistranslations are out of scope by the acceptance criterion
# anyway, so nothing is lost by declining them, and a near-zero drift becomes a
# usable signal instead of a number that has to be read by hand.
INSTRUCTIONS = """The text above is an existing translation of the numbered source lines. It was produced as flowing prose, so the source's line structure was lost.

Your task is to put the line breaks back, and nothing else. Distribute the existing translation over the source's lines and prefix every line with its source line number, numbered consecutively from 1, one output line per source line, in order.

This is not a translation task and not a proofreading task. Reproduce the existing translation word for word. Where its wording does not divide cleanly at a source line's boundary, adjust it at that boundary only: move the fewest words needed, and add or drop only what the split itself makes necessary.

Constraints:
- Every output line must be written in {target_lang}. Never copy a word or a line of the source text into the output, and never re-translate the source: the existing translation is the text being re-flowed.
- Change nothing else. Leave wording, punctuation, spelling and names exactly as they are - including anything you judge to be a mistranslation, an error or an awkward phrase. Correcting it is out of scope here.
- The line structure takes priority over prose flow. Never merge, split or drop a source line to make the result read better.
- Output the numbered lines only. No commentary, no headings, no blank lines."""

# Naming the words is what a general "keep proper nouns" rule failed to do: the
# model read "Mahishi" as an ordinary transliteration and helpfully turned it
# into "queen". The list says which words are fixed terms; the existing
# translation, not the glossary, decides how each is rendered - the glossary's
# English column has drifted from the text in places (বিভা is "Bibha" there and
# "Vibha" in all 472 occurrences of the translations).
NOUN_CONSTRAINT = """
- The words listed above are fixed proper nouns, not ordinary vocabulary. Keep the {target_lang} rendering the existing translation already uses for each of them - never the source-language spelling, and never a more familiar or more readable equivalent."""

LINE_RE = re.compile(r"^\s*(\d+)[.:)]?\s+(.*)$")

QUOTES = str.maketrans({c: "'" for c in '‘’“”"'})


def normalize(text: str) -> str:
    """Fold text down to what a drift comparison should actually care about.

    The originals mix straight and curly quotes (717 vs 378 apostrophes across
    all/en-gemini.jsonl), so a model that merely settles on one style would show
    up as drift. Folding them keeps the measurement about wording. Only the
    comparison is folded - the stored text keeps the model's quotes, which are
    directionally correct in a way a regex could not reproduce.
    """
    return re.sub(r"\s+", "", text).translate(QUOTES)


def number_lines(lines: List[str]) -> str:
    return "\n".join(f"{i} {line}" for i, line in enumerate(lines, 1))


def parse_numbered(text: str) -> Tuple[List[int], List[str]]:
    """Split a numbered response into its line numbers and its text.

    Unparseable lines are kept with number 0 rather than dropped, so that a
    malformed response shows up as a numbering violation instead of quietly
    losing content in the drift comparison.
    """
    numbers, texts = [], []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        if m := LINE_RE.match(line):
            numbers.append(int(m.group(1)))
            texts.append(m.group(2).strip())
        else:
            numbers.append(0)
            texts.append(line.strip())
    return numbers, texts


def align_segment(
    client: Client,
    source_lines: List[str],
    translation: str,
    source_lang: str,
    target_lang: str,
    nouns: List[str],
) -> str:
    # Each segment starts from the same blank history: carrying earlier segments
    # would grow every prompt without helping, since the source is fully given.
    c = client.copy()
    messages = [
        f"[Source text in {source_lang}, one numbered line per line]\n{number_lines(source_lines)}",
        f"[Existing {target_lang} translation of the text above]\n{translation}",
    ]
    instructions = INSTRUCTIONS
    if nouns:
        messages.append(f"[Proper nouns appearing in this segment]\n" + ", ".join(nouns))
        instructions += NOUN_CONSTRAINT
    messages.append(instructions.format(target_lang=target_lang))
    return c(messages).text.strip()


def load_glossary(path: str, language: str) -> List[str]:
    """Read one language column of the proper nouns TSV.

    The source column feeds the prompt's per-segment noun list; the target
    column is what check_glossary compares before and after. Longest first, so
    that find_nouns matches a compound term before its parts.
    """
    terms = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            header = next(f).rstrip("\n").split("\t")
            column = next(
                (i for i, name in enumerate(header) if name.lower() == language.lower()),
                -1,
            )
            if column < 0:
                return []
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) > column and (term := parts[column].strip()):
                    terms.append(term)
    except FileNotFoundError:
        pass
    return sorted(set(terms), key=len, reverse=True)


def find_nouns(keys: List[str], text: str) -> List[str]:
    """Pick the glossary's source-side terms that occur in this segment.

    Derived from the text rather than read from proper_nouns/en.jsonl, whose
    per-segment lists only hold each term's first appearance - segment 37:1
    lists three terms and not মহিষী, the one that actually needed protecting.

    Longer terms are matched first and their spans masked, so a term is only
    reported when it stands on its own rather than inside another (উদয় inside
    উদয়াদিত্য, লক্ষ্মী inside রাজ্য-লক্ষ্মী).

    Only the source-side keys are returned. The target renderings are left out
    on purpose: the existing translation is the authority on spelling, and the
    glossary disagrees with it in places.
    """
    found = []
    for key in keys:
        hit = False
        start = text.find(key)
        while start >= 0:
            # Every occurrence is masked, not just the first: otherwise a short
            # term still matches inside the second appearance of a longer one.
            if "\0" not in text[start:start + len(key)]:
                hit = True
                text = text[:start] + "\0" * len(key) + text[start + len(key):]
            start = text.find(key, start + 1)
        if hit:
            found.append(key)
    return found


def check_glossary(terms: List[str], translation: str, aligned: str) -> List[str]:
    """Report glossary terms the alignment dropped.

    Counts are compared before and after rather than merely checking presence,
    so a term replaced in one place out of three still shows up. Substring
    matches are not excluded: any over-counting applies equally to both sides,
    so a drop still means a real substitution.
    """
    lost = []
    for term in terms:
        before, after = translation.count(term), aligned.count(term)
        if after < before:
            lost.append(f"{term} {before}->{after}")
    return lost


def check_leak(source: str, translation: str, aligned: str) -> int:
    """Count characters the model carried over from the source language.

    The first full run leaked source text into 11 of 81 English segments - three
    of them re-translated into Bengali wholesale, most of the rest just left a
    proper noun or a whole line in the original script. No alphabet is named:
    a leaked character is one the source has and the existing translation does
    not, which catches Bengali in English or in Japanese output alike. Both
    conditions are needed - letters the translation lacks are otherwise ordinary
    (a segment with no 'x' in it), and letters the source has are otherwise
    shared (Bengali text carries ASCII digits and punctuation). Letters only,
    for the same reason: a newline or a curly quote the original translation
    happens to lack is a re-flow artefact, not carried-over source text.
    """
    leaked = set(source) - set(translation)
    return sum(1 for c in aligned if c.isalpha() and c in leaked)


SHORT_LINE = 40
RATIO_RANGE = (0.5, 2.0)
# Seam adjustments are a word or two per line; a proofreading run lands well
# above this (1.6-2.6% on the three segments that were run before the prompt
# stopped asking for corrections).
DRIFT_LIMIT = 0.01


def check_proportions(source_lines: List[str], texts: List[str]) -> List[str]:
    """Report output lines whose length is out of proportion to their source.

    A matching line count does not mean the lines match up. Segment 16:1 split
    one source line in two, dropped another (a hundred-word speech) and still
    came back with 11 lines for 11: everything between the two faults was off by
    one, and the only visible symptom was drift. Comparing each line's length
    against the segment's own median ratio catches that - the shifted lines are
    paired with the wrong source line and stop being proportionate.

    The median is per segment because the target-to-source length ratio varies
    by language and by passage. Short lines are skipped: an interjection can
    legitimately be half or twice its source's length.
    """
    ratios = [
        (i, len(text) / len(source))
        for i, (source, text) in enumerate(zip(source_lines, texts), 1)
        if len(source) > SHORT_LINE
    ]
    if len(ratios) < 3:
        return []
    median = sorted(r for _, r in ratios)[len(ratios) // 2]
    low, high = RATIO_RANGE
    return [
        f"line {i} is {ratio / median:.2f}x the expected length"
        for i, ratio in ratios
        if not low <= ratio / median <= high
    ]


def check(
    source_lines: List[str],
    translation: str,
    response: str,
    glossary: List[str],
) -> Tuple[List[str], float]:
    """Measure the response. Nothing here rejects it - see MEMO.md decision 3."""
    numbers, texts = parse_numbered(response)
    problems = []

    expected = list(range(1, len(source_lines) + 1))
    if numbers != expected:
        if len(numbers) != len(expected):
            problems.append(f"line count {len(numbers)} != {len(expected)}")
        else:
            problems.append("line numbering not consecutive from 1")

    if leaked := check_leak("\n".join(source_lines), translation, "\n".join(texts)):
        problems.append(f"source-language leak: {leaked} chars")

    if len(numbers) == len(expected):
        problems.extend(check_proportions(source_lines, texts))

    if lost := check_glossary(glossary, translation, "\n".join(texts)):
        problems.append("glossary: " + ", ".join(lost))

    # Now that only the line breaks are asked for, drift is a gate and not just
    # a number to read: what the seams need is a word or two per line, so a
    # segment that comes back rewritten says so by itself.
    # autojunk would treat any character occurring in over 1% of a long string
    # as noise - which here means the letters the comparison is made of - and
    # inflates the reported drift several-fold.
    before, after = normalize(translation), normalize("\n".join(texts))
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    drift = 0.0 if before == after else 1.0 - matcher.ratio()
    if drift > DRIFT_LIMIT:
        # The figure itself is printed alongside every violation, so naming the
        # limit here is enough.
        problems.append(f"drift over {DRIFT_LIMIT * 100:.1f}%")

    return problems, drift


def load_records(path: str) -> List[Dict]:
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except FileNotFoundError:
        pass
    return records


def save_records(path: str, records: List[Dict]) -> None:
    # The whole file is rewritten rather than appended to, because -s has to be
    # able to replace a record in place. The file is small enough that this
    # costs nothing, and it keeps resume and overwrite on the same code path.
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_segment_arg(value: str) -> List[Tuple[int, int]]:
    """Parse one or more chapter:segment references, comma separated.

    A list rather than a single reference because the failures worth redoing
    come in batches: the first full English run leaked source text into eleven
    segments, and naming them in one command keeps them on one client and one
    violation summary.
    """
    segments = []
    for item in value.split(","):
        m = re.fullmatch(r"(\d+):(\d+)", item.strip())
        if not m:
            raise argparse.ArgumentTypeError(
                "expected chapter:segment or a comma-separated list, e.g. 37:1 or 11:1,11:3"
            )
        segments.append((int(m.group(1)), int(m.group(2))))
    return segments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-flow existing translations onto the source's line structure"
    )
    parser.add_argument("translations", help="Translation JSONL from translate_segments.py")
    parser.add_argument("-m", "--model", required=True,
                        help="LLM model to use (e.g. openai:gpt-5.6-luna)")
    parser.add_argument("-o", "--output",
                        help="Output JSONL (default: <input>-aligned.jsonl)")
    parser.add_argument("-s", "--segment", type=parse_segment_arg,
                        help="Process only these chapter:segment references, comma separated "
                             "(e.g. 37:1 or 11:1,11:3), overwriting any existing records")
    parser.add_argument("--source", default="all/bn.md",
                        help="Source markdown file (default: all/bn.md)")
    parser.add_argument("--segmentation", default="segmentations.jsonl",
                        help="Segmentation JSONL file (default: segmentations.jsonl)")
    parser.add_argument("--proper-nouns", default="proper_nouns/all.tsv",
                        help="Proper nouns TSV, checked after the fact "
                             "(default: proper_nouns/all.tsv)")

    args = parser.parse_args()
    output = args.output or re.sub(r"\.jsonl$", "", args.translations) + "-aligned.jsonl"

    chapters = load_chapter_blocks(args.segmentation, args.source)["chapters"]
    records = load_records(args.translations)
    # Chapter 0 is the title record; it has no line structure to restore.
    targets = [r for r in records if r["chapter"] > 0]
    if args.segment:
        wanted = set(args.segment)
        targets = [r for r in targets if (r["chapter"], r["segment"]) in wanted]
        # Every unknown reference is reported, not just the first: a typo in a
        # long list is otherwise found one run at a time.
        if missing := wanted - {(r["chapter"], r["segment"]) for r in targets}:
            for chapter, segment in sorted(missing):
                print(f"No such segment: {chapter}:{segment}", file=sys.stderr)
            return 1

    existing = load_records(output)
    index = {(r["chapter"], r["segment"]): i for i, r in enumerate(existing)}

    # Params are worth seeing when testing one segment, and only noise otherwise.
    client = Client(model=args.model, show_params=len(args.segment or []) == 1)

    violations: List[Tuple[int, int, List[str], float]] = []
    processed = 0
    glossaries: Dict[str, List[str]] = {}

    for record in targets:
        chapter, segment = record["chapter"], record["segment"]
        key = (chapter, segment)

        if key in index and not args.segment:
            print(f"Chapter {chapter:2d} segment {segment} -> skipped (already aligned)")
            continue

        if chapter > len(chapters) or segment > len(chapters[chapter - 1]):
            print(f"Chapter {chapter:2d} segment {segment} -> no source segment", file=sys.stderr)
            continue

        source_text = chapters[chapter - 1][segment - 1]
        source_lines = source_text.split("\n")
        translation = record["response"]["translation"]

        for language in (record["source_lang"], record["target_lang"]):
            if language not in glossaries:
                glossaries[language] = load_glossary(args.proper_nouns, language)

        nouns = find_nouns(glossaries[record["source_lang"]], source_text)
        print(f"\nChapter {chapter:2d} segment {segment} -> aligning "
              f"({len(source_lines)} source lines, {len(nouns)} proper nouns)")
        response = align_segment(
            client, source_lines, translation,
            record["source_lang"], record["target_lang"], nouns,
        )

        problems, drift = check(
            source_lines, translation, response, glossaries[record["target_lang"]]
        )
        if problems:
            violations.append((chapter, segment, problems, drift))
            print(f"  violation: {', '.join(problems)}")
        print(f"  drift: {drift * 100:.1f}%")

        _, texts = parse_numbered(response)
        # Only the translation is carried over: summary and translation_notes
        # exist to feed translate_segments.py's running context, which this pass
        # does not have and does not need.
        aligned = {
            "chapter": chapter,
            "segment": segment,
            "source_lang": record["source_lang"],
            "target_lang": record["target_lang"],
            "model": args.model,
            "response": {"translation": "\n".join(texts)},
        }
        if key in index:
            existing[index[key]] = aligned
        else:
            index[key] = len(existing)
            existing.append(aligned)
        save_records(output, existing)
        processed += 1

    print(f"\nProcessed {processed} segments -> {output}")
    print(f"Violations: {len(violations)}/{processed}")
    for chapter, segment, problems, drift in violations:
        print(f"  {chapter:2d}:{segment} {', '.join(problems)} (drift {drift * 100:.1f}%)")

    return 0


if __name__ == "__main__":
    exit(main())
