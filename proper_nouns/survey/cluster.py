#!/usr/bin/env python3
"""
Cluster the surface forms found by survey.py into one entry per entity.

survey.py records proper nouns exactly as spelled, so one person appears under
many forms: inflected (প্রতাপাদিত্যের), shortened (প্রতাপ), and occasionally
misspelled (প্রতপাদিত্য). This script groups a chapter's forms by entity and
names a canonical form for each, which is what makes the misspellings visible.

The chapter is the unit: a chapter has a few dozen distinct forms, few enough
for one call to cover exhaustively and for a human to check, and its recurring
cast is the context that tells the model two spellings are the same person.
The whole corpus at once is too much, and mechanical grouping by prefix -
which does handle Indic suffix inflection - splits variants that differ near
the head of the word.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field
from llm7shi.compat import generate_with_schema
from llm7shi import create_json_descriptions_prompt


class Entity(BaseModel):
    canonical: str = Field(
        description="The name's base form: uninflected, carrying no case "
                    "ending, spelled correctly, and as complete as the text "
                    "shows the name to be. Normally one of the listed forms, "
                    "but when every listed form is inflected or misspelled, "
                    "give the base form even though it is not listed"
    )
    kind: Literal["person", "place", "title", "other"] = Field(
        description="What the name denotes: 'person' for an individual, "
                    "'place' for a location, 'title' for a title, rank, "
                    "kinship term or form of address used in place of a name "
                    "(Maharaj, Yuvaraj, elder brother, mother), 'other' for "
                    "anything else, such as a dynasty or a people"
    )
    forms: List[str] = Field(
        description="Every listed form belonging to this name, copied "
                    "verbatim from the list"
    )


class EntityClusters(BaseModel):
    entities: List[Entity] = Field(
        description="One entry per distinct name. Together these must use "
                    "every listed form exactly once"
    )


INSTRUCTIONS = """Above are the proper nouns that appear in one chapter of a {lang} novel, one per line, with the number of times each occurs. They are surface forms taken verbatim from the text, so the same name may be listed several times over: inflected or case-marked, in full and shortened, or simply misspelled.

Group the forms that are spellings of the SAME NAME, and give each group that name's base form.

Group by name, not by who is being referred to. This chapter names one person in several ways - by name, by title, by kinship term, by epithet - and those are separate entries here, however plainly they mean the same character in the story. Only spellings of one and the same name belong together.

Rules:
- Use every listed form exactly once. Every form belongs to some entry, even if that entry has only one form.
- Never invent, correct or normalize a listed form. Copy each one exactly as listed. (The base form you give in `canonical` is the one exception, and only when no listed form is already the base form.)
- Group together: inflected and case-marked forms, sandhi variants, differences in word spacing or hyphenation, a short form of the name alongside its full form, and spellings that differ only by a missing or wrong matra - those misspellings are what this survey is looking for, so they must land with the name they belong to rather than becoming entries of their own.
- Keep apart: different names, even when they share a first element ({lang} names often do), and a name and a title, even when they denote the same character. A title, kinship term, epithet or divine byname is its own entry with its own base form; several such words for one character stay several entries.
- A form that carries a title in front of the name (as in "King <name>") belongs to the name's entry, not to the title's.

There are {count} forms listed.{known}"""

KNOWN = """

Earlier chapters of this novel settled the names below, given as base form and kind. When a form listed above is a spelling of one of them, answer with exactly that base form and that same kind, so that one name keeps one spelling throughout the book - including when every occurrence in this chapter is misspelled, in which case the established spelling is the base form and the chapter's own spelling is only a variant of it.

The list is a reference, not a checklist. Names absent from it are expected; give those a base form of your own. Never bend a form onto a listed name it does not actually spell.

{names}"""

RETRY = """Your previous answer did not use every form exactly once.
{problems}
Answer again, covering exactly the listed forms."""


def format_forms(counts: Counter) -> str:
    # Sorted by spelling, not by frequency, so variants of one name sit next to
    # each other and the model sees them together.
    return "\n".join(f"{form}\t{count}" for form, count in sorted(counts.items()))


def format_known(known: Dict[str, str]) -> str:
    return "\n".join(f"{name}\t{kind}" for name, kind in sorted(known.items()))


def check(result: Dict, forms: set) -> List[str]:
    """Report the ways the clustering fails to be a partition of `forms`."""
    used = [f for entity in result["entities"] for f in entity["forms"]]
    problems = []
    if missing := forms - set(used):
        problems.append(f"- Missing forms: {', '.join(sorted(missing))}")
    if unknown := set(used) - forms:
        problems.append(f"- Forms not in the list: {', '.join(sorted(unknown))}")
    if duplicated := {f for f, n in Counter(used).items() if n > 1}:
        problems.append(f"- Forms used more than once: {', '.join(sorted(duplicated))}")
    # The canonical form is deliberately not required to be among the forms:
    # a name whose every occurrence in the chapter is inflected has no base
    # form to pick from.
    return problems


def cluster_chapter(counts: Counter, known: Dict[str, str], lang: str,
                    model: str, show_params: bool) -> Optional[Dict]:
    forms = set(counts)
    prompt = INSTRUCTIONS.format(
        lang=lang, count=len(forms),
        known=KNOWN.format(names=format_known(known)) if known else "")
    json_descriptions = create_json_descriptions_prompt(EntityClusters)
    contents = [format_forms(counts), prompt, json_descriptions]
    for attempt in range(5, 0, -1):
        response = generate_with_schema(
            contents,
            schema=EntityClusters,
            model=model,
            show_params=show_params,
        )
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as e:
            print(f"  Error decoding JSON: {e}")
            problems = None
        else:
            problems = check(result, forms)
            if not problems:
                return result
            print("  Clusters do not partition the input:")
            for problem in problems:
                print(f"  {problem}")
        if attempt > 1:
            print("  Retrying...")
            # Feed the diff back rather than re-asking blind: the failures are
            # dropped forms, which the model can fix if told which ones.
            if problems:
                contents = [format_forms(counts), prompt,
                            RETRY.format(problems="\n".join(problems)),
                            json_descriptions]
    return None


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
    # The whole file is rewritten rather than appended to, because -c has to be
    # able to replace a record in place.
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_chapters(path: str) -> Tuple[Dict[int, Counter], str]:
    """Collapse a survey JSONL into per-chapter form counts."""
    chapters: Dict[int, Counter] = {}
    lang = ""
    for record in load_records(path):
        lang = lang or record.get("target_lang", "")
        counts = chapters.setdefault(record["chapter"], Counter())
        for nouns in record["proper_nouns"].values():
            counts.update(nouns)
    return chapters, lang


# Corrections to the clustering, each one checked against all/bn.md. They are
# recorded here rather than edited into the output so that the output stays a
# plain record of what the model answered, and so that a re-run of a chapter
# does not silently lose them.
#
# A form the model filed under the wrong name. Most come from the survey
# splitting a two-word name across two entries, which leaves the chapter's
# clustering with two halves to place.
REASSIGN = {
    # "প্রতাপাদিত্য রায়ের" - the surname is Pratapaditya's here, not Basantaray's,
    # though the same chapter's "বসন্ত রায়কে" really is Basantaray.
    (2, "রায়ের"): "প্রতাপাদিত্য",
    # "রাম চন্দ্র বলিলেন" - Ramchandra written with a space, surveyed as two forms.
    (11, "রাম"): "রামচন্দ্র রায়",
    (11, "চন্দ্র"): "রামচন্দ্র রায়",
    # "রাম, রাম! ও কথা মুখে আনিতে নাই" - the god invoked in dismay, as in ch4, not
    # Ramchandra Ray.
    (28, "রাম"): "রাম",
    # "পরাণ ও হরি দুই ভাই আসিল" - a villager's name, not the word প্রাণ.
    (33, "পরাণ"): "পরাণ",
}

# Names the chapters settled on separately that the text shows to be one.
MERGE = {
    "রমাই": "রমাই ভাঁড়",       # the jester, also called রমাই ঠাকুর and, in jest,
    "রমাই ঠাকুর": "রমাই ভাঁড়",  # সেনাপতি রমাই after he bests the general in wit
    "উদয়": "উদয়াদিত্য",
}

# The kind to record where the correction changes it.
KINDS = {"পরাণ": "person"}

# Surveyed as proper nouns but not names at all - pronouns the survey mistook
# for forms of address.
DROP = {"তাঁর", "তাহা", "তোরা"}


def resolve_kinds(records: List[Dict]) -> Dict[str, str]:
    """One kind per name for the whole book, by majority across its chapters."""
    votes: Dict[str, Counter] = {}
    for record in records:
        for entity in record["entities"]:
            for form in entity["forms"]:
                canonical = REASSIGN.get((record["chapter"], form), entity["canonical"])
                canonical = MERGE.get(canonical, canonical)
                votes.setdefault(canonical, Counter())[entity["kind"]] += 1
    return {name: KINDS.get(name) or v.most_common(1)[0][0]
            for name, v in votes.items()}


def normalize(records: List[Dict]) -> List[Dict]:
    """Apply the corrections, keeping the per-chapter shape.

    Chapter by chapter is how the list is used: anchoring another language to
    Bengali happens one chapter at a time, and that chapter's two or three
    dozen names are what should be offered to the model - not the book's
    entire cast, which only invites matches to characters who are not there.
    Whatever needs the corpus-wide view aggregates these with collect_names.
    """
    kinds = resolve_kinds(records)
    result = []
    for record in sorted(records, key=lambda r: r["chapter"]):
        entities: Dict[str, set] = {}
        for entity in record["entities"]:
            for form in entity["forms"]:
                canonical = REASSIGN.get((record["chapter"], form), entity["canonical"])
                canonical = MERGE.get(canonical, canonical)
                if canonical in DROP:
                    continue
                entities.setdefault(canonical, set()).add(form)
        result.append({
            "chapter": record["chapter"],
            "target_lang": record["target_lang"],
            "entities": [{"canonical": name, "kind": kinds[name],
                          "forms": sorted(forms)}
                         for name, forms in sorted(entities.items())],
        })
    return result


def collect_names(records: List[Dict]) -> List[Dict]:
    """Aggregate normalized chapters into one entry per name."""
    names: Dict[str, Dict] = {}
    for record in sorted(records, key=lambda r: r["chapter"]):
        for entity in record["entities"]:
            name = names.setdefault(
                entity["canonical"],
                {"canonical": entity["canonical"], "kind": entity["kind"],
                 "chapters": [], "forms": set()})
            name["chapters"].append(record["chapter"])
            name["forms"].update(entity["forms"])
    return [{"canonical": n["canonical"], "kind": n["kind"],
             "chapters": n["chapters"], "forms": sorted(n["forms"])}
            for _, n in sorted(names.items())]


def collect_known(records: List[Dict], chapter: int) -> Dict[str, str]:
    """The names settled by the chapters clustered so far.

    Passing them into the next chapter is what keeps one name to one spelling
    across the book, and it lets a chapter whose every occurrence of a name is
    misspelled still be read as a variant of the established spelling. When a
    chapter is redone with -c, the names of every other chapter count as
    established, whether they come before it or after.
    """
    known: Dict[str, str] = {}
    for record in sorted(records, key=lambda r: r["chapter"]):
        if record["chapter"] == chapter:
            continue
        for entity in record["entities"]:
            known.setdefault(entity["canonical"], entity["kind"])
    return known


def default_output(input_path: str) -> str:
    stem = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(input_path)),
                        f"cluster-{stem}.jsonl")


def default_normalized(output_path: str) -> str:
    name = os.path.basename(output_path)
    name = name[len("cluster-"):] if name.startswith("cluster-") else name
    return os.path.join(os.path.dirname(os.path.abspath(output_path)),
                        f"normalized-{name}")


def parse_chapter_arg(value: str) -> List[int]:
    chapters = []
    for item in value.split(","):
        if not re.fullmatch(r"\d+", item.strip()):
            raise argparse.ArgumentTypeError(
                "expected a chapter number or a comma-separated list, e.g. 1 or 1,3")
        chapters.append(int(item))
    return chapters


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cluster surveyed proper-noun surface forms by entity, per chapter")
    parser.add_argument("survey",
                        help="Survey JSONL from survey.py (e.g. proper_nouns/survey/bn.jsonl)")
    parser.add_argument("-m", "--model", required=True,
                        help="LLM model to use (e.g. openai:gpt-5.6-terra)")
    parser.add_argument("-o", "--output",
                        help="Output JSONL (default: cluster-<lang>.jsonl next to the input)")
    parser.add_argument("-l", "--lang",
                        help="Language name to tell the model (default: the survey's target_lang)")
    parser.add_argument("-c", "--chapter", type=parse_chapter_arg,
                        help="Process only these chapters, comma separated (e.g. 1 or 1,3), "
                             "overwriting any existing records")
    parser.add_argument("-N", "--normalize", action="store_true",
                        help="Make no calls: fold the clustered chapters into one corrected "
                             "list of names, written as normalized-<lang>.jsonl")
    args = parser.parse_args()
    output = args.output or default_output(args.survey)

    if args.normalize:
        records = load_records(output)
        if not records:
            print(f"Nothing clustered yet in {output}", file=sys.stderr)
            return 1
        normalized = normalize(records)
        path = default_normalized(output)
        save_records(path, normalized)
        entities = collect_names(normalized)
        kinds = Counter(e["kind"] for e in entities)
        forms = sum(len(e["forms"]) for e in entities)
        print(f"{len(records)} chapters, {forms} forms -> {len(entities)} names")
        print("  " + ", ".join(f"{kind} {n}" for kind, n in kinds.most_common()))
        print(f"  written to {path}")
        return 0

    chapters, survey_lang = load_chapters(args.survey)
    if not chapters:
        print(f"No records in {args.survey}", file=sys.stderr)
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
        counts = chapters[chapter]

        if chapter in index and not args.chapter:
            print(f"Chapter {chapter:2d} -> skipped (already clustered)")
            continue
        if not counts:
            print(f"Chapter {chapter:2d} -> no proper nouns")
            result = {"entities": []}
        else:
            known = collect_known(existing, chapter)
            print(f"\nChapter {chapter:2d} -> clustering ({len(counts)} forms, "
                  f"{len(known)} names known)")
            result = cluster_chapter(counts, known, lang, args.model,
                                     show_params=chapter == targets[0])
            if result is None:
                print(f"Chapter {chapter:2d} -> failed, skipping", file=sys.stderr)
                continue
            print(f"Chapter {chapter:2d} -> {len(result['entities'])} entities")

        record = {
            "chapter": chapter,
            "target_lang": lang,
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
