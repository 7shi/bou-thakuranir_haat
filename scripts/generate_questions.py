"""
Generate a non-duplicating, detail-oriented RAG evaluation question set.

Unlike the old ``create_rag_questions.py`` (memoryless batches of 10 that kept
gravitating to the same salient events), this generator runs **two separate
multi-turn sessions** over a single uploaded copy of the full English text:

  * a *single-passage* session — each question answerable only by close reading
    of ONE scene (a specific line, object, number, gesture, reaction);
  * a *cross-reference* session — each question requiring synthesis of 2-3
    separated chapters (command<->execution, foreshadow<->payoff, consistency).

Within a session the Gemini-native ``contents`` list is managed by hand: the
uploaded file first, then each turn's user prompt followed by the model's reply
appended as a ``model``-role turn, so every new turn can see the questions
already produced and avoid overlap / fill chapter-coverage gaps.

Each session produces ``turns * per_turn`` questions (default 5 * 5 = 25), for a
combined 50 written to ``questions-en.jsonl``. Records carry ``anchor_id`` (1-based,
matching the line number; single first then cross) and ``type`` ("single" | "cross")
in addition to the
``RagQuestion`` fields, so the set is resumable and the JA translation stays
parallel by ``anchor_id``.

Resumable: completed turns are replayed into ``contents`` (prompt + reconstructed
model reply) from the records already in the output, and generation continues from
the first unfinished turn.

Gemini-billed: needs ``GEMINI_API_KEY`` in the environment. Run via ``uv``, e.g.

    GEMINI_API_KEY=... uv run scripts/generate_questions.py
"""
import argparse
import json
import mimetypes
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field
from google.genai import types
from llm7shi import config_from_schema, generate_content_retry, upload_file, delete_file

ROOT = Path(__file__).resolve().parent.parent

SCHEMA_FIELDS = ("question", "answer", "chapters", "rationale")


# --- Schema (mirrors create_rag_questions.RagQuestion) ---

class RagQuestion(BaseModel):
    """A single question, its answer, the supporting chapters, and the rationale."""
    question: str = Field(..., description="A specific, detail-oriented question about the story.")
    answer: str = Field(..., description="A concise and accurate answer to the question.")
    chapters: List[int] = Field(..., description="The chapter numbers where the evidence is found.")
    rationale: str = Field(..., description="The justification for the answer, citing the source text.")


class RagQuestionSet(BaseModel):
    """A batch of questions produced in one turn."""
    questions: List[RagQuestion] = Field(..., description="The questions generated this turn.")


# --- Prompts ---

INTRO = {
    "single": """\
You are building a RAG (Retrieval-Augmented Generation) evaluation set from the \
attached novel (the full English text). Across this whole session you will produce \
SINGLE-PASSAGE detail questions.

Each question MUST:
- be answerable only by close reading of ONE specific scene/passage;
- hinge on a concrete, nitpicky detail (a specific line, object, number, name, \
gesture, or a character's immediate reaction), NOT on broad plot or themes;
- never be a plot summary and never be answerable by general recall of the story;
- cite the single chapter it comes from in `chapters`.""",
    "cross": """\
You are building a RAG (Retrieval-Augmented Generation) evaluation set from the \
attached novel (the full English text). Across this whole session you will produce \
CROSS-REFERENCE questions.

Each question MUST:
- require synthesizing 2-3 SEPARATED chapters (e.g. a command and its later \
execution, a foreshadowing and its payoff, or a consistency check across scenes);
- NOT be answerable from any single scene in isolation;
- still depend on concrete details rather than vague themes;
- cite all the chapters whose evidence is needed in `chapters`.""",
}


def build_turn_prompt(sess_type: str, turn_idx: int, per_turn: int) -> str:
    """Deterministic per-turn prompt (must be reproducible for resume/replay)."""
    if turn_idx == 0:
        head = INTRO[sess_type]
    else:
        head = (
            "Continue the same RAG question set from the attached novel. "
            "Review the questions you have already produced in this conversation."
        )
    return (
        f"{head}\n\n"
        f"Now generate exactly {per_turn} new questions.\n"
        "- Do NOT overlap or duplicate any question already produced in this conversation "
        "(different event AND different expected answer).\n"
        "- Prefer chapters/scenes you have not used yet to spread coverage across the whole book.\n"
        "- For each question give a concise answer, the supporting `chapters`, and a `rationale` "
        "that quotes or pinpoints the exact evidence.\n"
        "Return only the structured JSON for this turn."
    )


# --- IO helpers ---

def load_existing(output_path: Path) -> List[dict]:
    records = []
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records


def append_record(output_path: Path, record: dict) -> None:
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def model_turn(questions: List[dict]) -> types.Content:
    """Reconstruct a model-role turn from saved questions (schema fields only)."""
    payload = {"questions": [{k: q[k] for k in SCHEMA_FIELDS} for q in questions]}
    return types.Content(role="model", parts=[types.Part(text=json.dumps(payload, ensure_ascii=False))])


# --- Session ---

def generate_session(file, sess_type: str, anchor_offset: int, turns: int,
                     per_turn: int, model: str, output_path: Path) -> None:
    config = config_from_schema(RagQuestionSet)

    done = [r for r in load_existing(output_path) if r.get("type") == sess_type]
    completed_turns = len(done) // per_turn
    saved = len(done)

    contents: list = [file]
    # Replay completed turns so the model keeps its memory of prior questions.
    for t in range(completed_turns):
        contents.append(build_turn_prompt(sess_type, t, per_turn))
        contents.append(model_turn(done[t * per_turn:(t + 1) * per_turn]))

    if completed_turns:
        print(f"[{sess_type}] resuming: {saved} question(s) / {completed_turns} turn(s) done")

    for t in range(completed_turns, turns):
        contents.append(build_turn_prompt(sess_type, t, per_turn))
        response = generate_content_retry(contents, model=model, config=config, show_params=False)
        questions = json.loads(response.text)["questions"]
        contents.append(types.Content(role="model", parts=[types.Part(text=response.text)]))
        for q in questions:
            record = {"anchor_id": anchor_offset + saved, "type": sess_type}
            record.update({k: q[k] for k in SCHEMA_FIELDS})
            append_record(output_path, record)
            saved += 1
        print(f"[{sess_type}] turn {t + 1}/{turns}: +{len(questions)} (total {saved})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input", type=Path, default=ROOT / "all" / "en-gemini.md",
                        help="English full-text Markdown to upload once.")
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "questions-en.jsonl",
                        help="Output questions JSONL (appended / resumed).")
    parser.add_argument("-m", "--model", default="gemini-3.1-pro-preview",
                        help="Gemini model for generation.")
    parser.add_argument("--turns", type=int, default=5, help="Turns per session.")
    parser.add_argument("--per-turn", type=int, default=5, help="Questions per turn.")
    parser.add_argument("--only", choices=["single", "cross"], default=None,
                        help="Run only one session type (default: both).")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file '{args.input}' not found.")
        return 1

    per_session = args.turns * args.per_turn
    sessions = [("single", 1), ("cross", per_session + 1)]
    if args.only:
        sessions = [s for s in sessions if s[0] == args.only]

    args.output.parent.mkdir(parents=True, exist_ok=True)

    file = None
    try:
        mimetype, _ = mimetypes.guess_type(args.input)
        file = upload_file(args.input, mimetype or "text/markdown")
        for sess_type, anchor_offset in sessions:
            generate_session(file, sess_type, anchor_offset, args.turns,
                             args.per_turn, args.model, args.output)
    finally:
        if file:
            delete_file(file)

    total = len(load_existing(args.output))
    print(f"\nDone. {total} question(s) in {args.output}")
    return 0


if __name__ == "__main__":
    exit(main())
