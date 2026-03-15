#!/usr/bin/env python3
"""Convert PNG images to SVG format using image tracing."""

import argparse
import base64
import subprocess
import sys
from pathlib import Path


def png_to_svg_embedded(png_path: Path, output_path: Path) -> None:
    """Convert PNG to SVG by embedding the image as base64."""
    with open(png_path, "rb") as f:
        png_data = base64.b64encode(f.read()).decode("utf-8")
    
    # Get image dimensions using sips (macOS built-in)
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png_path)],
        capture_output=True,
        text=True
    )
    
    width, height = 100, 100
    for line in result.stdout.split("\n"):
        if "pixelWidth" in line:
            width = int(line.split(":")[-1].strip())
        elif "pixelHeight" in line:
            height = int(line.split(":")[-1].strip())
    
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
     width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <image width="{width}" height="{height}" 
         xlink:href="data:image/png;base64,{png_data}"/>
</svg>'''
    
    with open(output_path, "w") as f:
        f.write(svg_content)


def png_to_svg_traced(png_path: Path, output_path: Path) -> None:
    """Convert PNG to SVG using potrace for vector tracing."""
    # Check if potrace is available
    potrace_check = subprocess.run(["which", "potrace"], capture_output=True)
    if potrace_check.returncode != 0:
        print("Warning: potrace not found. Install with: brew install potrace")
        print("Falling back to embedded mode...")
        png_to_svg_embedded(png_path, output_path)
        return
    
    pbm_path = png_path.with_suffix(".pbm")
    
    # Use sips to convert PNG directly to PBM (macOS built-in)
    subprocess.run(
        ["sips", "-s", "format", "pbm", str(png_path), "--out", str(pbm_path)],
        capture_output=True,
        check=True
    )
    
    # Run potrace
    subprocess.run(
        ["potrace", "-s", "-o", str(output_path), str(pbm_path)],
        check=True
    )
    
    # Clean up temp file
    pbm_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="Convert PNG to SVG")
    parser.add_argument("input", help="Input PNG file path")
    parser.add_argument("-o", "--output", help="Output SVG file path")
    parser.add_argument(
        "-m", "--mode",
        choices=["embed", "trace"],
        default="trace",
        help="Conversion mode: 'trace' (default) creates vector paths, 'embed' embeds PNG as base64"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == ".png":
        print("Warning: Input file may not be a PNG file")
    
    output_path = Path(args.output) if args.output else input_path.with_suffix(".svg")
    
    print(f"Converting {input_path} to {output_path} (mode: {args.mode})")
    
    if args.mode == "trace":
        png_to_svg_traced(input_path, output_path)
    else:
        png_to_svg_embedded(input_path, output_path)
    
    print(f"Done! Output saved to: {output_path}")


if __name__ == "__main__":
    main()
