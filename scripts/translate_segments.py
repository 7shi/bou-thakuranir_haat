import os
import json
import argparse
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from llm7shi.compat import generate_with_schema
from llm7shi import create_json_descriptions_prompt
from utils import load_chapter_blocks


class SegmentTranslation(BaseModel):
    """Complete translation result for a text segment"""
    summary: str = Field(
        description="Brief summary of this segment's content in the target language"
    )
    translation_notes: str = Field(
        description="Translation breakdown and notes - explain key translation choices, difficult phrases, cultural adaptations, or linguistic considerations"
    )
    translation: str = Field(
        description="Complete translation of the segment text into the target language"
    )


class TitleTranslation(BaseModel):
    """Translation result for the title"""
    reasoning: str = Field(
        description="Explanation of why this translation was chosen, considering story context, themes, and proper nouns"
    )
    translated_title: str = Field(
        description="Translation of the title into the target language, considering the full story context"
    )


def load_proper_nouns_dictionary(dict_file: str) -> Dict[str, str]:
    """Load proper nouns dictionary from JSON file"""
    if not os.path.exists(dict_file):
        return {}
    
    with open(dict_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_translation_context(
    proper_nouns_dict: Dict[str, str], 
    previous_summaries: List[str], 
    source_lang: str, 
    target_lang: str
) -> str:
    """Create context string for translation including proper nouns dictionary and story summary"""
    context_parts = []
    
    if proper_nouns_dict:
        context_parts.append(f"[Proper Nouns Dictionary ({source_lang} -> {target_lang})]")
        for source_noun, target_noun in proper_nouns_dict.items():
            context_parts.append(f"{source_noun}: {target_noun}")
        context_parts.append("")
    
    if previous_summaries:
        context_parts.append(f"[Previous Story Context in {target_lang}]")
        context_parts.extend(previous_summaries)
        context_parts.append("")
    
    return "\n".join(context_parts)




def translate_segment(
    segment_text: str,
    proper_nouns_dict: Dict[str, str],
    previous_summaries: List[str],
    source_lang: str,
    target_lang: str,
    model: str
) -> Optional[Dict]:
    """Translate a single segment with proper noun consistency and story context"""
    
    context = create_translation_context(
        proper_nouns_dict, 
        previous_summaries, 
        source_lang, 
        target_lang
    )
    
    prompt = f"""Please translate the following {source_lang} text segment into {target_lang}.

{context}[{source_lang.title()} Text to Translate]
{segment_text}

[Translation Instructions]
1. Maintain consistency with the proper nouns dictionary above - use the exact same transliterations
2. Consider the story context from previous segments to ensure narrative continuity
3. Ensure the translation flows naturally and maintains the original meaning
4. Provide translation notes explaining key choices and cultural context"""

    json_descriptions = create_json_descriptions_prompt(SegmentTranslation)
    
    try:
        result = generate_with_schema(
            [prompt, json_descriptions],
            schema=SegmentTranslation,
            model=model,
            show_params=False,
        )
        
        if result and hasattr(result, 'text'):
            try:
                translation_data = json.loads(result.text)
                return translation_data
            except json.JSONDecodeError as e:
                print(f"  DEBUG: Failed to parse JSON: {e}")
                return None
        else:
            print(f"  DEBUG: No result.text found")
            return None
    except Exception as e:
        print(f"Error translating segment: {e}")
        return None


def translate_title(
    title: str,
    proper_nouns_dict: Dict[str, str],
    all_summaries: List[str],
    source_lang: str,
    target_lang: str,
    model: str
) -> Optional[Dict]:
    """Translate the title with full story context"""
    
    context = create_translation_context(
        proper_nouns_dict,
        all_summaries,
        source_lang,
        target_lang
    )
    
    prompt = f"""Please translate the following {source_lang} title into {target_lang}.

{context}[{source_lang.title()} Title to Translate]
{title}

[Translation Instructions]
1. Use the proper nouns dictionary above for consistent transliterations
2. Consider the complete story context from all summaries to understand the title's meaning
3. The title should reflect the story's themes, characters, and plot as revealed in the summaries
4. Provide a natural, meaningful translation that captures the essence of the original title
5. The translation should be appropriate for the target language and culture"""

    json_descriptions = create_json_descriptions_prompt(TitleTranslation)
    
    try:
        result = generate_with_schema(
            [prompt, json_descriptions],
            schema=TitleTranslation,
            model=model,
        )
        
        if result and hasattr(result, 'text'):
            try:
                title_data = json.loads(result.text)
                return title_data
            except json.JSONDecodeError as e:
                print(f"  DEBUG: Failed to parse title JSON: {e}")
                return None
        else:
            print(f"  DEBUG: No title result.text found")
            return None
    except Exception as e:
        print(f"Error translating title: {e}")
        return None


def load_existing_translations(output_file: str) -> tuple[Dict[tuple, Dict], bool]:
    """Load existing translations from output file to support resume functionality"""
    existing = {}
    title_translated = False
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    key = (data['chapter'], data['segment'])
                    existing[key] = data
                    
                    # Check if title translation exists (chapter=0, segment=0)
                    if key == (0, 0):
                        title_translated = True
    
    return existing, title_translated


def save_translation_result(
    output_file: str,
    chapter: int,
    segment: int,
    source_lang: str,
    target_lang: str,
    translation_result: Dict
) -> None:
    """Save translation result to JSONL file"""
    record = {
        "chapter": chapter,
        "segment": segment,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "response": translation_result
    }
    
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def save_title_translation(
    output_file: str,
    source_lang: str,
    target_lang: str,
    title_result: Dict
) -> None:
    """Save title translation result to JSONL file"""
    record = {
        "chapter": 0,  # Special marker for title
        "segment": 0,  # Special marker for title
        "source_lang": source_lang,
        "target_lang": target_lang,
        "response": title_result
    }
    
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description='Translate text segments with proper noun consistency and story context')
    parser.add_argument('source_md', help='Source markdown file to translate')
    parser.add_argument('-f', '--from_lang', required=True, 
                       help='Source language (e.g., bengali, english, japanese)')
    parser.add_argument('-t', '--to_lang', required=True,
                       help='Target language (e.g., english, japanese, bengali)')
    parser.add_argument('-m', '--model', required=True,
                       help='LLM model to use (e.g., openai:gpt-4o-mini, anthropic:claude-3-haiku-20240307)')
    parser.add_argument('-o', '--output', required=True,
                       help='Output JSONL file for translation results')
    parser.add_argument('--segmentation', default='segmentation_results.jsonl',
                       help='Segmentation JSONL file (default: segmentation_results.jsonl)')
    parser.add_argument('--proper-nouns', default='proper_nouns_dictionary.json',
                       help='Proper nouns dictionary JSON file (default: proper_nouns_dictionary.json)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of chapters to process (for debugging)')
    
    args = parser.parse_args()
    
    try:
        # Load segments from markdown and segmentation data
        print(f"Loading segments from {args.source_md} using {args.segmentation}")
        data = load_chapter_blocks(args.segmentation, args.source_md)
        title = data["title"]
        chapter_blocks = data["chapters"]
        
        # Load proper nouns dictionary
        proper_nouns_dict = load_proper_nouns_dictionary(args.proper_nouns)
        
        # Load existing translations for resume capability
        existing_translations, title_already_translated = load_existing_translations(args.output)
        
        # Store total chapters count before applying limit
        total_chapters_in_file = len(chapter_blocks)
        
        # Initialize context tracking - load summaries from all previously completed chapters
        previous_summaries = []
        if args.limit:
            # Load context from all completed chapters before the ones we're processing
            for chapter_num in range(1, total_chapters_in_file + 1):
                if chapter_num <= len(chapter_blocks):
                    chapter_segments = chapter_blocks[chapter_num - 1]
                    chapter_complete = all(
                        (chapter_num, seg_num) in existing_translations
                        for seg_num in range(1, len(chapter_segments) + 1)
                    )
                    if chapter_complete:
                        # Load all summaries from this completed chapter
                        for seg_num in range(1, len(chapter_segments) + 1):
                            existing = existing_translations.get((chapter_num, seg_num), {})
                            if existing.get("summary"):
                                previous_summaries.append(existing["summary"])
                            elif existing.get("response", {}).get("summary"):
                                previous_summaries.append(existing["response"]["summary"])
                    else:
                        # Stop when we reach the first incomplete chapter
                        break
        
        # Apply chapter limit if specified - find next incomplete chapters
        if args.limit:
            incomplete_chapters = []
            for chapter_num, segments in enumerate(chapter_blocks, 1):
                # Check if this chapter is already complete
                chapter_complete = all(
                    (chapter_num, seg_num) in existing_translations
                    for seg_num in range(1, len(segments) + 1)
                )
                if not chapter_complete:
                    incomplete_chapters.append((chapter_num, segments))
                    if len(incomplete_chapters) >= args.limit:
                        break
            
            if incomplete_chapters:
                # Replace chapter_blocks with only the incomplete chapters to process
                chapter_blocks_to_process = [(num, segs) for num, segs in incomplete_chapters]
                print(f"Processing {len(incomplete_chapters)} incomplete chapters (limit: {args.limit})")
            else:
                chapter_blocks_to_process = []
                print(f"No incomplete chapters found (limit: {args.limit})")
        else:
            # Process all chapters with their original numbering
            chapter_blocks_to_process = [(i+1, chapter_blocks[i]) for i in range(len(chapter_blocks))]
        
        print(f"Title: {title}")
        print(f"Starting translation: {args.from_lang} -> {args.to_lang}")
        print(f"Total chapters in file: {total_chapters_in_file}")
        print("=" * 60)
        
        total_segments = sum(len(segments) for _, segments in chapter_blocks_to_process)
        processed_segments = 0
        completed_chapters = set()  # Track chapters that have been fully translated
        
        for chapter_num, segments in chapter_blocks_to_process:
            print(f"Chapter {chapter_num:2d}: {len(segments)} segments")
            
            for segment_num, segment_text in enumerate(segments, 1):
                processed_segments += 1
                segment_key = (chapter_num, segment_num)
                
                # Check if already processed
                if segment_key in existing_translations:
                    print(f"  Segment {segment_num} → skipped (already processed)")
                    # Load existing summary for context
                    existing = existing_translations[segment_key]
                    # Check both old format (summary field) and new format (response.summary)
                    if existing.get("summary"):
                        previous_summaries.append(existing["summary"])
                    elif existing.get("response", {}).get("summary"):
                        previous_summaries.append(existing["response"]["summary"])
                    continue
                
                print(f"  Segment {segment_num} → translating...", end="")
                
                # Translate segment
                translation_result = translate_segment(
                    segment_text,
                    proper_nouns_dict,
                    previous_summaries,
                    args.from_lang,
                    args.to_lang,
                    args.model
                )
                
                if translation_result:
                    # Update context
                    if translation_result.get("summary"):
                        previous_summaries.append(translation_result["summary"])
                    
                    # Save result
                    save_translation_result(
                        args.output,
                        chapter_num,
                        segment_num,
                        args.from_lang,
                        args.to_lang,
                        translation_result
                    )
                    
                    # Update existing_translations for chapter completion tracking
                    existing_translations[segment_key] = translation_result
                    
                    print(" completed")
                else:
                    print(" failed")
                
                # Progress indicator
                if processed_segments % 10 == 0:
                    print(f"  Progress: {processed_segments}/{total_segments} segments")
            
            # Check if this chapter is fully completed (all segments translated)
            chapter_segments_completed = all(
                (chapter_num, seg_num) in existing_translations
                for seg_num in range(1, len(segments) + 1)
            )
            if chapter_segments_completed:
                completed_chapters.add(chapter_num)
        
        # Count total completed chapters (including previously translated ones)
        all_completed_chapters = set()
        original_chapter_blocks = load_chapter_blocks(args.segmentation, args.source_md)["chapters"]
        for chapter_num in range(1, total_chapters_in_file + 1):
            if chapter_num <= len(original_chapter_blocks):
                chapter_length = len(original_chapter_blocks[chapter_num - 1])
                if all((chapter_num, seg_num) in existing_translations 
                      for seg_num in range(1, chapter_length + 1)):
                    all_completed_chapters.add(chapter_num)
        
        # Add currently completed chapters
        all_completed_chapters.update(completed_chapters)
        
        # Translate title with full story context (only if all chapters are completed)
        all_chapters_completed = len(all_completed_chapters) >= total_chapters_in_file
        should_translate_title = not title_already_translated and all_chapters_completed
        
        if should_translate_title:
            print(f"\nTranslating title: {title}")
            title_result = translate_title(
                title,
                proper_nouns_dict,
                previous_summaries,
                args.from_lang,
                args.to_lang,
                args.model
            )
            
            if title_result:
                save_title_translation(
                    args.output,
                    args.from_lang,
                    args.to_lang,
                    title_result
                )
                print(f"Title translated: {title_result.get('translated_title', '')}")
                print(f"Reasoning: {title_result.get('reasoning', '')}")
            else:
                print("Title translation failed")
        elif title_already_translated:
            print(f"\nTitle already translated (skipped)")
        elif not all_chapters_completed:
            print(f"\nTitle translation skipped (only {len(all_completed_chapters)}/{total_chapters_in_file} chapters completed)")
        
        print(f"\nTranslation completed!")
        print(f"Output saved to: {args.output}")
        print(f"Proper nouns dictionary loaded: {len(proper_nouns_dict)} entries")
        print(f"Chapters completed: {len(all_completed_chapters)}/{total_chapters_in_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
