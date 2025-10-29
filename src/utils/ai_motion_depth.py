import io
import os
import urllib.request
import tempfile
import subprocess
import requests
import numpy as np
from dataclasses import dataclass
from typing import Optional
from PIL import Image
import cv2


MidasURL = "https://github.com/isl-org/MiDaS/releases/download/v3/dpt_slim_384.onnx"


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


def ensure_midas_model() -> str:
    cache_dir = os.path.join(tempfile.gettempdir(), "mrt_midas")
    os.makedirs(cache_dir, exist_ok=True)
    model_path = os.path.join(cache_dir, "dpt_slim_384.onnx")
    if not os.path.exists(model_path):
        urllib.request.urlretrieve(MidasURL, model_path)
    return model_path


def estimate_depth(img: np.ndarray, model_path: str) -> np.ndarray:
    # img: HxWx3 BGR
    net = cv2.dnn.readNetFromONNX(model_path)
    inp = cv2.dnn.blobFromImage(img, 1/255.0, (384, 384), mean=(0.485,0.456,0.406), swapRB=True, crop=False)
    net.setInput(inp)
    depth = net.forward()  # shape: 1x1x384x384
    depth = depth[0,0]
    depth = cv2.resize(depth, (img.shape[1], img.shape[0]))
    # Normalize near/far to 0..1 (near higher values)
    depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-6)
    return depth


def render_depth_parallax(img: Image.Image, out_mp4: str, spec: MotionSpec) -> None:
    # Prepare canvas
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    # Fit to canvas with padding (contain)
    canvas = np.zeros((spec.height, spec.width, 3), dtype=np.uint8)
    h, w = img_bgr.shape[:2]
    scale = min(spec.width / w, spec.height / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_CUBIC)
    x = (spec.width - nw) // 2
    y = (spec.height - nh) // 2
    canvas[y:y+nh, x:x+nw] = resized

    # Estimate depth on canvas
    model_path = ensure_midas_model()
    depth = estimate_depth(canvas, model_path)

    # Create motion by splitting into layers via depth threshold
    mask_near = (depth >= 0.5).astype(np.uint8)  # foreground approx
    mask_far = 1 - mask_near

    frames = int(spec.duration * spec.fps)
    tmpdir = tempfile.mkdtemp()
    pattern = os.path.join(tmpdir, "frame_%05d.png")

    for t in range(frames):
        alpha_near = 1.0 + (spec.zoom_near - 1.0) * (t / frames)
        alpha_far  = 1.0 + (spec.zoom_far  - 1.0) * (t / frames)
        # Zoom near/far differently
        near = cv2.resize(canvas, None, fx=alpha_near, fy=alpha_near, interpolation=cv2.INTER_CUBIC)
        far  = cv2.resize(canvas, None, fx=alpha_far,  fy=alpha_far,  interpolation=cv2.INTER_CUBIC)
        far  = cv2.GaussianBlur(far, (0,0), spec.blur_bg)

        # Center-crop back to canvas size
        def center_crop(imgx):
            h2, w2 = imgx.shape[:2]
            sx = max(0, (w2 - spec.width)//2)
            sy = max(0, (h2 - spec.height)//2)
            return imgx[sy:sy+spec.height, sx:sx+spec.width]

        near_c = center_crop(near)
        far_c  = center_crop(far)

        # Composite with mask
        mask3 = np.dstack([mask_near*255]*3).astype(np.uint8)
        invmask3 = 255 - mask3
        comp = ((near_c * (mask3/255.0)) + (far_c * (invmask3/255.0))).astype(np.uint8)
        cv2.imwrite(pattern % t, comp)

    # Encode with ffmpeg
    ff_cmd = [
        "ffmpeg", "-y", "-r", str(spec.fps), "-i", os.path.join(tmpdir, "frame_%05d.png"),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_mp4
    ]
    subprocess.run(ff_cmd, check=True)


def animate_image_depth(url: str, out_mp4: str, spec: Optional[MotionSpec] = None) -> None:
    spec = spec or MotionSpec()
    img = download_image(url)
    render_depth_parallax(img, out_mp4, spec)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AI Motion Depth: MiDaS parallax animation")
    p.add_argument("image_url", type=str)
    p.add_argument("--out", type=str, default="motion_depth.mp4")
    p.add_argument("--duration", type=float, default=5.0)
    args = p.parse_args()

    spec = MotionSpec(duration=args.duration)
    animate_image_depth(args.image_url, args.out, spec)
