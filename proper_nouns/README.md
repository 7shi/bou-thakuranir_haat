# Proper Nouns Extraction and Translation

This directory contains tools for extracting and translating proper nouns from text documents.

## Files

### Scripts

- **`extract.py`** - Extracts proper nouns from source text and translates them to a target language
- **`translate.py`** - Translates proper nouns from TSV files from one language to another using an intermediate language
- **`utils.py`** - Utility functions for data loading, saving, and TSV management

### Data Files

- **`*.jsonl`** - Work files for `extract.py` containing intermediate processing results (JSONL format)
  - Each line contains: `{"chapter": N, "segment": N, "source_lang": "Lang", "target_lang": "Lang", "proper_nouns": {...}}`
  - Used for resume functionality - allows skipping already processed segments
  - Only used by `extract.py` - `translate.py` works directly with TSV files
  - Examples: `en.jsonl` (for extraction work)

- **`all.tsv`** - Consolidated TSV file containing all proper nouns across languages
  - Tab-separated values with source language as first column
  - Header row contains language names in Title Case (e.g., `Bengali	English	Japanese`)
  - Updated directly by both scripts - no intermediate work files needed for `translate.py`

## Usage

### Extracting Proper Nouns

```bash
uv run proper_nouns/extract.py SOURCE.md -f SOURCE_LANG -t TARGET_LANG -m MODEL -w WORK.jsonl -o OUTPUT.tsv
```

- `SOURCE.md` - Source markdown file to analyze
- `-f/--from_lang` - Source language (e.g., bengali, english)
- `-t/--to_lang` - Target language (e.g., english, japanese)
- `-m/--model` - LLM model to use (e.g., `openai:gpt-4o-mini`)
- `-w/--work-file` - Work file for intermediate results (required)
- `-o/--output` - Output TSV file (required)

**Optional parameters:**
- `--segmentation` - Segmentation JSONL file (default: `segmentations.jsonl`)
- `--limit` - Limit number of chapters to process

### Translating Proper Nouns Dictionary

```bash
uv run proper_nouns/translate.py [INPUT.tsv] -f SOURCE_LANG -i INTERMEDIATE_LANG -t TARGET_LANG -m MODEL -o OUTPUT.tsv
```

- `INPUT.tsv` - Input TSV file (optional, defaults to OUTPUT.tsv if omitted)
- `-f/--from_lang` - Source language (extracted from TSV data)
- `-i/--intermediate-lang` - Intermediate language (extracted from TSV data)
- `-t/--to_lang` - Target language
- `-m/--model` - LLM model to use
- `-o/--output` - Output TSV file (required)

**Optional parameters:**
- `--batch-size` - Number of proper nouns per batch (default: 30)
- `--limit` - Limit number of API calls

## Features

### Resume Functionality

**`extract.py`**:
- Successfully processed segments are recorded in JSONL work files
- Failed extractions are not marked as processed (allowing retry)
- Empty results are marked as processed (preventing re-processing)
- Re-running the same command will skip already processed segments

**`translate.py`**:
- Checks existing TSV data to skip already translated terms
- No intermediate work files needed - resumes by reading TSV directly
- Failed translations are not saved, allowing retry on next run
- Each successful batch immediately updates the TSV file

### TSV Integration

- TSV files are automatically updated with existing data
- Language names are normalized to Title Case (Bengali, English, Japanese)
- Source language appears as the first column
- `translate.py` updates TSV files directly without intermediate files

### Error Handling

**`extract.py`**:
- Extraction failures are not saved to work files (allowing retry)
- Empty results are saved to work files (preventing unnecessary re-processing)
- Work files track chapter and segment information for precise resume capability

**`translate.py`**:
- Translation failures are not saved to TSV (allowing retry)
- Successful translations are immediately written to TSV
- Batch-level error recovery - failed batches don't affect successful ones

## Example Workflow

The `translate.py` script now works directly with TSV files for streamlined processing:

1. **Extract Bengali → English proper nouns (creates initial TSV):**
   ```bash
   uv run proper_nouns/extract.py all-bn.md -f bengali -t english -m google:gemini-2.5-pro -w proper_nouns/en.jsonl -o proper_nouns/all.tsv
   ```

2. **Add Japanese translations to existing TSV:**
   ```bash
   uv run proper_nouns/translate.py -f bengali -i english -t japanese -m google:gemini-2.5-pro -o proper_nouns/all.tsv
   ```

3. **Add another language (e.g., Chinese):**
   ```bash
   uv run proper_nouns/translate.py -f bengali -i english -t chinese -m google:gemini-2.5-pro -o proper_nouns/all.tsv
   ```

4. **Resume processing after interruption:**
   ```bash
   # Re-run the same command - will skip completed segments
   uv run proper_nouns/extract.py all-bn.md -f bengali -t english -m google:gemini-2.5-pro -w proper_nouns/en.jsonl -o proper_nouns/all.tsv
   ```

**Key features:**
- Input TSV file is optional for `translate.py` - if omitted, reads from output TSV file
- Automatically extracts source and intermediate language data from TSV
- Updates the same TSV file with new target language translations directly
- Language columns are automatically managed and normalized to Title Case
- `extract.py` uses JSONL work files for chapter/segment-level resume
- `translate.py` uses TSV-based resume (no intermediate files needed)
- Each translation batch immediately updates the TSV for real-time progress

The final `proper_nouns/all.tsv` will contain proper nouns in all processed languages with proper normalization and consolidation.
