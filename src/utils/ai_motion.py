import io
import os
import tempfile
import subprocess
import requests
from dataclasses import dataclass
from typing import Optional
from PIL import Image
from rembg import remove


@dataclass
class MotionSpec:
    width: int = 1080
    height: int = 1920
    duration: float = 5.0
    fps: int = 30
    zoom_fg: float = 1.06
    zoom_bg: float = 1.02
    blur_bg: int = 20


def download_image(url: str) -> Image.Image:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGBA")


def segment_foreground(img: Image.Image) -> Image.Image:
    # rembg returns RGBA with transparent background
    out = remove(img)
    if not isinstance(out, Image.Image):
        out = Image.open(io.BytesIO(out)).convert("RGBA")
    return out


def composite_layers(fg: Image.Image, bg: Image.Image, spec: MotionSpec) -> tuple[str, str]:
    # Save separate PNGs for fg and bg, both at canvas size with transparency
    canvas = (spec.width, spec.height)
    # Fit background: cover
    bg_fit = bg.convert("RGB")
    bg_fit = bg_fit.resize(canvas, Image.LANCZOS)
    # Foreground: fit contain
    fg_fit = fg.copy()
    fg_fit.thumbnail(canvas, Image.LANCZOS)
    # Center place fg on transparent canvas
    fg_canvas = Image.new("RGBA", canvas, (0,0,0,0))
    x = (canvas[0] - fg_fit.width)//2
    y = (canvas[1] - fg_fit.height)//2
    fg_canvas.paste(fg_fit, (x,y), fg_fit)

    tmpdir = tempfile.mkdtemp()
    fg_path = os.path.join(tmpdir, "fg.png")
    bg_path = os.path.join(tmpdir, "bg.png")
    fg_canvas.save(fg_path)
    bg_fit.save(bg_path)
    return fg_path, bg_path


def render_parallax(fg_path: str, bg_path: str, out_mp4: str, spec: MotionSpec) -> None:
    w, h = spec.width, spec.height
    frames = int(spec.duration * spec.fps)
    # Build zoom expressions
    zfg = f"zoom='1+({spec.zoom_fg}-1)*on/{frames}'"
    zbg = f"zoom='1+({spec.zoom_bg}-1)*on/{frames}'"

    filter_complex = (
        f"[0:v]scale={w}:{h},boxblur={spec.blur_bg}:1,zoompan={zbg}:d={frames}:s={w}x{h}[bg];"
        f"[1:v]scale={w}:{h},zoompan={zfg}:d={frames}:s={w}x{h}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{spec.duration:.3f}", "-i", bg_path,
        "-loop", "1", "-t", f"{spec.duration:.3f}", "-i", fg_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-r", str(spec.fps),
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        out_mp4,
    ]
    subprocess.run(cmd, check=True)


def animate_image(url: str, out_mp4: str, spec: Optional[MotionSpec] = None) -> None:
    spec = spec or MotionSpec()
    img = download_image(url)
    fg = segment_foreground(img)
    # Background as original without alpha
    bg = img.convert("RGB")
    fg_path, bg_path = composite_layers(fg, bg, spec)
    render_parallax(fg_path, bg_path, out_mp4, spec)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AI Motion: segment foreground and animate parallax")
    p.add_argument("image_url", type=str)
    p.add_argument("--out", type=str, default="motion.mp4")
    p.add_argument("--duration", type=float, default=5.0)
    args = p.parse_args()

    spec = MotionSpec(duration=args.duration)
    animate_image(args.image_url, args.out, spec)
