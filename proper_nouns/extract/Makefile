MODEL_ := gemini-2.5-pro
MODEL  := google:$(MODEL_)
ROOT   := ../..

.PHONY: proper_nouns

proper_nouns:
	uv run extract.py $(ROOT)/all/bn.md -f Bengali -t English -m $(MODEL) -w en.jsonl -o all.tsv
	uv run translate.py -f Bengali -i English -t Japanese -m $(MODEL) -o all.tsv
	uv run translate.py -f Bengali -i English -t Hindi -m $(MODEL) -o all.tsv
