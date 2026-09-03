import os
import json
from typing import Dict


def load_work_data(work_file: str) -> Dict[int, Dict[int, Dict[str, str]]]:
    """Load work data from JSONL file organized by chapter and segment
    
    Returns:
        Dict[chapter, Dict[segment, Dict[source_term, target_term]]]
    """
    work_data = {}
    
    if os.path.exists(work_file):
        with open(work_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    chapter = data.get("chapter")
                    segment = data.get("segment")
                    
                    # Extract proper_nouns field only (extract.py format)
                    segment_data = data.get("proper_nouns", {})
                    
                    # Record all processed segments, even if no proper nouns were found
                    if chapter is not None and segment is not None:
                        if chapter not in work_data:
                            work_data[chapter] = {}
                        work_data[chapter][segment] = segment_data
    
    return work_data


def load_existing_proper_nouns(work_file: str) -> Dict[str, str]:
    """Load existing proper nouns from work file to support resume functionality
    
    This function works with extract.py work files:
    - For extract.py: loads from 'proper_nouns' field in each record
    """
    work_data = load_work_data(work_file)
    existing_proper_nouns = {}
    
    for chapter_data in work_data.values():
        for segment_data in chapter_data.values():
            existing_proper_nouns.update(segment_data)
    
    return existing_proper_nouns


def save_work_result(
    work_file: str,
    record_data: Dict
) -> None:
    """Save work result to JSONL work file"""
    with open(work_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record_data, ensure_ascii=False) + '\n')



def load_existing_tsv(tsv_file: str) -> Dict[str, Dict[str, str]]:
    """Load existing TSV file data
    
    Returns:
        Dict[source_term, Dict[language, translation]]
    """
    existing_data = {}
    lang_codes = []
    
    if os.path.exists(tsv_file):
        with open(tsv_file, 'r', encoding='utf-8') as f:
            # Read header
            first_line = f.readline().strip()
            if first_line:
                lang_codes = first_line.split('\t')
                # Normalize language codes to title case for consistency
                lang_codes = [code.title() for code in lang_codes]
                
                # Read data rows
                for line in f:
                    if line.strip():
                        values = line.strip().split('\t')
                        if len(values) >= len(lang_codes) and values[0]:  # Ensure we have source term
                            source_term = values[0]
                            existing_data[source_term] = {}
                            
                            for i, lang_code in enumerate(lang_codes):
                                if i < len(values) and values[i]:
                                    existing_data[source_term][lang_code] = values[i]
    
    return existing_data


def create_consolidated_tsv(work_files: Dict[str, str], output_file: str, source_lang: str) -> str:
    """Create a consolidated TSV file from multiple work files, merging with existing TSV data
    
    Args:
        work_files: Dictionary mapping language codes to work file paths
        output_file: Output TSV file path
        source_lang: Source language code (used as the key)
    """
    # Load existing TSV data
    existing_data = load_existing_tsv(output_file)
    
    # Collect new data from work files
    new_translations = {}
    
    for lang_code, work_file in work_files.items():
        # Normalize language code to title case
        normalized_lang_code = lang_code.title()
        
        if os.path.exists(work_file):
            with open(work_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Extract data from proper_nouns field only (extract.py format)
                        segment_data = data.get("proper_nouns", {})
                        
                        # Merge translations by source term
                        for source_term, target_term in segment_data.items():
                            if source_term not in new_translations:
                                new_translations[source_term] = {}
                            new_translations[source_term][normalized_lang_code] = target_term
    
    # Merge existing and new data
    all_translations = existing_data.copy()
    for source_term, translations in new_translations.items():
        if source_term not in all_translations:
            all_translations[source_term] = {}
        all_translations[source_term].update(translations)
    
    # Get all language codes and sort them (source language first, then target languages)
    all_lang_codes = set()
    for translations in all_translations.values():
        all_lang_codes.update(translations.keys())
    
    # Normalize source language to title case
    source_lang_normalized = source_lang.title()
    
    # Always include source language first, then sorted target languages
    lang_codes = [source_lang_normalized]
    target_lang_codes = sorted([code for code in all_lang_codes if code != source_lang_normalized])
    lang_codes.extend(target_lang_codes)
    
    # Create TSV file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header (already normalized to title case)
        f.write('\t'.join(lang_codes) + '\n')
        
        # Write data rows
        for source_term in sorted(all_translations.keys()):
            row_data = []
            for lang_code in lang_codes:
                if lang_code == source_lang_normalized:
                    # For source language, use the source term itself
                    row_data.append(source_term)
                else:
                    # For target languages, use the translation
                    translation = all_translations[source_term].get(lang_code, '')
                    row_data.append(translation)
            f.write('\t'.join(row_data) + '\n')
    
    return output_file


def save_extraction_result(
    work_file: str,
    chapter: int,
    segment: int,
    source_lang: str,
    target_lang: str,
    proper_nouns_dict: Dict[str, str]
) -> None:
    """Save proper nouns extraction result to JSONL work file"""
    record = {
        "chapter": chapter,
        "segment": segment,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "proper_nouns": proper_nouns_dict
    }
    save_work_result(work_file, record)


