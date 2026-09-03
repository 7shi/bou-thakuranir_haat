#!/usr/bin/env python3
"""
Anchor one translation's surface forms to the Bengali names, per chapter.

cluster.py groups a survey's forms by the name they spell, but only for
Bengali. The other three languages are not clustered on their own: what a
chapter's English "Vibha" and "Bibha" are variants of is a question about the
Bengali বিভা they both render, and deciding it inside English alone throws
away the one piece of evidence that settles it. So each chapter's target-
language forms are tied to that chapter's Bengali names, and the base form the
language settles on is chosen by comparison with the Bengali.

The chapter is the unit, as in cluster.py, and for the same reasons. Only that
chapter's 5 to 32 Bengali names are offered, never the book's whole cast, which
would invite matches to characters who are not in the passage.

Within the chapter, both sides are listed with how often each is used and the
lines it stands on. Spelling alone leaves the titles undecidable - chapter 1's
"Lord" and "lord" render প্রভু and নাথ, each used once - and position is the
only evidence that separates them. It is offered as evidence, not as a rule:
the line numbers correspond because the translations are aligned, but wording
can still shift to an adjacent line in the re-flow pass (see
all/aligned/README.md), which is why the decision stays at chapter level.

Not everything ties. A translator's addition, a common noun the survey took
for a name, a title the Bengali leaves implicit - these get an empty `bengali`
and stay visible as unresolved rather than being forced onto some name they do
not spell. Many:many is expected in the other direction too: one Bengali name
may be rendered by several distinct target names (a name and an epithet), and
those stay separate entries, exactly as in cluster.py.
"""

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field
from llm7shi.compat import generate_with_schema
from llm7shi import create_json_descriptions_prompt

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cluster import load_records, save_records, parse_chapter_arg


class Anchor(BaseModel):
    canonical: str = Field(
        description="The base form this language settles on for the name: "
                    "uninflected, spelled the way the Bengali name is best "
                    "rendered, and as complete as the text shows the name to "
                    "be. Normally one of the listed forms; when every listed "
                    "form is inflected or misspelled, give the base form even "
                    "though it is not listed"
    )
    bengali: str = Field(
        description="The Bengali name from the reference list that these "
                    "forms render, copied exactly. Empty string when they "
                    "render none of them"
    )
    kind: Literal["person", "place", "title", "other"] = Field(
        description="What the name denotes: 'person' for an individual, "
                    "'place' for a location, 'title' for a title, rank, "
                    "kinship term or form of address used in place of a name "
                    "(Maharaj, Yuvaraj, elder brother, mother), 'other' for "
                    "anything else, such as a dynasty or a people. When "
                    "`bengali` is filled in, use that name's kind"
    )
    forms: List[str] = Field(
        description="Every listed form belonging to this name, copied "
                    "verbatim from the list"
    )


class AnchoredNames(BaseModel):
    entities: List[Anchor] = Field(
        description="One entry per distinct name in the translation. Together "
                    "these must use every listed form exactly once"
    )


INSTRUCTIONS = """Above are the proper nouns that appear in one chapter of the {lang} translation of a Bengali novel, one per line, as the form, how many times it occurs, and the lines it occurs on. They are surface forms taken verbatim from the translation, so the same name may be listed several times over: inflected or possessive, in full and shortened, or simply misspelled.

Below are the names the Bengali original uses in that same chapter, as name, kind, count and lines.

{names}

Group the listed {lang} forms that are spellings of the SAME NAME, give each group the base form this translation should use for it, and say which Bengali name it renders.

Decide by comparison with the Bengali, not by looking at the {lang} alone. Two spellings that differ - one letter, a doubled consonant, a missing vowel - are the same name when they render the same Bengali name, and the base form to give is the one that renders it properly. This holds even when every occurrence in this chapter is misspelled: the base form is then a spelling the chapter never uses.

Group by name, not by who is being referred to. One character may be named, titled and addressed several ways; those are separate entries here, each tied to the Bengali name it renders, however plainly they mean the same person in the story.

Rules:
- Use every listed {lang} form exactly once. Every form belongs to some entry, even if that entry has only one form.
- Never invent, correct or normalize a listed form. Copy each one exactly as listed. (The base form you give in `canonical` is the one exception, and only when no listed form is already the base form.)
- Copy `bengali` exactly from the list above, or leave it empty. Never write a Bengali name that is not listed there.
- Leave `bengali` empty rather than forcing a match: a translator may add a name the original does not have, and the survey may have taken a common noun for one. An unmatched entry is a useful answer; a wrong match is not.
- Several entries may render the same Bengali name - a name and the title or epithet used for one character are two entries, each pointing at the Bengali name it renders, or left empty when the original has no counterpart for it.
- Keep apart: different names, even when they share an element, and a name and a title, even when they denote the same character.
- A form that carries a title in front of the name (as in "King <name>") belongs to the name's entry, not to the title's.
- Weigh the counts and the lines, which is what settles names that spell alike: a form used three times renders a name used about as often rather than a one-off, and a form standing on one line renders the name standing on that same line. Positions are written "segment:line" and correspond on both sides, closely but not exactly - a phrase may sit a line away in the translation - so read them as evidence, not as proof.

There are {count} {lang} forms listed.{known}"""

KNOWN = """

Earlier chapters of this translation settled the renderings below, as Bengali name, kind, and the {lang} base form chosen for it. When a form listed above renders one of those Bengali names, answer with exactly that {lang} base form, so that one name keeps one spelling throughout the book - including when every occurrence in this chapter is misspelled.

The list is a reference, not a checklist. Bengali names absent from it are expected; settle those on your own.

{settled}"""

RETRY = """Your previous answer had these problems:
{problems}
Answer again, covering exactly the listed {lang} forms."""


# Both sides of the comparison are listed the same way - how often a name is
# used and where - because that is what settles the cases the spelling cannot.
# A chapter's three "Grand-uncle" match a দাদামহাশয় used five times rather
# than a খুড়া used once, and two one-off titles that look alike in English are
# told apart by the line they stand on.
POSITION_LIMIT = 12


def format_places(places: List[str]) -> str:
    # One line listed once however often it names the name - the count column
    # carries the multiplicity, and a repeated position would only eat into
    # the dozen that fit.
    unique = list(dict.fromkeys(places))
    shown = ", ".join(unique[:POSITION_LIMIT])
    return shown + ", ..." if len(unique) > POSITION_LIMIT else shown


def format_names(entities: List[Dict]) -> str:
    rows = []
    for entity in entities:
        row = [entity["canonical"], entity["kind"]]
        if "count" in entity:
            row.append(str(entity["count"]))
        if entity.get("lines"):
            row.append(format_places(entity["lines"]))
        rows.append("\t".join(row))
    return "\n".join(rows)


def format_forms(places: Dict[str, List[str]]) -> str:
    # Sorted by spelling, not by frequency, so variants of one name sit next
    # to each other and the model sees them together.
    return "\n".join(f"{form}\t{len(positions)}\t{format_places(positions)}"
                      for form, positions in sorted(places.items()))


def format_settled(settled: Dict[Tuple[str, str], str]) -> str:
    return "\n".join(f"{bengali}\t{kind}\t{canonical}"
                     for (bengali, kind), canonical in sorted(settled.items()))


def check(result: Dict, forms: set, names: set) -> List[str]:
    """Report the ways the answer fails to be a partition tied to real names.

    Same partition check as cluster.py - a dropped or invented form is what to
    expect from a list this long - plus the one failure this step adds: a
    `bengali` that is not among the names offered for this chapter, which is
    the model reaching for a character who is not in the passage.
    """
    used = [f for entity in result["entities"] for f in entity["forms"]]
    problems = []
    if missing := forms - set(used):
        problems.append(f"- Missing forms: {', '.join(sorted(missing))}")
    if unknown := set(used) - forms:
        problems.append(f"- Forms not in the list: {', '.join(sorted(unknown))}")
    if duplicated := {f for f, n in Counter(used).items() if n > 1}:
        problems.append(f"- Forms used more than once: {', '.join(sorted(duplicated))}")
    if invented := {e["bengali"] for e in result["entities"]
                    if e["bengali"] and e["bengali"] not in names}:
        problems.append("- Bengali names not in the chapter's list: "
                        + ", ".join(sorted(invented)))
    return problems


def anchor_chapter(places: Dict[str, List[str]], entities: List[Dict],
                   settled: Dict[Tuple[str, str], str], lang: str,
                   model: str, show_params: bool) -> Optional[Dict]:
    forms = set(places)
    names = {e["canonical"] for e in entities}
    prompt = INSTRUCTIONS.format(
        lang=lang, count=len(forms), names=format_names(entities),
        known=KNOWN.format(lang=lang, settled=format_settled(settled)) if settled else "")
    json_descriptions = create_json_descriptions_prompt(AnchoredNames)
    contents = [format_forms(places), prompt, json_descriptions]
    for attempt in range(5, 0, -1):
        response = generate_with_schema(
            contents,
            schema=AnchoredNames,
            model=model,
            show_params=show_params,
        )
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as e:
            print(f"  Error decoding JSON: {e}")
            problems = None
        else:
            problems = check(result, forms, names)
            if not problems:
                return result
            print("  Answer rejected:")
            for problem in problems:
                print(f"  {problem}")
        if attempt > 1:
            print("  Retrying...")
            # Feed the diff back rather than re-asking blind: the failures are
            # dropped forms and stray Bengali names, both fixable when named.
            if problems:
                contents = [format_forms(places), prompt,
                            RETRY.format(lang=lang, problems="\n".join(problems)),
                            json_descriptions]
    return None


def load_places(path: str) -> Tuple[Dict[int, Dict[str, List[str]]], str]:
    """Collapse a survey JSONL into per-chapter form positions.

    Each form keeps the "segment:line" places it was found on, in reading
    order, which is what lets the target side be compared with the Bengali by
    position as well as by count.
    """
    chapters: Dict[int, Dict[str, List[str]]] = {}
    lang = ""
    for record in sorted(load_records(path), key=lambda r: (r["chapter"], r["segment"])):
        lang = lang or record.get("target_lang", "")
        places = chapters.setdefault(record["chapter"], {})
        for line, nouns in sorted(record["proper_nouns"].items(), key=lambda x: int(x[0])):
            for noun in nouns:
                places.setdefault(noun, []).append(f"{record['segment']}:{line}")
    return chapters, lang


def load_names(path: str) -> Tuple[Dict[int, List[Dict]], str]:
    """The Bengali names per chapter, from cluster.py -N's normalized output."""
    chapters: Dict[int, List[Dict]] = {}
    lang = ""
    for record in load_records(path):
        lang = lang or record.get("target_lang", "")
        chapters[record["chapter"]] = record["entities"]
    return chapters, lang


def collect_settled(records: List[Dict], chapter: int) -> Dict[Tuple[str, str], str]:
    """The Bengali-to-target renderings settled by the other chapters.

    Keyed by the Bengali name and its kind, so a name and a title that share a
    spelling in Bengali stay apart. Entries with no Bengali name are left out:
    they are the unresolved ones, and offering them as precedent would only
    spread a guess. As in cluster.py, a chapter redone with -c counts every
    other chapter as settled, whichever side of it they fall on.
    """
    settled: Dict[Tuple[str, str], str] = {}
    for record in sorted(records, key=lambda r: r["chapter"]):
        if record["chapter"] == chapter:
            continue
        for entity in record["entities"]:
            if entity["bengali"]:
                settled.setdefault((entity["bengali"], entity["kind"]),
                                   entity["canonical"])
    return settled


def default_output(input_path: str) -> str:
    stem = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(input_path)),
                        f"anchor-{stem}.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Anchor a translation's surveyed proper nouns to the Bengali names, per chapter")
    parser.add_argument("survey",
                        help="Survey JSONL from survey.py (e.g. proper_nouns/survey/en.jsonl)")
    parser.add_argument("-m", "--model", required=True,
                        help="LLM model to use (e.g. openai:gpt-5.6-terra)")
    parser.add_argument("-n", "--names",
                        help="Bengali names per chapter from cluster.py -N "
                             "(default: normalized-bn.jsonl next to the survey)")
    parser.add_argument("-o", "--output",
                        help="Output JSONL (default: anchor-<lang>.jsonl next to the input)")
    parser.add_argument("-l", "--lang",
                        help="Language name to tell the model (default: the survey's target_lang)")
    parser.add_argument("-c", "--chapter", type=parse_chapter_arg,
                        help="Process only these chapters, comma separated (e.g. 1 or 1,3), "
                             "overwriting any existing records")
    args = parser.parse_args()
    output = args.output or default_output(args.survey)
    names_path = args.names or os.path.join(
        os.path.dirname(os.path.abspath(args.survey)), "normalized-bn.jsonl")

    chapters, survey_lang = load_places(args.survey)
    if not chapters:
        print(f"No records in {args.survey}", file=sys.stderr)
        return 1
    names, source_lang = load_names(names_path)
    if not names:
        print(f"No Bengali names in {names_path}", file=sys.stderr)
        return 1
    lang = args.lang or survey_lang
    targets = sorted(chapters)
    if args.chapter:
        if missing := set(args.chapter) - set(targets):
            for chapter in sorted(missing):
                print(f"No such chapter: {chapter}", file=sys.stderr)
            return 1
        targets = sorted(set(args.chapter))

    existing = load_records(output)
    index = {r["chapter"]: i for i, r in enumerate(existing)}

    for chapter in targets:
        places = chapters[chapter]
        entities = names.get(chapter, [])

        if chapter in index and not args.chapter:
            print(f"Chapter {chapter:2d} -> skipped (already anchored)")
            continue
        if not places:
            print(f"Chapter {chapter:2d} -> no proper nouns")
            result = {"entities": []}
        elif not entities:
            print(f"Chapter {chapter:2d} -> no Bengali names, skipping", file=sys.stderr)
            continue
        else:
            settled = collect_settled(existing, chapter)
            print(f"\nChapter {chapter:2d} -> anchoring ({len(places)} forms, "
                  f"{len(entities)} Bengali names, {len(settled)} settled)")
            result = anchor_chapter(places, entities, settled, lang, args.model,
                                    show_params=chapter == targets[0])
            if result is None:
                print(f"Chapter {chapter:2d} -> failed, skipping", file=sys.stderr)
                continue
            unresolved = sum(1 for e in result["entities"] if not e["bengali"])
            print(f"Chapter {chapter:2d} -> {len(result['entities'])} names"
                  + (f", {unresolved} unresolved" if unresolved else ""))

        record = {
            "chapter": chapter,
            "target_lang": lang,
            "source_lang": source_lang or "Bengali",
            "model": args.model,
            "entities": result["entities"],
        }
        if chapter in index:
            existing[index[chapter]] = record
        else:
            existing.append(record)
            existing.sort(key=lambda r: r["chapter"])
            index = {r["chapter"]: i for i, r in enumerate(existing)}
        save_records(output, existing)

    return 0


if __name__ == "__main__":
    sys.exit(main())
