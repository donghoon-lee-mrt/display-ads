import os
import math
import json
import tempfile
import subprocess
import urllib.parse
import requests
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CanvasSpec:
    width: int = 1080
    height: int = 1920
    duration: float = 15.0
    fps: int = 30


@dataclass
class ClipSpec:
    url: str
    duration: float
    motion: str = "kenburns_in"  # or "none"
    fit: str = "blur_pad"        # or "fit", "cover"


class ImageSlideshowRenderer:
    def __init__(self, canvas: CanvasSpec) -> None:
        self.canvas = canvas

    def _download_images(self, urls: List[str], workdir: str) -> List[str]:
        paths: List[str] = []
        for idx, url in enumerate(urls):
            parsed = urllib.parse.urlparse(url)
            ext = os.path.splitext(parsed.path)[1] or ".jpg"
            out_path = os.path.join(workdir, f"img_{idx:02d}{ext}")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            paths.append(out_path)
        return paths

    def _build_ffmpeg_filter(self, image_path: str, clip: ClipSpec, stream_idx: int) -> str:
        w, h = self.canvas.width, self.canvas.height
        # Background blur pad: scale to fill height, then gaussian blur, then overlay center crop
        # Generate two streams: bg (blurred) and fg (fitted image)
        # Note: Use scale and boxblur for background, then overlay fg scaled to fit within canvas
        zoom_start = 1.0
        zoom_end = 1.05 if clip.motion == "kenburns_in" else 1.0
        frames = int(clip.duration * self.canvas.fps)
        zoom_expr = f"zoom='if(lte(on,1),{zoom_start},if(lte(on,{frames}),{zoom_start}+({zoom_end}-{zoom_start})*on/{frames},{zoom_end}))'"

        # Foreground fit (contain)
        fg = (
            f"[{stream_idx}:v]scale=w=min(iw*{h}/ih\,{w}):h=min({h}\,ih*{w}/iw),pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )
        # Background from same image, scaled to cover then heavy blur
        bg = (
            f"[{stream_idx}:v]scale=w={w}:h={h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:1,setsar=1"
        )
        # Zoom on foreground layer
        zoom = f",zoompan={zoom_expr}:d={frames}:s={w}x{h}"
        # Overlay fg over bg
        chain = f"{bg}[bg];{fg}{zoom}[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p"
        return chain

    def render(self, clips: List[ClipSpec], output_mp4: str, thumb_jpg: Optional[str] = None) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            # 1) Download images
            image_paths = self._download_images([c.url for c in clips], workdir)

            # 2) Build inputs
            cmd = ["ffmpeg", "-y"]
            filter_chains = []
            concat_inputs = []
            label_idx = 0

            for i, (img, clip) in enumerate(zip(image_paths, clips)):
                # For each clip, create a short video segment from single image with motion
                # Input
                cmd += ["-loop", "1", "-t", f"{clip.duration:.3f}", "-i", img]

            # 3) Build filter_complex per clip to produce segments, then concat
            # Build chain per stream index
            seg_labels = []
            for i, clip in enumerate(clips):
                chain = self._build_ffmpeg_filter(f"img_{i:02d}", clip, i)
                filter_chains.append(chain + f"[v{i}]")
                seg_labels.append(f"[v{i}]")

            # Concat all segments
            concat = f"{''.join(seg_labels)}concat=n={len(clips)}:v=1:a=0[vout]"
            filter_complex = ";".join(filter_chains + [concat])

            cmd += [
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-r", str(self.canvas.fps),
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                "-t", f"{self.canvas.duration:.3f}",
                output_mp4,
            ]

            subprocess.run(cmd, check=True)

            if thumb_jpg:
                subprocess.run([
                    "ffmpeg", "-y", "-i", output_mp4, "-vf", "thumbnail,scale=540:-1", "-frames:v", "1", thumb_jpg
                ], check=True)


def build_default_clips(image_urls: List[str], total_duration: float = 15.0, num_clips: int = 4) -> List[ClipSpec]:
    if not image_urls:
        raise ValueError("image_urls is empty")
    take = min(num_clips, len(image_urls))
    per = total_duration / take
    return [ClipSpec(url=image_urls[i], duration=per, motion="kenburns_in", fit="blur_pad") for i in range(take)]


def fetch_header_images(product_id: str) -> List[str]:
    api = f"https://api3.myrealtrip.com/traveler-experiences/api/web/v2/traveler/products/{product_id}/header"
    r = requests.get(api, timeout=30)
    r.raise_for_status()
    data = r.json().get("data", {})
    urls = [img.get("url") for img in data.get("images", []) if isinstance(img, dict) and img.get("url")]
    return urls


def render_from_product(product_id: str, output_mp4: str, thumb_jpg: Optional[str] = None) -> None:
    urls = fetch_header_images(product_id)
    clips = build_default_clips(urls, total_duration=15.0, num_clips=4)
    renderer = ImageSlideshowRenderer(CanvasSpec())
    renderer.render(clips, output_mp4=output_mp4, thumb_jpg=thumb_jpg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render 15s vertical slideshow from product header images")
    parser.add_argument("product_id", type=str, help="Product ID (e.g., 3149960)")
    parser.add_argument("--out", type=str, default="output.mp4", help="Output MP4 path")
    parser.add_argument("--thumb", type=str, default="thumb.jpg", help="Output thumbnail path")
    args = parser.parse_args()

    render_from_product(args.product_id, output_mp4=args.out, thumb_jpg=args.thumb)
