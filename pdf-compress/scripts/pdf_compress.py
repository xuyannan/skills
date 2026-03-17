#!/usr/bin/env python3
"""Compress PDF files to a target size using Ghostscript."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# Ghostscript quality presets (from lowest to highest quality)
QUALITY_PRESETS = {
    "screen":  {"dpi": 72,  "desc": "低质量，最小体积，适合屏幕浏览"},
    "ebook":   {"dpi": 150, "desc": "中等质量，适合电子书和一般阅读"},
    "printer": {"dpi": 300, "desc": "较高质量，适合打印"},
    "prepress": {"dpi": 300, "desc": "最高质量，适合印前处理"},
}

DEFAULT_QUALITY = "ebook"

SIZE_UNITS = {"K": 1024, "M": 1024 * 1024, "G": 1024 * 1024 * 1024}


def parse_size(size_str: str) -> float:
    """Parse human-readable size string (e.g. '5M', '500K') to bytes."""
    match = re.match(r'^([\d.]+)\s*([KMG])?B?$', size_str.strip().upper())
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid size format: '{size_str}'. Use formats like 500K, 5M, 10M"
        )
    value = float(match.group(1))
    unit = match.group(2)
    if unit:
        return value * SIZE_UNITS[unit]
    return value


def format_size(size_bytes: float) -> str:
    """Format bytes to human-readable string."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f}MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f}KB"
    else:
        return f"{size_bytes:.0f}B"


def check_ghostscript() -> str:
    """Check if Ghostscript is installed and return its path."""
    gs_path = shutil.which("gs")
    if not gs_path:
        print("Error: Ghostscript (gs) is not installed.")
        print("Install it with: brew install ghostscript")
        sys.exit(1)
    return gs_path


def compress_pdf_gs(input_path: Path, output_path: Path, quality: str, dpi: int) -> bool:
    """Compress a PDF using Ghostscript with given quality and DPI settings."""
    gs_path = check_ghostscript()

    cmd = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        "-dColorImageDownsampleType=/Bicubic",
        "-dGrayImageDownsampleType=/Bicubic",
        "-dMonoImageDownsampleType=/Bicubic",
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dDownsampleMonoImages=true",
        f"-sOutputFile={output_path}",
        str(input_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  Warning: Compression timed out for {input_path.name}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def compress_to_target_size(
    input_path: Path, output_path: Path, max_bytes: float, quality: str
) -> bool:
    """Compress PDF, iteratively lowering DPI to meet target size."""
    original_size = input_path.stat().st_size

    # If already under target, just copy
    if original_size <= max_bytes:
        shutil.copy2(input_path, output_path)
        return True

    # Try the preset DPI first
    base_dpi = QUALITY_PRESETS[quality]["dpi"]
    dpi_steps = [base_dpi]

    # Build a descending list of DPIs to try
    for dpi in [200, 150, 120, 100, 72, 50, 36]:
        if dpi < base_dpi and dpi not in dpi_steps:
            dpi_steps.append(dpi)
    dpi_steps.sort(reverse=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_output = Path(tmpdir) / "compressed.pdf"

        for dpi in dpi_steps:
            if compress_pdf_gs(input_path, tmp_output, quality, dpi):
                compressed_size = tmp_output.stat().st_size
                if compressed_size <= max_bytes:
                    shutil.copy2(tmp_output, output_path)
                    return True
                # If even at this DPI it's too large but smaller than original,
                # keep trying lower DPI
            if tmp_output.exists():
                tmp_output.unlink()

        # If we couldn't hit target with quality preset, try 'screen' at very low DPI
        if quality != "screen":
            for dpi in [72, 50, 36]:
                if compress_pdf_gs(input_path, tmp_output, "screen", dpi):
                    compressed_size = tmp_output.stat().st_size
                    if compressed_size <= max_bytes:
                        shutil.copy2(tmp_output, output_path)
                        return True
                if tmp_output.exists():
                    tmp_output.unlink()

        # Last resort: use the best result we got (smallest file)
        # Re-run with lowest settings
        if compress_pdf_gs(input_path, tmp_output, "screen", 36):
            shutil.copy2(tmp_output, output_path)
            compressed_size = output_path.stat().st_size
            if compressed_size < original_size:
                print(f"  Warning: Could not reach target {format_size(max_bytes)}, "
                      f"best result: {format_size(compressed_size)}")
                return True

    return False


def compress_pdfs(
    path: str,
    output_dir: str = None,
    max_size: float = None,
    quality: str = DEFAULT_QUALITY,
    overwrite: bool = False,
) -> None:
    """Compress PDF file(s)."""
    input_path = Path(path)

    if not input_path.exists():
        print(f"Path not found: {path}")
        sys.exit(1)

    # Collect PDF files
    if input_path.is_file():
        if not input_path.suffix.lower() == ".pdf":
            print(f"Not a PDF file: {path}")
            sys.exit(1)
        pdf_files = [input_path]
        base_dir = input_path.parent
    else:
        pdf_files = sorted(input_path.glob("*.pdf")) + sorted(input_path.glob("*.PDF"))
        base_dir = input_path

    if not pdf_files:
        print("No PDF files found.")
        return

    # Setup output directory
    if overwrite:
        out_path = None  # will overwrite in place
    elif output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = base_dir / "compressed_output"
        out_path.mkdir(parents=True, exist_ok=True)

    if out_path:
        print(f"Output directory: {out_path}")
    print(f"Quality preset: {quality} ({QUALITY_PRESETS[quality]['desc']})")
    if max_size:
        print(f"Target max size: {format_size(max_size)}")
    print(f"Found {len(pdf_files)} PDF file(s)\n")

    success_count = 0
    for pdf_file in pdf_files:
        original_size = pdf_file.stat().st_size

        if overwrite:
            # Compress to temp then replace original
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            final_output = pdf_file
        else:
            tmp_path = None
            final_output = out_path / pdf_file.name

        compress_target = tmp_path if overwrite else final_output

        if max_size:
            ok = compress_to_target_size(pdf_file, compress_target, max_size, quality)
        else:
            dpi = QUALITY_PRESETS[quality]["dpi"]
            ok = compress_pdf_gs(pdf_file, compress_target, quality, dpi)

        if ok:
            if overwrite and tmp_path:
                shutil.move(str(tmp_path), str(final_output))

            compressed_size = final_output.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            print(
                f"✓ {pdf_file.name}: {format_size(original_size)} → {format_size(compressed_size)} "
                f"(reduced {ratio:.1f}%)"
            )
            success_count += 1
        else:
            if overwrite and tmp_path and tmp_path.exists():
                tmp_path.unlink()
            print(f"✗ {pdf_file.name}: compression failed")

    print(f"\nDone: {success_count}/{len(pdf_files)} file(s) compressed successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compress PDF files using Ghostscript",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.pdf                    # Compress single file (ebook quality)
  %(prog)s ./pdfs                          # Compress all PDFs in directory
  %(prog)s document.pdf -s 5M             # Compress to under 5MB
  %(prog)s document.pdf -s 500K           # Compress to under 500KB
  %(prog)s ./pdfs -q screen               # Use lowest quality for smallest size
  %(prog)s document.pdf -s 2M --overwrite # Overwrite original file
        """,
    )
    parser.add_argument("path", help="PDF file or directory containing PDF files")
    parser.add_argument("-o", "--output", help="Output directory (default: <path>/compressed_output)")
    parser.add_argument(
        "-s", "--max-size", type=parse_size,
        help="Target max file size, e.g. 500K, 5M, 10M"
    )
    parser.add_argument(
        "-q", "--quality", choices=list(QUALITY_PRESETS.keys()),
        default=DEFAULT_QUALITY,
        help=f"Quality preset (default: {DEFAULT_QUALITY})"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite original PDF files (use with caution!)"
    )
    args = parser.parse_args()

    compress_pdfs(args.path, args.output, args.max_size, args.quality, args.overwrite)
