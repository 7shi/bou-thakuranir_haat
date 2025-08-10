import re
import os
from pathlib import Path
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
#model="models/imagen-4.0-generate-preview-06-06"
model="models/imagen-3.0-generate-002"

def generate(image_path: Path, prompt: str):
    """Generates images using the Gemini API and saves them."""
    print(f"Generating image {image_path} ...")
    result = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=dict(
            number_of_images=1,
            output_mime_type="image/jpeg",
            person_generation="ALLOW_ADULT",
            aspect_ratio="16:9",
        )
    )

    if not result.generated_images:
        print("No images were generated for this prompt.")
        return

    # Ensure the output directory exists
    output_dir = image_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    result.generated_images[0].image.save(str(image_path))


def parse_prompts(markdown_content: str) -> dict[int, str]:
    """Parses the markdown file to extract chapter numbers and prompts."""
    prompts = {}
    chapter_num = 0
    for line in markdown_content.splitlines():
        if m := re.match(r"### Chapter (\d+)", line):
            chapter_num = int(m.group(1))
        elif m := re.match(r"\*\*Prompt:\*\*(.*)", line):
            prompts[chapter_num] = m.group(1).strip()
    return prompts

def main():
    """Main function to read prompts from images.md and generate images."""
    script_dir = Path(__file__).parent
    markdown_file = script_dir.parent / "images.md"
    output_dir = script_dir.parent / "images"

    print(f"Reading prompts from: {markdown_file}")
    if not markdown_file.is_file():
        print(f"Error: Markdown file not found at {markdown_file}")
        return

    content = markdown_file.read_text(encoding="utf-8")
    prompts = parse_prompts(content)

    if not prompts:
        print("No prompts could be parsed from the markdown file.")
        return

    print(f"Found {len(prompts)} prompts to process.")
    
    for chapter_num, prompt in prompts.items():
        for i in range(1, 5):
            image_path = output_dir / f"{chapter_num:02d}_{i}.jpg"
            if not image_path.exists():
                generate(image_path, prompt)

if __name__ == "__main__":
    main()
