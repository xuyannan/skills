#!/usr/bin/env python3
"""Batch apply aspect-ratio-specific watermark templates to images."""

from __future__ import annotations

import argparse
import re
import shutil
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


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SIZE_UNITS = {"K": 1024, "M": 1024**2, "G": 1024**3}
DEFAULT_QUALITY = 95


def parse_size(size_str: str) -> int:
    """Parse a human-readable size such as 10M or 500KB into bytes."""
    match = re.fullmatch(r"([\d]+(?:\.\d+)?)\s*([KMG])?B?", size_str.strip().upper())
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid size format: {size_str!r}. Use formats like 10M or 500KB."
        )

    value = float(match.group(1))
    unit = match.group(2)
    size = value * SIZE_UNITS[unit] if unit else value
    if size <= 0:
        raise argparse.ArgumentTypeError("The target size must be greater than zero.")
    return int(size)


def format_size(size: int) -> str:
    """Format bytes using binary units."""
    if size >= 1024**2:
        return f"{size / 1024**2:.2f}MB"
    if size >= 1024:
        return f"{size / 1024:.0f}KB"
    return f"{size}B"


def is_within(path: Path, directory: Path) -> bool:
    """Return whether path is directory itself or one of its descendants."""
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def iter_images(
    source_dir: Path, excluded_dirs: Iterable[Path]
) -> Iterable[Path]:
    """Yield supported images recursively, excluding output/template folders."""
    excluded = [directory.resolve() for directory in excluded_dirs]
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        resolved = path.resolve()
        if any(is_within(resolved, directory) for directory in excluded):
            continue
        yield path


def template_name_for(image: Image.Image) -> str:
    """Choose a template name based on exact 4:3 or 16:9 aspect ratio."""
    width, height = image.size
    horizontal = width >= height

    if horizontal and width * 3 == height * 4:
        return "4-3-h.png"
    if not horizontal and height * 3 == width * 4:
        return "4-3-v.png"
    if horizontal and width * 9 == height * 16:
        return "16-9-h.png"
    if not horizontal and height * 9 == width * 16:
        return "16-9-v.png"
    return "16-9-h.png" if horizontal else "4-3-v.png"


def prepare_base(image: Image.Image, image_format: str) -> Image.Image:
    """Normalize orientation and color mode before compositing."""
    image = ImageOps.exif_transpose(image)
    if image_format == "JPEG":
        return image.convert("RGB")
    if image.mode not in ("RGBA", "RGB"):
        return image.convert("RGBA")
    return image


def save_candidate(
    image: Image.Image,
    output_path: Path,
    image_format: str,
    quality: int,
) -> None:
    """Save one output candidate with format-specific optimization."""
    save_kwargs: dict[str, object] = {}
    if image_format == "JPEG":
        save_kwargs.update(
            quality=quality,
            optimize=True,
            progressive=True,
        )
    elif image_format == "WEBP":
        save_kwargs.update(quality=quality, method=6)
    elif image_format == "PNG":
        save_kwargs.update(optimize=True, compress_level=9)

    image.save(output_path, format=image_format, **save_kwargs)


def save_with_size_limit(
    image: Image.Image,
    output_path: Path,
    image_format: str,
    max_bytes: int | None,
) -> tuple[int, bool]:
    """Save an image, optionally adjusting quality and dimensions to a limit."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".image-watermark-", dir=output_path.parent
    ) as temp_dir:
        candidate_path = Path(temp_dir) / output_path.name
        best_path = Path(temp_dir) / f"best-{output_path.name}"

        if max_bytes is None:
            save_candidate(image, candidate_path, image_format, DEFAULT_QUALITY)
            result_size = candidate_path.stat().st_size
            candidate_path.replace(output_path)
            return result_size, True

        qualities = (
            list(range(95, 9, -5))
            if image_format in {"JPEG", "WEBP"}
            else [95]
        )
        best_size: int | None = None
        reached_target = False
        scale = 1.0

        while scale >= 0.2:
            if scale == 1.0:
                candidate = image
            else:
                width = max(1, int(image.width * scale))
                height = max(1, int(image.height * scale))
                candidate = image.resize((width, height), Image.Resampling.LANCZOS)

            for quality in qualities:
                save_candidate(candidate, candidate_path, image_format, quality)
                candidate_size = candidate_path.stat().st_size
                if best_size is None or candidate_size < best_size:
                    shutil.copyfile(candidate_path, best_path)
                    best_size = candidate_size
                if candidate_size <= max_bytes:
                    candidate_path.replace(output_path)
                    reached_target = True
                    if candidate is not image:
                        candidate.close()
                    return candidate_size, reached_target

            if candidate is not image:
                candidate.close()
            scale *= 0.9

        if best_size is None:
            raise RuntimeError("Could not create an output image")
        best_path.replace(output_path)
        return best_size, reached_target


def apply_watermark(
    image_path: Path,
    template_dir: Path,
    output_path: Path,
    max_bytes: int | None,
) -> tuple[str, int, bool]:
    """Apply the selected template and save the result."""
    with Image.open(image_path) as source:
        image_format = (source.format or image_path.suffix.lstrip(".")).upper()
        if image_format == "JPG":
            image_format = "JPEG"
        if image_format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError(f"Unsupported image format: {image_format}")

        base = prepare_base(source, image_format)
        template_name = template_name_for(base)
        template_path = template_dir / template_name
        if not template_path.is_file():
            raise FileNotFoundError(f"Watermark template not found: {template_path}")

        with Image.open(template_path) as source_template:
            template = source_template.convert("RGBA")
            template_height = max(
                1, round(template.height * base.width / template.width)
            )
            template = template.resize(
                (base.width, template_height), Image.Resampling.LANCZOS
            )

        canvas = base.convert("RGBA")
        top = canvas.height - template.height
        if top < 0:
            # Keep the template's bottom edge aligned and crop only its top.
            template = template.crop((0, -top, template.width, template.height))
            top = 0
        canvas.alpha_composite(template, (0, top))
        result = canvas.convert("RGB") if image_format == "JPEG" else canvas

        result_size, reached_target = save_with_size_limit(
            result, output_path, image_format, max_bytes
        )
        return template_name, result_size, reached_target


def process_directory(
    source: str,
    watermark_dir: str | None = None,
    output_dir: str | None = None,
    max_size: int | None = None,
) -> int:
    """Process all supported images in a directory recursively."""
    source_path = Path(source).expanduser()
    if not source_path.is_dir():
        print(f"Input directory not found: {source}", file=sys.stderr)
        return 1

    template_path = (
        Path(watermark_dir).expanduser()
        if watermark_dir
        else source_path / "watermark"
    )
    output_path = (
        Path(output_dir).expanduser()
        if output_dir
        else source_path / "processed"
    )
    if not template_path.is_dir():
        print(f"Watermark directory not found: {template_path}", file=sys.stderr)
        return 1

    source_resolved = source_path.resolve()
    output_resolved = output_path.resolve()
    template_resolved = template_path.resolve()
    if output_resolved == source_resolved:
        print("Output directory must not be the input directory.", file=sys.stderr)
        return 1
    if output_resolved == template_resolved or is_within(
        output_resolved, template_resolved
    ):
        print(
            "Output directory must not be the watermark directory or its child.",
            file=sys.stderr,
        )
        return 1

    output_path.mkdir(parents=True, exist_ok=True)
    images = list(iter_images(source_path, (output_path, template_path)))
    print(f"Watermark directory: {template_path}")
    print(f"Output directory: {output_path}")
    if not images:
        print("No supported image files found.")
        return 0
    print(f"Found {len(images)} image(s)")

    processed = failed = 0
    for image_path in images:
        relative_path = image_path.relative_to(source_path)
        destination = output_path / relative_path
        try:
            template_name, result_size, reached_target = apply_watermark(
                image_path, template_path, destination, max_size
            )
            status = ""
            if max_size is not None and not reached_target:
                status = " (target not reached)"
            processed += 1
            print(
                f"Processed: {relative_path} "
                f"[{template_name}] -> {format_size(result_size)}{status}"
            )
        except Exception as error:
            failed += 1
            print(f"Failed: {relative_path}: {error}")

    print(f"Summary: {processed} processed, {failed} failed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply aspect-ratio-specific watermark templates recursively."
    )
    parser.add_argument("directory", help="Directory containing photos")
    parser.add_argument(
        "-w",
        "--watermark-dir",
        help="Watermark template directory (default: <directory>/watermark)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory (default: <directory>/processed)",
    )
    parser.add_argument(
        "-s",
        "--max-size",
        type=parse_size,
        help="Optional maximum output size, e.g. 10M, 500K",
    )
    args = parser.parse_args()
    return process_directory(args.directory, args.watermark_dir, args.output, args.max_size)


if __name__ == "__main__":
    raise SystemExit(main())
