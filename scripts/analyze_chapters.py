import re

def analyze_chapters(filename):
    """Analyze line count per chapter (excluding empty lines)"""
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    chapters = []
    current_chapter = None
    current_content_lines = 0
    
    for i, line in enumerate(lines, 1):
        # Detect chapter start
        chapter_match = re.match(r'^## (.+পরিচ্ছেদ.*)', line.strip())
        
        if chapter_match:
            # Save previous chapter
            if current_chapter:
                chapters.append({
                    'title': current_chapter,
                    'start_line': current_start_line,
                    'end_line': i - 1,
                    'content_lines': current_content_lines,
                    'total_lines': i - 1 - current_start_line + 1
                })
            
            # Start new chapter
            current_chapter = chapter_match.group(1)
            current_start_line = i
            current_content_lines = 0
        
        elif current_chapter and line.strip():  # If not empty line
            current_content_lines += 1
    
    # Save last chapter
    if current_chapter:
        chapters.append({
            'title': current_chapter,
            'start_line': current_start_line,
            'end_line': len(lines),
            'content_lines': current_content_lines,
            'total_lines': len(lines) - current_start_line + 1
        })
    
    return chapters

def print_analysis(chapters):
    """Display analysis results"""
    
    print("Chapter Line Count Analysis (excluding empty lines)")
    print("=" * 60)
    print(f"{'Chapter':<4} {'Start':<6} {'End':<6} {'Content':<8} {'Total':<6}")
    print("-" * 60)
    
    total_content_lines = 0
    total_lines = 0
    
    for i, chapter in enumerate(chapters, 1):
        print(f"{i:<4} {chapter['start_line']:<6} "
              f"{chapter['end_line']:<6} {chapter['content_lines']:<8} {chapter['total_lines']:<6}")
        
        total_content_lines += chapter['content_lines']
        total_lines += chapter['total_lines']
    
    print("-" * 60)
    print(f"{'Total':<4} {'':6} {'':6} {total_content_lines:<8} {total_lines:<6}")
    
    # Statistics
    content_lines = [ch['content_lines'] for ch in chapters]
    print(f"\nStatistics:")
    print(f"Number of chapters: {len(chapters)}")
    print(f"Shortest chapter: {min(content_lines)} lines")
    print(f"Longest chapter: {max(content_lines)} lines") 
    print(f"Average: {sum(content_lines)/len(content_lines):.1f} lines")
    
    # Line count histogram (5-line intervals)
    print(f"\nLine Count Distribution Histogram (5-line intervals):")
    print("=" * 50)
    
    # Create 5-line interval ranges
    max_lines = max(content_lines)
    ranges = []
    for start in range(0, max_lines + 1, 5):
        end = start + 4
        if start == 0:
            start = 1  # 1 line or more
        count = len([ch for ch in chapters if start <= ch['content_lines'] <= end])
        ranges.append((f"{start:2d}-{end:2d} lines", count))
    
    # Display histogram
    max_count = max(count for _, count in ranges)
    for range_label, count in ranges:
        if count > 0:  # Don't display ranges with 0 count
            bar = "█" * count if max_count > 0 else ""
            print(f"{range_label}: {count:2d} chapters {bar}")
    
    # Distribution by line count
    short_chapters = len([ch for ch in chapters if ch['content_lines'] < 30])
    medium_chapters = len([ch for ch in chapters if 30 <= ch['content_lines'] < 80])
    long_chapters = len([ch for ch in chapters if ch['content_lines'] >= 80])
    
    print(f"\nDistribution by line count:")
    print(f"Short chapters (<30 lines): {short_chapters} chapters")
    print(f"Medium chapters (30-79 lines): {medium_chapters} chapters") 
    print(f"Long chapters (≥80 lines): {long_chapters} chapters")

if __name__ == "__main__":
    filename = "all-bn.md"
    
    try:
        chapters = analyze_chapters(filename)
        print_analysis(chapters)
        
        # Save as CSV file
        import csv
        with open('chapter_analysis.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Chapter', 'Start Line', 'End Line', 'Content Lines', 'Total Lines'])
            
            for i, chapter in enumerate(chapters, 1):
                writer.writerow([i, chapter['start_line'], 
                               chapter['end_line'], chapter['content_lines'], chapter['total_lines']])
        
        print(f"\nResults saved to chapter_analysis.csv.")
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
