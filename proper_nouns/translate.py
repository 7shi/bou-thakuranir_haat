import os
import json
import argparse
from typing import Dict, List
from pydantic import BaseModel, Field
from llm7shi.compat import generate_with_schema
from llm7shi import create_json_descriptions_prompt
import sys
import os

from utils import (
    load_existing_proper_nouns,
    create_consolidated_dictionary,
    save_translation_result
)


class ProperNounsTranslation(BaseModel):
    """Translations of proper nouns to target language"""
    translations: List[str] = Field(
        description="List of target language translations corresponding to the input proper nouns in the same order"
    )


def load_proper_nouns_dictionary(input_file: str) -> Dict[str, str]:
    """Load existing proper nouns dictionary from JSON file"""
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)




def translate_proper_nouns_batch(
    proper_nouns_dict: Dict[str, str],
    existing_translations: Dict[str, str],
    source_lang: str,
    intermediate_lang: str,
    target_lang: str,
    model: str,
    work_file: str,
    batch_size: int = 50,
    limit: int = None
) -> Dict[str, str]:
    """Translate proper nouns in batches to target language"""
    
    # Filter out already translated items
    remaining_nouns = {k: v for k, v in proper_nouns_dict.items() if k not in existing_translations}
    source_nouns = list(remaining_nouns.keys())
    
    if not source_nouns:
        print("  All proper nouns already translated")
        return existing_translations.copy()
    
    translated_dict = existing_translations.copy()
    
    # Calculate total batches and apply limit if specified
    total_batches = (len(source_nouns) + batch_size - 1) // batch_size
    if limit is not None:
        total_batches = min(total_batches, limit)
        print(f"  Limited to {limit} API calls (processing {limit * batch_size} items max)")
    
    print(f"  Remaining to translate: {len(source_nouns)} proper nouns")
    
    # Process in batches
    api_calls_made = 0
    for i in range(0, len(source_nouns), batch_size):
        if limit is not None and api_calls_made >= limit:
            print(f"  Reached API call limit ({limit}), stopping")
            break
            
        api_calls_made += 1
        batch = source_nouns[i:i+batch_size]
        
        print(f"  Translating batch {api_calls_made}/{total_batches} ({len(batch)} items)...", end="")
        
        # Create batch dictionary in "A: B\nC: D\n..." format
        batch_lines = []
        for noun in batch:
            batch_lines.append(f"{noun}: {remaining_nouns[noun]}")
        batch_dict = "\n".join(batch_lines)
        
        prompt = f"""The above dictionary shows proper nouns in {source_lang} (keys) with their {intermediate_lang} translations (values). Please create a new dictionary mapping the same {source_lang} proper nouns (keys) to their {target_lang} translations (values).

[Translation Instructions]
1. Use the {source_lang} terms as keys (same as in the input)
2. Translate each {source_lang} proper noun to {target_lang} using BOTH the original {source_lang} term AND the {intermediate_lang} translation as reference
3. The {intermediate_lang} translations provide valuable context for accurate {target_lang} translation
4. For names: use appropriate {target_lang} transliteration/translation conventions
5. For places: use commonly accepted {target_lang} names where they exist
6. For deities/mythological figures: use standard {target_lang} translations
7. For titles/honorifics: translate appropriately to {target_lang} equivalents
8. Maintain consistency and cultural appropriateness
9. Return the {target_lang} translations in the EXACT SAME ORDER as the input proper nouns

Examples of good translations:
- Personal names should be transliterated appropriately to {target_lang}
- Place names should use established {target_lang} names when available
- Religious/mythological terms should use standard {target_lang} translations
- Titles should be translated to appropriate {target_lang} equivalents"""

        json_descriptions = create_json_descriptions_prompt(ProperNounsTranslation)
        
        try:
            result = generate_with_schema(
                [batch_dict, prompt, json_descriptions],
                schema=ProperNounsTranslation,
                model=model,
                show_params=True,
            )
            
            if result and hasattr(result, 'text'):
                try:
                    translation_data = json.loads(result.text)
                    translations_list = translation_data.get("translations", [])
                    
                    # Map translations back to source nouns
                    if len(translations_list) == len(batch):
                        batch_translations = {}
                        for i, source_noun in enumerate(batch):
                            translated_dict[source_noun] = translations_list[i]
                            batch_translations[source_noun] = translations_list[i]
                        
                        # Save this batch result
                        save_translation_result(
                            work_file,
                            api_calls_made,
                            source_lang,
                            intermediate_lang,
                            target_lang,
                            batch_translations
                        )
                        
                        print(f" completed ({len(translations_list)} translated)")
                    else:
                        print(f" failed (length mismatch: expected {len(batch)}, got {len(translations_list)})")
                except json.JSONDecodeError as e:
                    print(f" failed (JSON decode error: {e})")
            else:
                print(" failed (no result)")
        except Exception as e:
            print(f" failed (error: {e})")
    
    return translated_dict


def main():
    parser = argparse.ArgumentParser(description='Translate proper nouns dictionary to target language')
    parser.add_argument('input_json', help='Input JSON file with proper nouns dictionary')
    parser.add_argument('-f', '--from_lang', required=True,
                       help='Source language (e.g., bengali, english, japanese)')
    parser.add_argument('-i', '--intermediate-lang', required=True,
                       help='Intermediate language of input dictionary values (e.g., english)')
    parser.add_argument('-t', '--to_lang', required=True,
                       help='Target language (e.g., english, japanese, bengali)')
    parser.add_argument('-m', '--model', required=True,
                       help='LLM model to use (e.g., openai:gpt-4o-mini, anthropic:claude-3-haiku-20240307)')
    parser.add_argument('-o', '--output', required=True,
                       help='Output JSON file for translated proper nouns dictionary')
    parser.add_argument('--batch-size', type=int, default=30,
                       help='Number of proper nouns to translate in each batch (default: 30)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of API calls to make (for debugging/testing)')
    
    args = parser.parse_args()
    
    try:
        # Create work file name from output file
        work_file = args.output.replace('.json', '-work.jsonl')
        
        # Load source proper nouns dictionary
        print(f"Loading proper nouns dictionary from {args.input_json}")
        source_dict = load_proper_nouns_dictionary(args.input_json)
        
        # Load existing translations for resume capability
        existing_translations = load_existing_proper_nouns(work_file)
        
        print(f"Translating proper nouns: {args.from_lang} -> {args.to_lang}")
        print(f"Input format: {args.from_lang} -> {args.intermediate_lang}")
        print(f"Output format: {args.from_lang} -> {args.to_lang}")
        print(f"Total proper nouns to translate: {len(source_dict)}")
        print(f"Already translated: {len(existing_translations)}")
        print(f"Batch size: {args.batch_size}")
        
        # Apply limit information
        if args.limit:
            print(f"API call limit: {args.limit}")
        
        print("=" * 60)
        
        # Translate proper nouns
        translated_dict = translate_proper_nouns_batch(
            source_dict,
            existing_translations,
            args.from_lang,
            args.intermediate_lang,
            args.to_lang,
            args.model,
            work_file,
            args.batch_size,
            args.limit
        )
        
        # Create consolidated dictionary
        create_consolidated_dictionary(work_file, args.output, "translations")
        
        print(f"\nTranslation completed!")
        print(f"Working data saved to: {work_file}")
        print(f"Final dictionary saved to: {args.output}")
        print(f"Source proper nouns: {len(source_dict)}")
        print(f"Translated proper nouns: {len(translated_dict)}")
        print(f"New translations in this run: {len(translated_dict) - len(existing_translations)}")
        
        # Show sample translations
        if translated_dict:
            print(f"\nSample Translations ({args.from_lang} -> {args.to_lang}):")
            sample_items = list(translated_dict.items())[:10]
            for source, target in sample_items:
                print(f"  {source} → {target}")
            if len(translated_dict) > 10:
                print(f"  ... and {len(translated_dict) - 10} more")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
