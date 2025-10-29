#!/usr/bin/env python3
import argparse
import os
import re
from urllib.parse import urlparse

from pathlib import Path
import sys

# Allow import from src/
CUR = Path(__file__).resolve().parent
ROOT = CUR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.image_slideshow import render_from_product


def extract_product_id(input_str: str) -> str:
    # Accept raw numeric or URL containing /products/{id}
    m = re.search(r"/products/(\d+)", input_str)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d+", input_str):
        return input_str
    raise ValueError("Could not extract product_id from input. Provide numeric ID or product URL.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch header images and render slideshow")
    parser.add_argument("product", type=str, help="Product ID or product URL")
    parser.add_argument("--out", type=str, default="output.mp4")
    parser.add_argument("--thumb", type=str, default="thumb.jpg")
    args = parser.parse_args()

    pid = extract_product_id(args.product)
    render_from_product(pid, output_mp4=args.out, thumb_jpg=args.thumb)
    print(f"Done. MP4: {args.out} | Thumb: {args.thumb}")


if __name__ == "__main__":
    main()
