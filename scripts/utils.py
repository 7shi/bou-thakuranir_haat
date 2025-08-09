import json
import re
from typing import List, Dict, Any


def load_chapter_blocks(jsonl_path: str, md_path: str) -> Dict[str, Any]:
    """
    Load JSONL segmentation data and source markdown file, returning title and chapter blocks.
    
    Args:
        jsonl_path: Path to JSONL file with segmentation data
        md_path: Path to source markdown file
        
    Returns:
        Dict[str, Any]: Dictionary containing title and chapters
        - "title": The main title from the first line of the markdown (without #)
        - "chapters": List of chapters, each containing list of segment strings
        Format: {"title": "Title", "chapters": [["segment1", "segment2", ...], ...]}
        
    Note:
        - Chapters found in JSONL are segmented according to boundaries
        - Chapters not in JSONL are included as single blocks
    """
    # Load source markdown file
    with open(md_path, 'r', encoding='utf-8') as f:
        md_lines = f.readlines()
    
    # Extract title from first line (remove # and strip)
    title = ""
    if md_lines:
        first_line = md_lines[0].strip()
        if first_line.startswith('#'):
            title = first_line.lstrip('#').strip()
    
    # Extract all chapters from markdown file
    all_chapters = {}
    current_chapter = None
    current_start_line = None
    current_content_lines = 0
    
    for i, line in enumerate(md_lines, 1):
        # Detect chapter start
        chapter_match = re.match(r'^## (.+পরিচ্ছেদ.*)', line.strip())
        
        if chapter_match:
            # Save previous chapter
            if current_chapter:
                chapter_num = len(all_chapters) + 1
                all_chapters[chapter_num] = {
                    'title': current_chapter,
                    'start_line': current_start_line,
                    'end_line': i - 1,
                    'content_lines': current_content_lines,
                }
            
            # Start new chapter
            current_chapter = chapter_match.group(1)
            current_start_line = i
            current_content_lines = 0
        
        elif current_chapter and line.strip():  # If not empty line
            current_content_lines += 1
    
    # Save last chapter
    if current_chapter:
        chapter_num = len(all_chapters) + 1
        all_chapters[chapter_num] = {
            'title': current_chapter,
            'start_line': current_start_line,
            'end_line': len(md_lines),
            'content_lines': current_content_lines,
        }
    
    # Load segmentation data from JSONL
    segmentation_data = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                chapter_num = data['chapter']
                boundaries = data['boundaries']
                segmentation_data[chapter_num] = boundaries
    
    # Process all chapters
    result = []
    
    for chapter_num in sorted(all_chapters.keys()):
        chapter_info = all_chapters[chapter_num]
        
        if chapter_num in segmentation_data:
            # Chapter has segmentation data - use boundaries
            boundaries = segmentation_data[chapter_num]
            chapter_segments = []
            
            for boundary in boundaries:
                start_line = boundary['start_line']
                end_line = boundary['end_line']
                
                # Extract lines from source markdown (convert to 0-based indexing)
                segment_lines = []
                for line_num in range(start_line - 1, end_line):
                    if line_num < len(md_lines):
                        line_content = md_lines[line_num].strip()
                        # Skip empty lines and chapter headers
                        if line_content and not line_content.startswith('##'):
                            segment_lines.append(line_content)
                
                # Join segment lines into a single string
                segment_text = '\n'.join(segment_lines)
                if segment_text:  # Only add non-empty segments
                    chapter_segments.append(segment_text)
            
            if chapter_segments:  # Only add chapters with content
                result.append(chapter_segments)
        
        else:
            # Chapter not in JSONL - create single block
            start_line = chapter_info['start_line']
            end_line = chapter_info['end_line']
            
            # Extract all content lines for the chapter
            chapter_lines = []
            for line_num in range(start_line - 1, end_line):
                if line_num < len(md_lines):
                    line_content = md_lines[line_num].strip()
                    # Skip empty lines and chapter headers
                    if line_content and not line_content.startswith('##'):
                        chapter_lines.append(line_content)
            
            # Create single block for the chapter
            if chapter_lines:
                chapter_text = '\n'.join(chapter_lines)
                result.append([chapter_text])  # Single segment in a list
    
    return {"title": title, "chapters": result}


if __name__ == "__main__":
    # Test the function
    data = load_chapter_blocks("segmentation_results.jsonl", "all-bn.md")
    
    print(f"Title: {data['title']}")
    print(f"Loaded {len(data['chapters'])} chapters")
    for i, chapter in enumerate(data['chapters'], 1):
        print(f"Chapter {i}: {len(chapter)} segments")
        for j, segment in enumerate(chapter, 1):
            print(f"  Segment {j}: {len(segment)} characters")