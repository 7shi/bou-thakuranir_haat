import argparse
from pathlib import Path
from PIL import Image

MAX_SIZE = 50 * 1024
TARGET_WIDTH = 1024

# tmp: chapter number -> selected suffix (1-4) among images/{NN}_{suffix}.jpg
SELECTED_SUFFIX = {
    0: 4, 1: 3, 2: 1, 3: 4, 4: 1, 5: 2, 6: 1, 7: 3, 8: 2, 9: 2,
    10: 2, 11: 4, 12: 1, 13: 4, 14: 4, 15: 4, 16: 3, 17: 4, 18: 4, 19: 3,
    20: 1, 21: 1, 22: 3, 23: 2, 24: 4, 25: 4, 26: 2, 27: 2, 28: 3, 29: 2,
    30: 4, 31: 2, 32: 4, 33: 2, 34: 1, 35: 3, 36: 3, 37: 4, 38: 2,
}


def compress(src_path: Path, dst_path: Path):
    """Saves src_path as a JPEG under MAX_SIZE bytes, shrinking quality/size as needed."""
    image = Image.open(src_path).convert("RGB")
    height = round(image.height * TARGET_WIDTH / image.width)
    image = image.resize((TARGET_WIDTH, height))
    for quality in range(85, 4, -5):
        image.save(dst_path, "JPEG", quality=quality)
        if dst_path.stat().st_size <= MAX_SIZE:
            return
    while dst_path.stat().st_size > MAX_SIZE:
        image = image.resize((image.width * 9 // 10, image.height * 9 // 10))
        image.save(dst_path, "JPEG", quality=70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Recompress images even if the output already exists")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    src_dir = script_dir.parent / "images"
    dst_dir = script_dir.parent / "dist" / "images"
    dst_dir.mkdir(parents=True, exist_ok=True)

    for chapter_num, suffix in SELECTED_SUFFIX.items():
        src_path = src_dir / f"{chapter_num:02d}_{suffix}.jpg"
        dst_path = dst_dir / f"{chapter_num:02d}.jpg"
        if dst_path.exists() and not args.force:
            continue
        compress(src_path, dst_path)
        print(f"{src_path.name} -> {dst_path} ({dst_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
