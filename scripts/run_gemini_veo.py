#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

CUR = Path(__file__).resolve().parent
ROOT = CUR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from generators.gemini.veo import generate_video_from_image, GeminiVeoGenerator


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate video from image using Gemini Veo 3")
    ap.add_argument("image_url", type=str, help="URL of the image to animate")
    ap.add_argument("--out", type=str, default="gemini_veo_output.mp4")
    ap.add_argument("--prompt", type=str, default="A person in the image moving naturally with subtle breathing, slight head movements, and gentle eye blinking")
    
    args = ap.parse_args()
    
    try:
        result = generate_video_from_image(args.image_url, args.prompt, args.out)
        print(f"✅ Success! Video saved: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Setup needed:")
        print("1. Get API key: https://aistudio.google.com/app/apikey")
        print("2. export GEMINI_API_KEY=your-api-key")


if __name__ == "__main__":
    main()