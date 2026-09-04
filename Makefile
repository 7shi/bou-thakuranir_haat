MODEL_ := gemini-2.5-pro
MODEL  := google:$(MODEL_)
GEMMA  := google:gemma-4-31b-it

# The aligned translations are stored as deltas and unpacked before conversion
# (see all/aligned/Makefile for the unpack/align/pack rules).
ALIGNED := all/aligned/en-gemini-terra.jsonl all/aligned/ja-gemini-terra.jsonl all/aligned/bn-gemini-terra.jsonl all/aligned/hi-gemini-terra.jsonl

all:

.PHONY: translate convert split questions titles images build clean serve deploy release

build: images
	uv run templates/build.py

images:
	uv run scripts/compress_images.py

clean:
	rm -rf dist

serve:
	cd dist && uv run python -m http.server 8000

deploy: build
	bash templates/deploy.sh

release:
	mkdir -p release
	cd images && git ls-files --others --ignored --exclude-standard | grep -v '^__pycache__/' | zip ../release/images.zip -@

translate:
	uv run scripts/translate_segments.py -f Bengali -t English -m $(MODEL) -o all/en-gemini.jsonl all/bn.md
	uv run scripts/translate_segments.py -f Bengali -t Japanese -m $(MODEL) -o all/ja-gemini.jsonl all/bn.md
	uv run scripts/translate_segments.py -f Bengali -t Hindi -m $(MODEL) -o all/hi-gemini.jsonl all/bn.md
	uv run scripts/translate_segments.py -f "Classical Bengali" -t "Modern Bengali" -m $(MODEL) -o all/bn-gemini.jsonl all/bn.md

convert:
	$(MAKE) -C all/aligned unpack
	uv run scripts/jsonl_to_md.py all/en-gemini.jsonl -a all/aligned/en-gemini-terra.jsonl
	uv run scripts/jsonl_to_md.py all/ja-gemini.jsonl -a all/aligned/ja-gemini-terra.jsonl
	uv run scripts/jsonl_to_md.py all/hi-gemini.jsonl -a all/aligned/hi-gemini-terra.jsonl
	uv run scripts/jsonl_to_md.py all/bn-gemini.jsonl -a all/aligned/bn-gemini-terra.jsonl
	uv run scripts/jsonl_to_md.py --mode full all/en-gemini.jsonl -a all/aligned/en-gemini-terra.jsonl -o all/en-gemini-full.md
	uv run scripts/jsonl_to_md.py --mode full all/ja-gemini.jsonl -a all/aligned/ja-gemini-terra.jsonl -o all/ja-gemini-full.md
	uv run scripts/jsonl_to_md.py --mode full all/hi-gemini.jsonl -a all/aligned/hi-gemini-terra.jsonl -o all/hi-gemini-full.md
	uv run scripts/jsonl_to_md.py --mode summary all/en-gemini.jsonl -o all/en-gemini-summary.md
	uv run scripts/jsonl_to_md.py --mode summary all/ja-gemini.jsonl -o all/ja-gemini-summary.md
	uv run scripts/jsonl_to_md.py --mode summary all/hi-gemini.jsonl -o all/hi-gemini-summary.md
	uv run scripts/jsonl_to_md.py --mode summary all/bn-gemini.jsonl -o all/bn-gemini-summary.md

split:
	uv run scripts/split-line.py -o all/en-gemini-lines.md -l en all/en-gemini.md
	uv run scripts/split-line.py -o all/ja-gemini-lines.md -l ja all/ja-gemini.md

questions:
	uv run scripts/generate_questions.py -o questions-en.jsonl
	uv run scripts/translate_questions.py -i questions-en.jsonl -o questions-ja.jsonl

titles:
	uv run scripts/generate_titles.py all/en-gemini.jsonl -m $(GEMMA)
	uv run scripts/generate_titles.py all/ja-gemini.jsonl -m $(GEMMA) --title-lang Japanese
