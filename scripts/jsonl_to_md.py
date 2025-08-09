#!/usr/bin/env python3
"""
Convert JSONL translation results to Markdown format.

This script converts translation results from JSONL format to a structured
Markdown document, organizing content by chapters and including summaries,
translation notes, and full translations.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL file and return list of records."""
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def extract_title_translation(records: List[Dict[str, Any]]) -> str:
    """Extract title translation from records (chapter 0, segment 0)."""
    title_record = next(
        (r for r in records if r['chapter'] == 0 and r['segment'] == 0),
        None
    )
    if title_record and 'response' in title_record:
        response = title_record['response']
        if 'translated_title' in response:
            return response['translated_title']
        elif 'translation' in response:
            return response['translation']
    return "Untitled"


def group_by_chapter(records: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """Group records by chapter number, excluding title (chapter 0)."""
    chapters = {}
    for record in records:
        chapter = record['chapter']
        if chapter > 0:  # Exclude title translation (chapter 0)
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(record)
    
    # Sort segments within each chapter
    for chapter_records in chapters.values():
        chapter_records.sort(key=lambda x: x['segment'])
    
    return chapters


def format_translation_text(text: str) -> str:
    """Format translation text for Markdown, preserving paragraphs."""
    # Replace \n with proper paragraph breaks
    paragraphs = text.split('\n')
    formatted_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if para:
            formatted_paragraphs.append(para)
    
    return '\n\n'.join(formatted_paragraphs)


def create_markdown_content(
    records: List[Dict[str, Any]], 
    source_lang: str, 
    target_lang: str,
    output_mode: str = 'translation'
) -> str:
    """Create formatted Markdown content from JSONL records."""
    
    # Extract title
    title = extract_title_translation(records)
    
    # Group by chapters
    chapters = group_by_chapter(records)
    
    # Build markdown content
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    
    # Add language info only for full mode
    if output_mode == 'full':
        lines.append(f"*Translated from {source_lang} to {target_lang}*")
        lines.append("")
    
    # Add chapters
    for chapter_num in sorted(chapters.keys()):
        chapter_records = chapters[chapter_num]
        
        lines.append(f"## Chapter {chapter_num}")
        lines.append("")
        
        for record in chapter_records:
            response = record.get('response', {})
            segment_num = record['segment']
            
            if output_mode == 'full':
                # Full mode: include headers and all content
                lines.append(f"### Segment {segment_num}")
                lines.append("")
                
                # Summary (if available)
                if 'summary' in response:
                    lines.append("**Summary:**")
                    lines.append(response['summary'])
                    lines.append("")
                
                # Translation notes (if available)
                if 'translation_notes' in response:
                    lines.append("**Translation Notes:**")
                    lines.append(response['translation_notes'])
                    lines.append("")
                
                # Main translation
                if 'translation' in response:
                    lines.append("**Translation:**")
                    lines.append("")
                    formatted_text = format_translation_text(response['translation'])
                    lines.append(formatted_text)
                    lines.append("")
            
            elif output_mode == 'summary':
                # Summary only mode: no headers, just summaries
                if 'summary' in response:
                    lines.append(response['summary'])
                    lines.append("")
            
            else:  # translation mode (default)
                # Translation only mode: no headers, just translations
                if 'translation' in response:
                    formatted_text = format_translation_text(response['translation'])
                    lines.append(formatted_text)
                    lines.append("")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Convert JSONL translation results to Markdown format')
    parser.add_argument('input_file', help='Input JSONL file path')
    parser.add_argument('-o', '--output', help='Output Markdown file path (default: same name with .md extension)')
    parser.add_argument('--mode', choices=['translation', 'summary', 'full'], default='translation',
                       help='Output mode: translation (default, translation only), summary (summaries only), full (all content with headers)')
    parser.add_argument('--source-lang', default='Bengali', help='Source language name (default: Bengali)')
    parser.add_argument('--target-lang', default='English', help='Target language name (default: English)')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' not found")
        return 1
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.md')
    
    try:
        print(f"Loading JSONL file: {input_path}")
        records = load_jsonl(str(input_path))
        
        if not records:
            print("Error: No records found in input file")
            return 1
        
        print(f"Processing {len(records)} records...")
        
        # Create markdown content
        markdown_content = create_markdown_content(
            records,
            args.source_lang,
            args.target_lang,
            args.mode
        )
        
        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Markdown file created: {output_path}")
        
        # Show statistics
        chapters = group_by_chapter(records)
        total_segments = sum(len(ch) for ch in chapters.values())
        print(f"Converted {len(chapters)} chapters, {total_segments} segments")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
