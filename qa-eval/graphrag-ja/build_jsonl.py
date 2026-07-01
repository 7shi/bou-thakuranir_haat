#!/usr/bin/env python
# /// script
# dependencies = [
#   "fastparquet>=2026.5.0",
#   "pandas>=3.0.3",
#   "pyarrow>=24.0.0",
# ]
# ///
"""graphrag/{local,global}/NN.txt の回答に埋め込まれた [Data: ...] 引用タグを
章番号へマッピングし、results-ja/graphrag-{local,global}.jsonl を生成する。

引用タグの ID は GraphRAG の context テーブルの id 列 = parquet の human_readable_id:
    Sources (N)       -> text_units.human_readable_id == N
    Entities (N)      -> entities.human_readable_id == N        (.text_unit_ids)
    Relationships (N) -> relationships.human_readable_id == N   (.text_unit_ids)
    Reports (N)       -> communities.community == N             (.text_unit_ids)

text_unit -> 章 は、元文書中の "## Chapter N" 見出し位置と、各 text_unit テキストの
出現位置 (char offset) の重なりで決定する。
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
RESULTS = ROOT / ".." / "results-ja"
DOC = (ROOT / "input" / "ja-gemini.txt").read_text(encoding="utf-8")

# --- 章境界 (開始 char offset) ---
CHAPTERS = [(int(m.group(1)), m.start()) for m in re.finditer(r"^## Chapter (\d+)", DOC, re.M)]


def chapters_for_text(text: str) -> set[int]:
    """text_unit のテキストが元文書中で重なる章番号の集合を返す。"""
    pos = DOC.find(text[:80])
    if pos < 0:
        pos = DOC.find(text[50:130])
    if pos < 0:
        return set()
    end = pos + len(text)
    out = set()
    for i, (c, off) in enumerate(CHAPTERS):
        nxt = CHAPTERS[i + 1][1] if i + 1 < len(CHAPTERS) else len(DOC)
        if off < end and nxt > pos:
            out.add(c)
    return out


# --- ルックアップ構築 ---
text_units = pd.read_parquet(OUTPUT / "text_units.parquet")
entities = pd.read_parquet(OUTPUT / "entities.parquet")
relationships = pd.read_parquet(OUTPUT / "relationships.parquet")
communities = pd.read_parquet(OUTPUT / "communities.parquet")

tu_id_to_chapters: dict[str, set[int]] = {}
tu_hrid_to_chapters: dict[int, set[int]] = {}
for _, r in text_units.iterrows():
    chs = chapters_for_text(r["text"])
    tu_id_to_chapters[r["id"]] = chs
    tu_hrid_to_chapters[int(r["human_readable_id"])] = chs


def chapters_from_text_unit_ids(ids) -> set[int]:
    out: set[int] = set()
    if ids is None:
        return out
    for tid in ids:
        out |= tu_id_to_chapters.get(tid, set())
    return out


entity_hrid_to_chapters = {
    int(r["human_readable_id"]): chapters_from_text_unit_ids(r["text_unit_ids"])
    for _, r in entities.iterrows()
}
rel_hrid_to_chapters = {
    int(r["human_readable_id"]): chapters_from_text_unit_ids(r["text_unit_ids"])
    for _, r in relationships.iterrows()
}
community_to_chapters = {
    int(r["community"]): chapters_from_text_unit_ids(r["text_unit_ids"])
    for _, r in communities.iterrows()
}

TYPE_LOOKUP = {
    "Sources": lambda n: tu_hrid_to_chapters.get(n, set()),
    "Entities": lambda n: entity_hrid_to_chapters.get(n, set()),
    "Relationships": lambda n: rel_hrid_to_chapters.get(n, set()),
    "Reports": lambda n: community_to_chapters.get(n, set()),
}

# --- [Data: ...] パーサ ---
DATA_BLOCK = re.compile(r"\[Data:([^\]]*)\]")
TYPE_MARKER = re.compile(r"(Sources|Entities|Relationships|Reports)\s*\(")


def strip_tags(answer: str) -> str:
    """回答本文から [Data: ...] 引用タグを除去する。タグ直前の空白も取り除く。"""
    text = re.sub(r"[ \t]*\[Data:[^\]]*\]", "", answer)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_chapters(answer: str) -> list[str]:
    chs: set[int] = set()
    for block in DATA_BLOCK.findall(answer):
        markers = list(TYPE_MARKER.finditer(block))
        for i, m in enumerate(markers):
            typ = m.group(1)
            seg_end = markers[i + 1].start() if i + 1 < len(markers) else len(block)
            segment = block[m.end():seg_end]
            fn = TYPE_LOOKUP[typ]
            for num in re.findall(r"\d+", segment):
                chs |= fn(int(num))
    return [str(c) for c in sorted(chs)]


def build(method: str) -> None:
    src_dir = ROOT / method
    out_path = RESULTS / f"graphrag-{method}.jsonl"
    rows = []
    for txt in sorted(src_dir.glob("*.txt")):
        qid = int(txt.stem)
        answer = txt.read_text(encoding="utf-8").strip()
        rows.append(
            {
                "question_id": qid,
                "expanded": parse_chapters(answer),
                "answer": strip_tags(answer),
            }
        )
    rows.sort(key=lambda r: r["question_id"])
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    empties = sum(1 for r in rows if not r["expanded"])
    print(f"{method}: {len(rows)} 件 -> {out_path}  (expanded 空: {empties})")


if __name__ == "__main__":
    build("local")
    build("global")
