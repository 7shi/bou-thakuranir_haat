TEXT = input/ja-gemini.txt

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  init  Run init, prompt-tune and index"
	@echo "  run   Run queries"

init:
	graphrag init -m gemma4:31b-it-qat -e embeddinggemma
	ln -sf ../../../all/ja-gemini.md $(TEXT)
	cp settings-1.yaml settings.yaml
	GRAPHRAG_RAWLOG_DIR=rawlogs/1-tune  graphrag prompt-tune --language Japanese
	GRAPHRAG_RAWLOG_DIR=rawlogs/2-index graphrag index

run:
	cp settings-2.yaml settings.yaml
	sh run_queries.sh
	uv run build_jsonl.py

clean:
	rm -rf `cat .gitignore`

.PHONY: help init run clean
