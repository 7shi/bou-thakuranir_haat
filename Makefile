MODEL_ := gemini-2.5-pro
MODEL  := google:$(MODEL_)

all:

.PHONY: proper_nouns translate convert questions

proper_nouns:
	time uv run proper_nouns/extract.py all-bn.md -f bengali -t english -m $(MODEL) -w proper_nouns/en.jsonl -o proper_nouns/all.tsv
	time uv run proper_nouns/translate.py -f bengali -i english -t japanese -m $(MODEL) -o proper_nouns/all.tsv
	time uv run proper_nouns/translate.py -f bengali -i english -t hindi -m $(MODEL) -o proper_nouns/all.tsv

translate:
	time uv run scripts/translate_segments.py -f bengali -t english -m $(MODEL) -o all-en-gemini.jsonl all-bn.md
	time uv run scripts/translate_segments.py -f bengali -t japanese -m $(MODEL) -o all-ja-gemini.jsonl all-bn.md
	time uv run scripts/translate_segments.py -f bengali -t hindi -m $(MODEL) -o all-hi-gemini.jsonl all-bn.md

convert:
	uv run scripts/jsonl_to_md.py all-en-gemini.jsonl
	uv run scripts/jsonl_to_md.py all-ja-gemini.jsonl
	uv run scripts/jsonl_to_md.py all-hi-gemini.jsonl
	uv run scripts/jsonl_to_md.py --mode full all-en-gemini.jsonl -o all-en-gemini-full.md
	uv run scripts/jsonl_to_md.py --mode full all-ja-gemini.jsonl -o all-ja-gemini-full.md
	uv run scripts/jsonl_to_md.py --mode full all-hi-gemini.jsonl -o all-hi-gemini-full.md
	uv run scripts/jsonl_to_md.py --mode summary all-en-gemini.jsonl -o all-en-gemini-summary.md
	uv run scripts/jsonl_to_md.py --mode summary all-ja-gemini.jsonl -o all-ja-gemini-summary.md
	uv run scripts/jsonl_to_md.py --mode summary all-hi-gemini.jsonl -o all-hi-gemini-summary.md
	uv run scripts/split-line.py -o all-en-gemini-lines.md -l en all-en-gemini.md
	uv run scripts/split-line.py -o all-ja-gemini-lines.md -l ja all-ja-gemini.md

questions:
	uv run scripts/create_rag_questions.py -m $(MODEL_) -c 100 -o questions-en.jsonl all-en-gemini.md -l English
	uv run scripts/create_rag_questions.py -m $(MODEL_) -c 100 -o questions-ja.jsonl all-ja-gemini.md -l Japanese
