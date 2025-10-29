#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

CUR = Path(__file__).resolve().parent
ROOT = CUR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.ai_motion import animate_image, MotionSpec


def main() -> None:
    ap = argparse.ArgumentParser(description="Animate single image with AI segmentation + parallax")
    ap.add_argument("image_url", type=str)
    ap.add_argument("--out", type=str, default="motion.mp4")
    ap.add_argument("--duration", type=float, default=5.0)
    ap.add_argument("--zoom_fg", type=float, default=1.06)
    ap.add_argument("--zoom_bg", type=float, default=1.02)
    args = ap.parse_args()

    spec = MotionSpec(duration=args.duration, zoom_fg=args.zoom_fg, zoom_bg=args.zoom_bg)
    animate_image(args.image_url, args.out, spec)
    print(f"Done. MP4: {args.out}")


if __name__ == "__main__":
    main()
