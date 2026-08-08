#!/usr/bin/env python3
"""Compress images larger than a target size into a separate directory."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageOps
except ImportError:
    print(
        "Pillow is required. Install it with: python3 -m pip install pillow",
        file=sys.stderr,
    )
    sys.exit(1)


DEFAULT_MAX_SIZE = 1.5 * 1024 * 1024
SIZE_UNITS = {
    "K": 1024,
    "M": 1024 * 1024,
    "G": 1024 * 1024 * 1024,
}
SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
}


def parse_size(size_str: str) -> int:
    """Parse a human-readable size such as 500K or 1.5M into bytes."""
    match = re.fullmatch(r"([\d]+(?:\.\d+)?)\s*([KMG])?B?", size_str.strip().upper())
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid size format: {size_str!r}. Use formats like 500K, 1.5M, or 2MB."
        )

    value = float(match.group(1))
    unit = match.group(2)
    size = value * SIZE_UNITS[unit] if unit else value
    if size <= 0:
        raise argparse.ArgumentTypeError("The target size must be greater than zero.")
    return int(size)


def format_size(size: int | float) -> str:
    """Format bytes using binary units for human-readable output."""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f}MB"
    if size >= 1024:
        return f"{size / 1024:.0f}KB"
    return f"{size:.0f}B"


def iter_images(source: Path, recursive: bool) -> Iterable[Path]:
    """Yield supported image files from a file or directory."""
    if source.is_file():
        if source.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield source
        return

    iterator = source.rglob("*") if recursive else source.iterdir()
    for path in sorted(iterator):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def is_within(path: Path, directory: Path) -> bool:
    """Return whether path is directory itself or one of its descendants."""
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def output_path_for(
    image_path: Path, source: Path, output_dir: Path, recursive: bool
) -> Path:
    """Build an output path, preserving relative directories when requested."""
    if source.is_file():
        relative_path = Path(image_path.name)
    elif recursive:
        relative_path = image_path.relative_to(source)
    else:
        relative_path = Path(image_path.name)
    return output_dir / relative_path


def jpeg_frame(image: Image.Image) -> Image.Image:
    """Convert an image to a JPEG-compatible frame, preserving transparency."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def prepare_image(image: Image.Image, image_format: str) -> Image.Image:
    """Normalize image orientation and color mode for the target format."""
    image = ImageOps.exif_transpose(image)
    if image_format == "JPEG":
        return jpeg_frame(image)
    if image_format == "PNG" and image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA"):
        return image.convert("RGBA" if "A" in image.getbands() else "RGB")
    return image


def save_image(image: Image.Image, output_path: Path, image_format: str, quality: int) -> None:
    """Save a candidate image with format-specific optimization settings."""
    save_kwargs: dict[str, object] = {}
    if image_format == "JPEG":
        save_kwargs.update(quality=quality, optimize=True, progressive=True)
    elif image_format == "WEBP":
        save_kwargs.update(quality=quality, method=6)
    elif image_format == "PNG":
        save_kwargs.update(optimize=True, compress_level=9)
    elif image_format == "GIF":
        save_kwargs.update(optimize=True)
    elif image_format == "TIFF":
        save_kwargs.update(compression="tiff_adobe_deflate")
    elif image_format == "BMP":
        # BMP has no useful quality setting, but Pillow can still save a valid file.
        pass

    image.save(output_path, format=image_format, **save_kwargs)


def compress_to_target(
    source_path: Path, output_path: Path, max_bytes: int
) -> tuple[int, bool]:
    """Compress one image and return (result size, target reached)."""
    with Image.open(source_path) as original:
        image_format = (original.format or source_path.suffix.lstrip(".")).upper()
        if image_format == "JPG":
            image_format = "JPEG"
        if image_format == "TIF":
            image_format = "TIFF"
        if image_format not in {"JPEG", "PNG", "WEBP", "GIF", "TIFF", "BMP"}:
            raise ValueError(f"Unsupported image format: {image_format}")

        image = prepare_image(original, image_format)
        original_size = image.size
        qualities = (
            list(range(95, 9, -5))
            if image_format in {"JPEG", "WEBP"}
            else [90, 75, 60, 45, 30, 15]
        )
        scale = 1.0
        best_size: int | None = None
        reached_target = False

        with tempfile.TemporaryDirectory(prefix="image-compress-") as temp_dir:
            temp_path = Path(temp_dir) / output_path.name
            while scale >= 0.2:
                if scale == 1.0:
                    candidate = image
                else:
                    width = max(1, int(original_size[0] * scale))
                    height = max(1, int(original_size[1] * scale))
                    candidate = image.resize((width, height), Image.Resampling.LANCZOS)

                for quality in qualities:
                    save_image(candidate, temp_path, image_format, quality)
                    candidate_size = temp_path.stat().st_size
                    if best_size is None or candidate_size < best_size:
                        best_size = candidate_size
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        temp_path.replace(output_path)
                        temp_path = Path(temp_dir) / output_path.name
                    if candidate_size <= max_bytes:
                        reached_target = True
                        return candidate_size, reached_target

                scale *= 0.9

        if best_size is None:
            raise RuntimeError("No compressed output was produced")
        return best_size, reached_target


def compress_images(
    source: str,
    output: str | None = None,
    max_size: int = int(DEFAULT_MAX_SIZE),
    recursive: bool = False,
) -> int:
    """Compress all oversized images and return a process exit code."""
    source_path = Path(source).expanduser()
    if not source_path.exists():
        print(f"Path not found: {source}", file=sys.stderr)
        return 1

    if not source_path.is_file() and not source_path.is_dir():
        print(f"Path is not a file or directory: {source}", file=sys.stderr)
        return 1

    output_path = (
        Path(output).expanduser()
        if output
        else source_path.parent / "compressed"
        if source_path.is_file()
        else source_path / "compressed"
    )
    source_resolved = source_path.resolve()
    output_resolved = output_path.resolve()
    if source_resolved == output_resolved:
        print("Output directory must not be the input file or directory.", file=sys.stderr)
        return 1

    output_path.mkdir(parents=True, exist_ok=True)
    image_paths = [
        image_path
        for image_path in iter_images(source_path, recursive)
        if not is_within(image_path.resolve(), output_resolved)
    ]
    print(f"Output directory: {output_path}")
    if not image_paths:
        print("No supported image files found.")
        return 0
    print(f"Found {len(image_paths)} image(s)")

    compressed = skipped = failed = 0
    for image_path in image_paths:
        original_bytes = image_path.stat().st_size
        if original_bytes <= max_size:
            skipped += 1
            print(
                f"Skipped: {image_path.name} "
                f"({format_size(original_bytes)} <= {format_size(max_size)})"
            )
            continue

        destination = output_path_for(image_path, source_path, output_path, recursive)
        try:
            result_bytes, reached_target = compress_to_target(
                image_path, destination, max_size
            )
            if result_bytes >= original_bytes:
                if destination.exists():
                    destination.unlink()
                failed += 1
                print(
                    f"Failed: {image_path.name} "
                    "(compression did not reduce the file size)"
                )
                continue

            compressed += 1
            status = "" if reached_target else " (target not reached)"
            ratio = (1 - result_bytes / original_bytes) * 100
            print(
                f"Compressed: {image_path.name} "
                f"({format_size(original_bytes)} -> {format_size(result_bytes)}, "
                f"{ratio:.1f}%){status}"
            )
        except Exception as error:
            failed += 1
            print(f"Failed: {image_path.name}: {error}")

    print(f"Summary: {compressed} compressed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compress images larger than a target size into a separate directory."
    )
    parser.add_argument("path", help="Image file or directory containing images")
    parser.add_argument(
        "-s",
        "--max-size",
        type=parse_size,
        default=int(DEFAULT_MAX_SIZE),
        help="Maximum file size, e.g. 500K, 1.5M (default: 1.5M)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory (default: <input location>/compressed)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively scan directories and preserve relative paths",
    )
    args = parser.parse_args()
    return compress_images(args.path, args.output, args.max_size, args.recursive)


if __name__ == "__main__":
    raise SystemExit(main())
