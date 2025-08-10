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
    load_existing_tsv,
    create_consolidated_tsv
)


class ProperNounsTranslation(BaseModel):
    """Translations of proper nouns to target language"""
    translations: List[str] = Field(
        description="List of target language translations corresponding to the input proper nouns in the same order"
    )


def update_tsv_with_translations(tsv_file: str, new_translations: Dict[str, str], target_lang: str) -> None:
    """Update TSV file with new translations"""
    # Load existing TSV data
    existing_data = load_existing_tsv(tsv_file)
    
    # Normalize target language
    target_lang_normalized = target_lang.title()
    
    # Update with new translations
    for source_term, translation in new_translations.items():
        if source_term not in existing_data:
            existing_data[source_term] = {}
        existing_data[source_term][target_lang_normalized] = translation
    
    # Write back to TSV
    if existing_data:
        # Get all language codes
        all_lang_codes = set()
        for translations in existing_data.values():
            all_lang_codes.update(translations.keys())
        
        lang_codes = sorted(all_lang_codes)
        
        # Write TSV file
        with open(tsv_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write('\t'.join(lang_codes) + '\n')
            
            # Write data rows
            for source_term in sorted(existing_data.keys()):
                row_data = []
                for lang_code in lang_codes:
                    translation = existing_data[source_term].get(lang_code, '')
                    row_data.append(translation)
                f.write('\t'.join(row_data) + '\n')


def load_tsv_language_data(tsv_file: str, from_lang: str, intermediate_lang: str) -> Dict[str, str]:
    """Load proper nouns dictionary from TSV file for specific language pair
    
    Args:
        tsv_file: Path to TSV file
        from_lang: Source language (normalized to Title case)
        intermediate_lang: Intermediate language (normalized to Title case)
    
    Returns:
        Dict mapping source terms to intermediate language translations
    """
    if not os.path.exists(tsv_file):
        return {}
    
    # Normalize language names to Title case
    from_lang_normalized = from_lang.title()
    intermediate_lang_normalized = intermediate_lang.title()
    
    # Load TSV data
    tsv_data = load_existing_tsv(tsv_file)
    
    # Extract source->intermediate mapping
    result = {}
    for source_term, translations in tsv_data.items():
        source_value = translations.get(from_lang_normalized, '')
        intermediate_value = translations.get(intermediate_lang_normalized, '')
        
        # Use source_value as key if available, otherwise use source_term
        key = source_value if source_value else source_term
        if intermediate_value:
            result[key] = intermediate_value
    
    return result




def translate_proper_nouns_batch(
    proper_nouns_dict: Dict[str, str],
    existing_tsv_data: Dict[str, Dict[str, str]],
    source_lang: str,
    intermediate_lang: str,
    target_lang: str,
    model: str,
    output_tsv: str,
    batch_size: int = 50,
    limit: int = None,
    show_params: bool
) -> Dict[str, str]:
    """Translate proper nouns in batches to target language"""
    
    # Normalize language names
    target_lang_normalized = target_lang.title()
    
    # Filter out already translated items (check TSV data)
    remaining_nouns = {}
    existing_translations = {}
    
    for source_term, intermediate_translation in proper_nouns_dict.items():
        if source_term in existing_tsv_data and target_lang_normalized in existing_tsv_data[source_term]:
            # Already translated
            existing_translations[source_term] = existing_tsv_data[source_term][target_lang_normalized]
        else:
            # Needs translation
            remaining_nouns[source_term] = intermediate_translation
    
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
                show_params=show_params,
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
                        
                        # Update TSV immediately after each successful batch
                        update_tsv_with_translations(output_tsv, batch_translations, target_lang)
                        
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
    parser.add_argument('input_tsv', nargs='?', help='Input TSV file (optional, defaults to output file)')
    parser.add_argument('-f', '--from_lang', required=True,
                       help='Source language (e.g., bengali, english, japanese)')
    parser.add_argument('-i', '--intermediate-lang', required=True,
                       help='Intermediate language of input dictionary values (e.g., english)')
    parser.add_argument('-t', '--to_lang', required=True,
                       help='Target language (e.g., english, japanese, bengali)')
    parser.add_argument('-m', '--model', required=True,
                       help='LLM model to use (e.g., openai:gpt-4o-mini, anthropic:claude-3-haiku-20240307)')
    parser.add_argument('-o', '--output', required=True,
                       help='Output TSV file for translated proper nouns dictionary')
    parser.add_argument('--batch-size', type=int, default=30,
                       help='Number of proper nouns to translate in each batch (default: 30)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of API calls to make (for debugging/testing)')
    
    args = parser.parse_args()
    
    try:
        # Determine input file (default to output file if not specified)
        input_file = args.input_tsv if args.input_tsv else args.output
        
        # Load source proper nouns dictionary from TSV
        print(f"Loading proper nouns dictionary from {input_file}")
        source_dict = load_tsv_language_data(input_file, args.from_lang, args.intermediate_lang)
        
        # Load existing TSV data for skip logic
        existing_tsv_data = load_existing_tsv(args.output)
        
        print(f"Translating proper nouns: {args.from_lang} -> {args.to_lang}")
        print(f"Input format: {args.from_lang} -> {args.intermediate_lang}")
        print(f"Output format: {args.from_lang} -> {args.to_lang}")
        print(f"Total proper nouns to translate: {len(source_dict)}")
        print(f"Batch size: {args.batch_size}")
        
        # Apply limit information
        if args.limit:
            print(f"API call limit: {args.limit}")
        
        print("=" * 60)
        
        # Translate proper nouns
        translated_dict = translate_proper_nouns_batch(
            source_dict,
            existing_tsv_data,
            args.from_lang,
            args.intermediate_lang,
            args.to_lang,
            args.model,
            args.output,
            args.batch_size,
            args.limit,
            bool(args.limit)
        )
        
        print(f"\nTranslation completed!")
        print(f"Final TSV saved to: {args.output}")
        print(f"Source proper nouns: {len(source_dict)}")
        print(f"Total translated proper nouns: {len(translated_dict)}")
        
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
