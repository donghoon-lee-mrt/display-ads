import io
import os
import tempfile
import subprocess
import requests
import numpy as np
from dataclasses import dataclass
from typing import Optional
from PIL import Image
import cv2


@dataclass
class MotionSpec:
    width: int = 1080
    height: int = 1920
    duration: float = 5.0
    fps: int = 30
    zoom_near: float = 1.06  # foreground zoom factor
    zoom_far: float = 1.01   # background zoom factor
    blur_bg: int = 12


def download_image(url: str) -> Image.Image:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def fit_to_canvas(img_rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = img_rgb.shape[:2]
    scale = min(width / w, height / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img_rgb, (nw, nh), interpolation=cv2.INTER_CUBIC)
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = (width - nw) // 2
    y = (height - nh) // 2
    canvas[y:y+nh, x:x+nw] = resized
    return canvas


def grabcut_foreground(img_bgr: np.ndarray) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    rect_w, rect_h = int(w * 0.6), int(h * 0.6)
    rx = (w - rect_w) // 2
    ry = (h - rect_h) // 2
    rect = (rx, ry, rect_w, rect_h)

    mask = np.zeros((h, w), np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    cv2.grabCut(img_bgr, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype('uint8')
    # Feather edges
    mask2 = cv2.GaussianBlur(mask2, (0, 0), 3)
    return mask2


def render_parallax(img: Image.Image, out_mp4: str, spec: MotionSpec) -> None:
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    canvas = fit_to_canvas(img_bgr, spec.width, spec.height)

    mask_fg = grabcut_foreground(canvas)
    mask_fg_3 = cv2.cvtColor(mask_fg, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
    mask_bg_3 = 1.0 - mask_fg_3

    frames = int(spec.duration * spec.fps)
    tmpdir = tempfile.mkdtemp()
    pattern = os.path.join(tmpdir, "frame_%05d.png")

    for t in range(frames):
        a_near = 1.0 + (spec.zoom_near - 1.0) * (t / frames)
        a_far  = 1.0 + (spec.zoom_far  - 1.0) * (t / frames)

        near = cv2.resize(canvas, None, fx=a_near, fy=a_near, interpolation=cv2.INTER_CUBIC)
        far  = cv2.resize(canvas, None, fx=a_far,  fy=a_far,  interpolation=cv2.INTER_CUBIC)
        far  = cv2.GaussianBlur(far, (0,0), spec.blur_bg)

        def center_crop(imgx):
            h2, w2 = imgx.shape[:2]
            sx = max(0, (w2 - spec.width)//2)
            sy = max(0, (h2 - spec.height)//2)
            return imgx[sy:sy+spec.height, sx:sx+spec.width]

        near_c = center_crop(near)
        far_c  = center_crop(far)

        comp = (near_c.astype(np.float32) * mask_fg_3 + far_c.astype(np.float32) * mask_bg_3).astype(np.uint8)
        cv2.imwrite(pattern % t, comp)

    ff_cmd = [
        "ffmpeg", "-y", "-r", str(spec.fps), "-i", os.path.join(tmpdir, "frame_%05d.png"),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_mp4
    ]
    subprocess.run(ff_cmd, check=True)


def animate_image_grabcut(url: str, out_mp4: str, spec: Optional[MotionSpec] = None) -> None:
    spec = spec or MotionSpec()
    img = download_image(url)
    render_parallax(img, out_mp4, spec)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AI Motion (GrabCut): parallax animation without external models")
    p.add_argument("image_url", type=str)
    p.add_argument("--out", type=str, default="motion_grabcut.mp4")
    p.add_argument("--duration", type=float, default=5.0)
    args = p.parse_args()

    spec = MotionSpec(duration=args.duration)
    animate_image_grabcut(args.image_url, args.out, spec)
