#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

CUR = Path(__file__).resolve().parent
ROOT = CUR.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from generators.veo.video import generate_video_from_url, VeoSpec


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate video from image using Veo on Vertex AI")
    ap.add_argument("image_url", type=str, help="URL of the image to animate")
    ap.add_argument("--out", type=str, default="veo_output.mp4")
    ap.add_argument("--prompt", type=str, default="A person in the image moving naturally with subtle movements, breathing, slight head movement")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--resolution", type=str, default="1080p", choices=["480p", "720p", "1080p"])
    ap.add_argument("--motion", type=str, default="medium", choices=["low", "medium", "high"])
    
    args = ap.parse_args()
    
    spec = VeoSpec(
        duration=args.duration,
        resolution=args.resolution,
        motion_intensity=args.motion,
        prompt=args.prompt
    )
    
    try:
        result = generate_video_from_url(args.image_url, args.out, args.prompt, spec)
        print(f"✅ Done. Video: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Setup needed:")
        print("export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("gcloud auth application-default login")


if __name__ == "__main__":
    main()