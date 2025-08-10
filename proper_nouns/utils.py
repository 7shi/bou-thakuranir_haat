import os
import json
from typing import Dict


def load_existing_proper_nouns(work_file: str) -> Dict[str, str]:
    """Load existing proper nouns from work file to support resume functionality
    
    This function works with both extract.py and translate.py work files:
    - For extract.py: loads from 'proper_nouns' field in each record
    - For translate.py: loads from 'translations' field in each record
    """
    existing_proper_nouns = {}
    
    if os.path.exists(work_file):
        with open(work_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    # Load proper nouns from each segment/batch
                    # Try both field names for compatibility
                    segment_data = data.get("proper_nouns", {}) or data.get("translations", {})
                    existing_proper_nouns.update(segment_data)
    
    return existing_proper_nouns


def save_work_result(
    work_file: str,
    record_data: Dict
) -> None:
    """Save work result to JSONL work file"""
    with open(work_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record_data, ensure_ascii=False) + '\n')


def create_consolidated_dictionary(work_file: str, output_file: str, data_field: str = "proper_nouns") -> str:
    """Create a consolidated dictionary file from work file
    
    Args:
        work_file: Input JSONL work file
        output_file: Output JSON dictionary file
        data_field: Field name to extract from each record ("proper_nouns" or "translations")
    """
    all_data = {}
    
    if os.path.exists(work_file):
        with open(work_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    # Extract data from specified field, fall back to both field names
                    segment_data = data.get(data_field, {})
                    if not segment_data and data_field == "proper_nouns":
                        segment_data = data.get("translations", {})
                    elif not segment_data and data_field == "translations":
                        segment_data = data.get("proper_nouns", {})
                    
                    all_data.update(segment_data)
    
    # Create dictionary file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
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


def save_translation_result(
    work_file: str,
    batch_number: int,
    source_lang: str,
    intermediate_lang: str,
    target_lang: str,
    batch_translations: Dict[str, str]
) -> None:
    """Save translation result to JSONL work file"""
    record = {
        "batch": batch_number,
        "source_lang": source_lang,
        "intermediate_lang": intermediate_lang,
        "target_lang": target_lang,
        "translations": batch_translations
    }
    save_work_result(work_file, record)