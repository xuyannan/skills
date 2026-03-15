#!/usr/bin/env python3
"""Convert all HEIC images in a directory to JPG format."""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
    import pillow_heif
except ImportError:
    print("Please install required packages: pip3 install pillow pillow-heif")
    sys.exit(1)

pillow_heif.register_heif_opener()


MAX_SIZE_BYTES = 1.5 * 1024 * 1024  # 1.5MB


def save_with_size_limit(img: Image.Image, output_path: Path, max_bytes: float) -> None:
    """Save image as JPG, adjusting quality to stay under size limit."""
    quality = 95
    while quality >= 10:
        img.save(output_path, "JPEG", quality=quality)
        if output_path.stat().st_size <= max_bytes:
            return
        quality -= 5
    # If still too large, resize the image
    scale = 0.9
    while scale > 0.3:
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        resized.save(output_path, "JPEG", quality=85)
        if output_path.stat().st_size <= max_bytes:
            return
        scale -= 0.1


def convert_heic_to_jpg(directory: str, output_dir: str = None, delete_original: bool = False) -> None:
    """Convert all HEIC files in directory to JPG."""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)
    
    # Setup output directory
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = dir_path / "jpg_output"
    out_path.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out_path}")
    
    heic_files = list(dir_path.glob("*.HEIC")) + list(dir_path.glob("*.heic"))
    
    if not heic_files:
        print("No HEIC files found.")
        return
    
    print(f"Found {len(heic_files)} HEIC file(s)")
    
    for heic_file in heic_files:
        jpg_file = out_path / heic_file.with_suffix(".jpg").name
        try:
            with Image.open(heic_file) as img:
                rgb_img = img.convert("RGB")
                save_with_size_limit(rgb_img, jpg_file, MAX_SIZE_BYTES)
            size_mb = jpg_file.stat().st_size / (1024 * 1024)
            print(f"Converted: {heic_file.name} -> {jpg_file.name} ({size_mb:.2f}MB)")
            
            if delete_original:
                heic_file.unlink()
                print(f"Deleted: {heic_file.name}")
        except Exception as e:
            print(f"Failed to convert {heic_file.name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert HEIC images to JPG")
    parser.add_argument("directory", help="Directory containing HEIC files")
    parser.add_argument("-o", "--output", help="Output directory (default: <directory>/jpg_output)")
    parser.add_argument("-d", "--delete", action="store_true", 
                        help="Delete original HEIC files after conversion")
    args = parser.parse_args()
    
    convert_heic_to_jpg(args.directory, args.output, args.delete)
