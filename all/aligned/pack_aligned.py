#!/usr/bin/env python3
"""
Store an aligned JSONL as a delta against the translation it was aligned from.

align_lines.py re-flows an existing translation onto the source's line
structure without rewriting it, so an aligned file is very nearly a copy of
all/<lang>-gemini.jsonl: the same words, with line breaks inserted and a word
or two moved at the seams. Keeping whole copies of it costs 300-400 KB each and
buries the interesting part - what actually changed - in text that is already
in the repository. This packs the aligned file into the edits alone: 4.6 KB for
Japanese, 8.9 KB for English, a 35-91x reduction, and a diff a reviewer can
read. See all/aligned/README.md decision 7.

    uv run all/aligned/pack_aligned.py pack   ja-gemini-terra.jsonl
    uv run all/aligned/pack_aligned.py unpack ja-gemini-terra.delta.jsonl

Run from anywhere - `-b`/the base path and the recorded "base" field resolve
against the repo root, not the caller's CWD. See Makefile for the `pack`/
`unpack` targets.

pack refuses to write a delta it cannot round-trip: it unpacks its own output
in memory and compares the bytes against the file it was given, so a delta on
disk is one that has already been proved reversible.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
from typing import Dict, List, Tuple

from align_lines import load_records, save_records

# The aligned records carry the translation only (decision 5), and every field
# but these three is constant across a file, so they go in the header.
PER_RECORD = ("chapter", "segment")
CONSTANT = ("source_lang", "target_lang", "model")

# The "base" field is stored repo-root-relative (e.g. "all/en-gemini.jsonl"),
# both in freshly-written headers and in every delta already committed. That
# string has to resolve against the repo root regardless of the caller's CWD,
# not just when this script happens to be run from there.
REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def sha256(path: str) -> str:
    with open(resolve(path), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def delta_path(path: str) -> str:
    return re.sub(r"\.jsonl$", "", path) + ".delta.jsonl"


def base_path(path: str) -> str:
    """en-gemini-terra.jsonl -> all/en-gemini.jsonl (repo-root-relative)

    Aligned files live in all/aligned/ and are named after their base with the
    model appended; the base itself lives one directory up, in all/. Only the
    basename of `path` is used, so this does not depend on how much of the
    directory prefix the caller included.
    """
    name = os.path.basename(path)
    name = re.sub(r"\.delta(?=\.jsonl$)", "", name)
    name = re.sub(r"-[^-.]+(?=\.jsonl$)", "", name)
    return os.path.join("all", name)


def load_base(path: str) -> Dict[Tuple[int, int], str]:
    # The title record (chapter 0) has no translation and is not aligned.
    return {
        (r["chapter"], r["segment"]): r["response"]["translation"]
        for r in load_records(resolve(path))
        if "translation" in r["response"]
    }


def diff(before: str, after: str) -> List[List]:
    """The edits turning `before` into `after`, as [start, end, replacement].

    Every opcode difflib reports is a replacement of before[i1:i2]: an insert
    has i1 == i2 and a delete has an empty replacement, so the tag carries no
    information and is dropped. autojunk would treat any character occurring in
    over 1% of a long string as noise - which here means the letters the text is
    made of - and produces a much larger delta.
    """
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    return [
        [i1, i2, after[j1:j2]]
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    ]


def patch(before: str, ops: List[List]) -> str:
    out = []
    pos = 0
    for start, end, text in ops:
        out.append(before[pos:start])
        out.append(text)
        pos = end
    out.append(before[pos:])
    return "".join(out)


def pack(source: str, base: str, output: str) -> int:
    records = load_records(source)
    if not records:
        print(f"No records in {source}", file=sys.stderr)
        return 1

    translations = load_base(base)
    if missing := [
        (r["chapter"], r["segment"])
        for r in records
        if (r["chapter"], r["segment"]) not in translations
    ]:
        for chapter, segment in missing:
            print(f"Not in {base}: {chapter}:{segment}", file=sys.stderr)
        return 1

    # A file whose constants are not constant would silently lose them to the
    # header, so this is checked rather than assumed.
    header = {"base": base, "base_sha256": sha256(base)}
    for field in CONSTANT:
        values = {r[field] for r in records}
        if len(values) > 1:
            print(f"{source}: {field} is not constant: {sorted(values)}", file=sys.stderr)
            return 1
        header[field] = values.pop()

    delta = [header]
    for record in records:
        key = (record["chapter"], record["segment"])
        delta.append(
            {
                **{f: record[f] for f in PER_RECORD},
                "ops": diff(translations[key], record["response"]["translation"]),
            }
        )

    # Reversibility is a property of the file on disk, not of the algorithm, so
    # it is established before the file exists: rebuild from the delta in memory
    # and compare against the bytes we were asked to replace.
    rebuilt = render(delta, translations)
    original = open(source, "r", encoding="utf-8").read()
    if rebuilt != original:
        print(f"{source}: delta does not round-trip; nothing written", file=sys.stderr)
        return 1

    save_records(output, delta)
    print(f"{source} -> {output}")
    print(f"  {len(delta) - 1} records, {len(original.encode()):,} -> "
          f"{len(open(output, 'rb').read()):,} bytes, round-trip verified")
    return 0


def render(delta: List[Dict], translations: Dict[Tuple[int, int], str]) -> str:
    header, records = delta[0], delta[1:]
    out = []
    for record in records:
        key = (record["chapter"], record["segment"])
        out.append(
            {
                **{f: record[f] for f in PER_RECORD},
                **{f: header[f] for f in CONSTANT},
                "response": {"translation": patch(translations[key], record["ops"])},
            }
        )
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out)


def unpack(source: str, output: str) -> int:
    delta = load_records(source)
    if not delta:
        print(f"No records in {source}", file=sys.stderr)
        return 1

    header = delta[0]
    base = header["base"]
    actual = sha256(base)
    if actual != header["base_sha256"]:
        # The delta is meaningless against a different base, and the failure is
        # silent corruption rather than an error, so this refuses to guess.
        print(f"{base} has changed since {source} was packed", file=sys.stderr)
        print(f"  expected {header['base_sha256']}\n  actual   {actual}", file=sys.stderr)
        return 1

    translations = load_base(base)
    if missing := [
        (r["chapter"], r["segment"])
        for r in delta[1:]
        if (r["chapter"], r["segment"]) not in translations
    ]:
        for chapter, segment in missing:
            print(f"Not in {base}: {chapter}:{segment}", file=sys.stderr)
        return 1

    text = render(delta, translations)
    with open(output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{source} -> {output} ({len(delta) - 1} records)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pack an aligned JSONL into a delta against its base translation"
    )
    parser.add_argument("command", choices=("pack", "unpack"))
    parser.add_argument("file", help="Aligned JSONL to pack, or delta JSONL to unpack")
    parser.add_argument("-b", "--base",
                        help="Base translation JSONL (default: the parent "
                             "directory plus the input name with the model "
                             "suffix dropped; ignored by unpack, which reads "
                             "the base recorded in the delta)")
    parser.add_argument("-o", "--output",
                        help="Output file (default: .delta.jsonl for pack, the "
                             "name with .delta removed for unpack)")

    args = parser.parse_args()

    if args.command == "pack":
        output = args.output or delta_path(args.file)
        return pack(args.file, args.base or base_path(args.file), output)

    output = args.output or args.file.replace(".delta.jsonl", ".jsonl")
    if output == args.file:
        print("Refusing to unpack over the delta itself; pass -o", file=sys.stderr)
        return 1
    return unpack(args.file, output)


if __name__ == "__main__":
    sys.exit(main())
