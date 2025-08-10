import os
import json
import argparse
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from llm7shi.compat import generate_with_schema
from llm7shi import create_json_descriptions_prompt
import sys
import os

from utils import (
    load_work_data,
    load_existing_proper_nouns,
    create_consolidated_tsv,
    save_extraction_result
)

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from scripts.utils import load_chapter_blocks


class ProperNounsExtraction(BaseModel):
    """Proper nouns extracted from a text segment"""
    proper_nouns: List[str] = Field(
        description="List of proper nouns discovered in this segment in the SOURCE language (as they appear in the original text)"
    )
    proper_noun_translations: List[str] = Field(
        description="Corresponding translations/transliterations for the proper nouns listed above (in the same order, in the TARGET language)"
    )


def create_proper_nouns_context(accumulated_proper_nouns: Dict[str, str], source_lang: str, target_lang: str) -> str:
    """Create context string showing already extracted proper nouns"""
    if not accumulated_proper_nouns:
        return ""
    
    context_parts = [f"[Already Extracted Proper Nouns ({source_lang} -> {target_lang})]"]
    for source_noun, target_noun in accumulated_proper_nouns.items():
        context_parts.append(f"{source_noun} → {target_noun}")
    context_parts.append("")
    
    return "\n".join(context_parts)


def extract_proper_nouns_from_segment(
    segment_text: str,
    accumulated_proper_nouns: Dict[str, str],
    source_lang: str,
    target_lang: str,
    model: str,
    show_params: bool
) -> Optional[Dict]:
    """Extract proper nouns from a single segment"""
    
    context = create_proper_nouns_context(accumulated_proper_nouns, source_lang, target_lang)
    
    prompt = f"""Please extract all proper nouns from the following {source_lang} text segment and provide their {target_lang} translations/transliterations.

{context}[{source_lang.title()} Text to Analyze]
{segment_text}

[Extraction Instructions]
1. Identify ALL proper nouns in the text (names of people, places, organizations, etc.)
2. Extract the BASE FORM of proper nouns only (do not include possessive forms, grammatical suffixes, or declined forms)
3. Only extract proper nouns that are NOT already in the dictionary above
4. Provide appropriate translations/transliterations for each proper noun
5. For names: use standard romanization/transliteration conventions
6. For places: use commonly accepted English names where they exist
7. Maintain consistency with the existing proper nouns dictionary

Examples:
- Extract "যশোহর" not "যশোহরের" (possessive form)
- Extract "প্রতাপাদিত্য" not "প্রতাপাদিত্যের" (possessive form)
- Extract base forms without grammatical suffixes"""

    json_descriptions = create_json_descriptions_prompt(ProperNounsExtraction)
    
    try:
        result = generate_with_schema(
            [prompt, json_descriptions],
            schema=ProperNounsExtraction,
            model=model,
            show_params=show_params,
        )
        
        if result and hasattr(result, 'text'):
            try:
                extraction_data = json.loads(result.text)
                return extraction_data
            except json.JSONDecodeError as e:
                print(f"  DEBUG: Failed to parse JSON: {e}")
                return None
        else:
            print(f"  DEBUG: No result.text found")
            return None
    except Exception as e:
        print(f"Error extracting proper nouns from segment: {e}")
        return None


def process_proper_nouns_from_result(extraction_result: Dict) -> Dict[str, str]:
    """Convert list-based proper nouns result to dictionary format (source -> target)"""
    proper_nouns_dict = {}
    source_nouns = extraction_result.get("proper_nouns", [])
    target_nouns = extraction_result.get("proper_noun_translations", [])
    
    # Pair up source and target nouns (handle mismatched lengths gracefully)
    for i in range(min(len(source_nouns), len(target_nouns))):
        if source_nouns[i].strip() and target_nouns[i].strip():
            proper_nouns_dict[source_nouns[i].strip()] = target_nouns[i].strip()
    
    return proper_nouns_dict




def main():
    parser = argparse.ArgumentParser(description='Extract proper nouns from text segments with consistency')
    parser.add_argument('source_md', help='Source markdown file to analyze')
    parser.add_argument('-f', '--from_lang', required=True, 
                       help='Source language (e.g., bengali, english, japanese)')
    parser.add_argument('-t', '--to_lang', required=True,
                       help='Target language (e.g., english, japanese, bengali)')
    parser.add_argument('-m', '--model', required=True,
                       help='LLM model to use (e.g., openai:gpt-4o-mini, anthropic:claude-3-haiku-20240307)')
    parser.add_argument('-w', '--work-file', required=True,
                       help='Work file (JSONL) for intermediate results')
    parser.add_argument('-o', '--output', required=True,
                       help='Output TSV file for final proper nouns dictionary')
    parser.add_argument('--segmentation', default='segmentations.jsonl',
                       help='Segmentation JSONL file (default: segmentations.jsonl)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of chapters to process (for debugging)')
    
    args = parser.parse_args()
    
    try:
        # Use specified work file
        work_file = args.work_file
        
        # Load segments from markdown and segmentation data
        print(f"Loading segments from {args.source_md} using {args.segmentation}")
        data = load_chapter_blocks(args.segmentation, args.source_md)
        title = data["title"]
        chapter_blocks = data["chapters"]
        
        # Load existing work data for resume capability
        work_data = load_work_data(work_file)
        existing_proper_nouns = load_existing_proper_nouns(work_file)
        
        # Initialize accumulated proper nouns
        accumulated_proper_nouns = existing_proper_nouns.copy()
        
        # Apply chapter limit if specified
        if args.limit:
            chapter_blocks = chapter_blocks[:args.limit]
            print(f"Processing limited to {args.limit} chapters")
        
        print(f"Title: {title}")
        print(f"Extracting proper nouns: {args.from_lang} -> {args.to_lang}")
        print(f"Total chapters: {len(chapter_blocks)}")
        print(f"Already extracted proper nouns: {len(accumulated_proper_nouns)}")
        print("=" * 60)
        
        total_segments = sum(len(chapter) for chapter in chapter_blocks)
        processed_segments = 0
        new_proper_nouns_found = 0
        
        for chapter_num, segments in enumerate(chapter_blocks, 1):
            print(f"Chapter {chapter_num:2d}: {len(segments)} segments")
            
            for segment_num, segment_text in enumerate(segments, 1):
                processed_segments += 1
                
                # Skip if this segment is already processed
                if chapter_num in work_data and segment_num in work_data[chapter_num]:
                    print(f"  Segment {segment_num} → skipped (already processed)")
                    continue
                
                print(f"  Segment {segment_num} → extracting...", end="")
                
                # Extract proper nouns from segment
                extraction_result = extract_proper_nouns_from_segment(
                    segment_text,
                    accumulated_proper_nouns,
                    args.from_lang,
                    args.to_lang,
                    args.model,
                    bool(args.limit)
                )
                
                if extraction_result:
                    # Update accumulated proper nouns
                    new_proper_nouns = process_proper_nouns_from_result(extraction_result)
                    
                    if new_proper_nouns:
                        accumulated_proper_nouns.update(new_proper_nouns)
                        new_proper_nouns_found += len(new_proper_nouns)
                        print(f" completed ({len(new_proper_nouns)} new)")
                        
                        # Show new proper nouns found
                        for source, target in new_proper_nouns.items():
                            print(f"    {source} → {target}")
                    else:
                        print(" completed (no new proper nouns)")
                    
                    # Save result to mark segment as processed (success or no results)
                    save_extraction_result(
                        work_file,
                        chapter_num,
                        segment_num,
                        args.from_lang,
                        args.to_lang,
                        new_proper_nouns
                    )
                else:
                    print(" failed")
                    # Don't save failed extractions - allow retry on next run
                
                # Progress indicator
                if processed_segments % 10 == 0:
                    print(f"  Progress: {processed_segments}/{total_segments} segments")
        
        # Create consolidated TSV output
        work_files = {args.to_lang: work_file}
        create_consolidated_tsv(work_files, args.output, args.from_lang)
        
        print(f"\nProper nouns extraction completed!")
        print(f"Working data saved to: {work_file}")
        print(f"Final dictionary saved to: {args.output}")
        print(f"Total proper nouns found: {len(accumulated_proper_nouns)}")
        print(f"New proper nouns in this run: {new_proper_nouns_found}")
        
        # Display final dictionary
        if accumulated_proper_nouns:
            print(f"\nFinal Proper Nouns Dictionary ({args.from_lang} -> {args.to_lang}):")
            for source, target in sorted(accumulated_proper_nouns.items()):
                print(f"  {source} → {target}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
