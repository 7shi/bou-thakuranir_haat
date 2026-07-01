#!/usr/bin/env bash
# Run all questions in QUESTIONS through GraphRAG local / global and
# save each answer body to {local,global}/NN.txt.
#
# Prerequisites:
#   - output/ must contain indexed artifacts
#   - the same env vars used during indexing must be set (e.g. OLLAMA_HOST)
#       export OLLAMA_HOST=localhost   # enable if needed
#   - settings.yaml uses concurrent_requests: 1, so execution is serial and slow
#
# Usage:
#   bash run_queries.sh            # all questions
#   bash run_queries.sh 1          # dry-run with anchor_id=1 only
#
# Resume: skips a question if the output file already exists and is non-empty.
#
# rawlog: each query gets its own subdirectory for later inspection.
#   rawlogs/3-query/{local,global}-NN/00001.xml ...
#   graphrag chdirs to the root specified by -r, so GRAPHRAG_RAWLOG_DIR must be
#   an absolute path (relative paths cause double-creation under root).

set -uo pipefail

# Change to the directory containing this script
cd "$(dirname "$0")" || exit 1

ROOT="."
QUESTIONS="$ROOT/../../questions-ja.jsonl"
ONLY="${1:-}"   # if set, run only that anchor_id

# Parent directory for rawlogs (absolute path)
RAWLOG_BASE="$PWD/$ROOT/rawlogs/3-query"

mkdir -p "$ROOT/local" "$ROOT/global" "$ROOT/logs"

run_one() {
  local method="$1" id="$2" question="$3"
  local nn out log rawlog
  nn=$(printf '%02d' "$id")
  out="$ROOT/$method/$nn.txt"
  log="$ROOT/logs/query-$method-$nn.log"
  rawlog="$RAWLOG_BASE/$method-$nn"

  if [[ -s "$out" ]]; then
    echo "  skip   $method/$nn.txt (exists)"
    return
  fi

  echo "  run    $method/$nn.txt"
  # Recreate the rawlog directory to avoid mixing with previous runs.
  rm -rf "$rawlog"
  mkdir -p "$rawlog"
  # graphrag query writes the answer body directly to stdout (status to stderr).
  # Save stdout as-is and redirect stderr to a separate log file.
  # Use per-query rawlog directories with absolute paths.
  GRAPHRAG_RAWLOG_DIR="$rawlog" \
    graphrag query -r "$ROOT" -m "$method" "$question" > "$out" 2> "$log"

  if [[ ! -s "$out" ]]; then
    echo "  WARN   $method/$nn.txt: empty output. Check $log"
  fi
}

while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  id=$(jq -r '.anchor_id' <<< "$line")
  question=$(jq -r '.question' <<< "$line")

  if [[ -n "$ONLY" && "$id" != "$ONLY" ]]; then
    continue
  fi

  echo "[$id] $question"
  run_one local  "$id" "$question"
  run_one global "$id" "$question"
done < "$QUESTIONS"

echo "done."
