import streamlit as st
import os
import io
import re
import json
import time
import subprocess
import tempfile
import os
from pathlib import Path
from typing import List
from datetime import date, timedelta
import cv2
import numpy as np
import requests
import time

# 로깅 설정
import logging
from logging.handlers import RotatingFileHandler

def _safe_repr(obj, max_len: int = 2000):
    try:
        s = repr(obj)
        return s if len(s) <= max_len else s[:max_len] + "..."
    except Exception:
        return "<unrepr>"

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return root_logger
    root_logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        filename=os.path.join("logs", "app.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    return root_logger

setup_logging()
logger = logging.getLogger(__name__)

def log_calls(level=logging.INFO):
    def _decorator(func):
        def _wrapper(*args, **kwargs):
            logger_local = logging.getLogger(func.__module__)
            logger_local.log(level, f"START {func.__name__} args=%s kwargs=%s", _safe_repr(args), _safe_repr(kwargs))
            _t0 = time.time()
            try:
                result = func(*args, **kwargs)
                _dt_ms = (time.time() - _t0) * 1000.0
                logger_local.log(level, f"END   {func.__name__} ok in {_dt_ms:.1f}ms")
                return result
            except Exception:
                _dt_ms = (time.time() - _t0) * 1000.0
                logger_local.exception(f"FAIL  {func.__name__} in {_dt_ms:.1f}ms")
                raise
        return _wrapper
    return _decorator

# 페이지 설정
st.set_page_config(
    page_title="🎬 Marketing Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 환경 변수 설정
if 'GOOGLE_API_KEY' not in os.environ:
    os.environ['GOOGLE_API_KEY'] = 'Google api key'

# Gemini 클라이언트 초기화
@log_calls()
@st.cache_resource
def init_gemini_client():
    # 지연 로딩: google-genai가 설치되지 않았어도 앱이 기동되도록 함
    try:
        from google import genai as _genai
        return _genai.Client()
    except Exception as e:
        raise e

try:
    client = init_gemini_client()
except Exception:
    client = None

# API 설정
API_BASE = 'https://api3.myrealtrip.com/traveler-experiences/api/web/v2/traveler/products/{pid}/header'

@log_calls()
def find_first_image_url(obj):
    """재귀적으로 첫 번째 이미지 URL 찾기"""
    if isinstance(obj, dict):
        for v in obj.values():
            u = find_first_image_url(v)
            if u: return u
    elif isinstance(obj, list):
        for v in obj:
            u = find_first_image_url(v)
            if u: return u
    elif isinstance(obj, (str, bytes)):
        s = obj.decode() if isinstance(obj, bytes) else obj
        if re.search(r'\.(jpg|jpeg|png)(\?|$)', s, re.I):
            return s
    return None

@log_calls()
def analyze_images(pid):
    """API에서 이미지 분석하여 후보군 선정"""
    try:
        import requests
        hdr = requests.get(API_BASE.format(pid=pid), timeout=20)
        hdr.raise_for_status()
        data = hdr.json()['data']
        
        candidates = []
        images = data.get('images', [])
        
        # 타입별 카운트
        type_count = {}
        for img_info in images:
            img_type = img_info.get('type', 'UNKNOWN')
            type_count[img_type] = type_count.get(img_type, 0) + 1
        
        # NON_REVIEW 우선, 그 다음 REVIEW
        for priority_type in ['NON_REVIEW', 'REVIEW']:
            for img_info in images:
                url = img_info.get('url', '')
                img_type = img_info.get('type', '')
                
                if img_type != priority_type:
                    continue
                    
                # JPG/JPEG만, PNG/아이콘 제외
                if not re.search(r'\.(jpg|jpeg)(\?|$)', url, re.I):
                    continue
                if 'icon' in url.lower():
                    continue
                    
                candidates.append({
                    'url': url,
                    'type': img_type,
                    'filename': url.split('/')[-1].split('?')[0],
                    'reviewId': img_info.get('reviewId', None)
                })
                
                if len(candidates) >= 8:  # 8개면 충분
                    break
            
            if len(candidates) >= 8:
                break
        
        return candidates, type_count, len(images)
        
    except Exception as e:
        st.error(f"API 호출 오류: {e}")
        return [], {}, 0

@log_calls()
def analyze_accommodation_images(pid: str, check_in: str, check_out: str, adult_count: int = 2, child_count: int = 0):
    """숙소(Union) 추천 API에서 이미지 후보 수집

    참고 엔드포인트:
    https://api3.myrealtrip.com/accommodations/v1/products/{pid}/front/recommendation?checkIn=YYYY-MM-DD&checkOut=YYYY-MM-DD&adultCount=N&childCount=M
    """
    try:
        import requests
        url = (
            "https://api3.myrealtrip.com/accommodations/v1/products/"
            f"{pid}/front/recommendation?checkIn={check_in}&checkOut={check_out}"
            f"&adultCount={adult_count}&childCount={child_count}"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # sections[*].data[*].imageUrls.large / original 등에서 이미지 수집
        sections = data.get('data', {}).get('sections', [])
        candidates = []

        def _pick_image_url(image_urls: dict) -> str:
            if not isinstance(image_urls, dict):
                return ""
            for key in ["large", "original", "medium", "small", "thumb"]:
                url = image_urls.get(key)
                if isinstance(url, str) and re.search(r"\.(jpg|jpeg)(\?|$)", url, re.I):
                    return url
            # fallback: 아무거나 문자열
            for v in image_urls.values():
                if isinstance(v, str):
                    return v
            return ""

        total_items = 0
        for sec in sections:
            items = sec.get('data', []) if isinstance(sec, dict) else []
            total_items += len(items)
            for item in items:
                img_url = _pick_image_url(item.get('imageUrls', {}))
                if not img_url:
                    continue
                if 'icon' in img_url.lower():
                    continue
                candidates.append({
                    'url': img_url,
                    'type': 'ACCOM_RECO',
                    'filename': img_url.split('/')[-1].split('?')[0],
                    'reviewId': None
                })
                if len(candidates) >= 8:
                    break
            if len(candidates) >= 8:
                break

        # type_count 유사 포맷으로 반환
        type_count = { 'ACCOM_RECO': len(candidates) }
        return candidates, type_count, total_items

    except Exception as e:
        st.error(f"숙소 API 호출 오류: {e}")
        return [], {}, 0

@log_calls()
def analyze_bnb_images(product_id: str, start_date: str, end_date: str, adults: int = 1, children: int = 0):
    """한인민박(options) API에서 옵션 썸네일 기반 이미지 후보 수집

    참고 엔드포인트:
    https://api3.myrealtrip.com/product/products/{productId}/options?productId={productId}&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&adults=N&children=M&isReservable=false&roomTypes=
    """
    try:
        import requests
        base = "https://api3.myrealtrip.com/product/products"
        url = (
            f"{base}/{product_id}/options?productId={product_id}"
            f"&startDate={start_date}&endDate={end_date}"
            f"&adults={adults}&children={children}"
            f"&isReservable=false&roomTypes="
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # data 는 옵션 배열. 각 item.thumbnailImageUrl 수집
        items = data.get('data') if isinstance(data, dict) else data
        if items is None:
            items = []

        candidates = []
        for item in items:
            img_url = item.get('thumbnailImageUrl') if isinstance(item, dict) else None
            if not isinstance(img_url, str):
                continue
            if not re.search(r"\.(jpg|jpeg)(\?|$)", img_url, re.I):
                continue
            candidates.append({
                'url': img_url,
                'type': 'BNB_OPTION',
                'filename': img_url.split('/')[-1].split('?')[0],
                'reviewId': None
            })
            if len(candidates) >= 8:
                break

        type_count = { 'BNB_OPTION': len(candidates) }
        total_items = len(items)
        return candidates, type_count, total_items

    except Exception as e:
        st.error(f"한인민박 API 호출 오류: {e}")
        return [], {}, 0

@log_calls()
def download_and_analyze_images(candidates, pid):
    """후보 이미지 다운로드 및 해상도 분석"""
    analyzed = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, cand in enumerate(candidates):
        try:
            status_text.text(f"이미지 다운로드 중... {i+1}/{len(candidates)}: {cand['filename']}")
            progress_bar.progress((i + 1) / len(candidates))
            
            import requests
            from PIL import Image
            img_bytes = requests.get(cand['url'], timeout=15).content
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            
            W, H = img.size
            aspect_ratio = H / W if W > 0 else 0
            is_portrait = aspect_ratio >= 1.2
            is_landscape = aspect_ratio <= 0.8
            
            # 점수 계산: 해상도 + NON_REVIEW 가산점 + 세로구도 가산점
            base_score = W * H
            type_bonus = 2.0 if cand['type'] == 'NON_REVIEW' else 1.0
            orientation_bonus = 1.5 if is_portrait else 1.2 if is_landscape else 1.0
            
            analyzed.append({
                **cand,
                'image': img,
                'width': W,
                'height': H,
                'aspect_ratio': aspect_ratio,
                'is_portrait': is_portrait,
                'is_landscape': is_landscape,
                'pixels': W * H,
                'score': base_score * type_bonus * orientation_bonus
            })
            
        except Exception as e:
            st.warning(f"이미지 다운로드 실패: {cand['filename']} - {e}")
    
    # 점수순 정렬
    analyzed.sort(key=lambda x: x['score'], reverse=True)
    
    progress_bar.empty()
    status_text.empty()
    
    return analyzed


@log_calls()
def apply_text_overlay(video_path: str, text_settings: dict, product_id: str, ai_engine: str = "veo") -> str:
    """비디오에 텍스트 오버레이 적용"""
    try:
        copy_text = text_settings.get('copy', '')
        if not copy_text:
            return video_path
        
        position = text_settings.get('position', 'top')
        # 자동 스케일(PlayResY 기준 1280) 지원
        auto_scale = bool(text_settings.get('auto_scale', False))
        font_scale_pct = text_settings.get('font_scale_pct', None)
        if auto_scale and isinstance(font_scale_pct, (int, float)):
            font_size = max(24, int(1280 * (float(font_scale_pct) / 100.0)))
        else:
            font_size = int(text_settings.get('font_size', 64))
        font_color = text_settings.get('font_color', 'white')
        border_width = int(text_settings.get('border_width', 3))
        if auto_scale:
            border_width = max(2, int(font_size * 0.06))
        bg_opacity = text_settings.get('bg_opacity', 0.4)
        
        # 출력 경로
        output_path = f"outputs/{product_id}/final_{ai_engine}.mp4"
        os.makedirs(f"outputs/{product_id}", exist_ok=True)
        
        # ASS 자막 파일 생성
        ass_file = f"outputs/{product_id}/overlay_{ai_engine}.ass"
        
        # 위치별 설정
        if position == "top":
            alignment = 8  # 상단 중앙
            margin_v = max(80, font_size * 2 if auto_scale else 120)
        elif position == "middle":
            alignment = 5  # 중앙
            margin_v = 0
        else:  # bottom
            alignment = 2  # 하단 중앙
            margin_v = max(80, font_size * 2 if auto_scale else 120)

        # 줄바꿈을 ASS 자막 형식으로 변환 (f-string 내에서 백슬래시 사용 불가)
        formatted_copy = copy_text.replace('\n', '\\N')

        # ASS 자막 내용
        ass_content = f"""[Script Info]
; Script generated by Marketing Video Generator
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,AppleSDGothicNeo,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H66000000,0,0,0,0,100,100,0,0,1,{border_width},0,{alignment},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,Default,,0,0,0,,{formatted_copy}"""
        
        # ASS 파일 저장
        with open(ass_file, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        # FFmpeg 명령어로 자막 합성
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"subtitles={ass_file}",
            '-c:a', 'copy',
            '-preset', 'fast',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg 오류: {result.stderr}")
        
        # 임시 파일 정리
        if os.path.exists(ass_file):
            try:
                os.unlink(ass_file)
            except PermissionError:
                pass
        
        return output_path
        
    except Exception as e:
        logger.exception(f"텍스트 오버레이 적용 실패: {e}")
        return video_path


@log_calls()
def extract_copy_from_api(pid: str, product_type: str = "travel"):
    """상품 유형별 마케팅 카피 추출 (여행/숙소/해외호텔/한인민박)

    - travel: traveler-experiences header API 사용
    - accommodation/overseas_hotel: 추천 API에서 근사 타이틀 시도, 실패 시 기본 문구
    - bnb: options API에서 첫 옵션 타이틀/가격으로 카피 구성
    """
    try:
        import requests
        if product_type == "travel":
            hdr = requests.get(API_BASE.format(pid=pid), timeout=20)
            data = hdr.json().get('data', {})
            title = (data.get('title') or '').strip()
            price_info = data.get('ctaButton', {}).get('price', {})
            sale_price = price_info.get('salePrice', '')
        copy_lines = []
        if title:
            copy_lines.append(title)
        if sale_price:
            copy_lines.append(f'지금 예약 · {sale_price}')
            return '\n'.join(copy_lines) if copy_lines else '지금 예약하고 혜택 받기'

        if product_type in ("accommodation", "overseas_hotel"):
            today_ = date.today()
            ci = (today_ + timedelta(days=7)).strftime('%Y-%m-%d')
            co = (today_ + timedelta(days=8)).strftime('%Y-%m-%d')
            url = (
                "https://api3.myrealtrip.com/accommodations/v1/products/"
                f"{pid}/front/recommendation?checkIn={ci}&checkOut={co}&adultCount=2&childCount=0"
            )
            r = requests.get(url, timeout=20)
            js = r.json()
            sections = js.get('data', {}).get('sections', [])
            # 첫 아이템의 타이틀을 사용 (없으면 기본)
            for sec in sections:
                items = sec.get('data', []) if isinstance(sec, dict) else []
                if items:
                    title = (items[0].get('title') or '').strip()
                    if title:
                        return title
                    break
            return '지금 예약하고 혜택 받기'

        if product_type == "bnb":
            today_ = date.today()
            start_date = (today_ + timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = (today_ + timedelta(days=8)).strftime('%Y-%m-%d')
            url = (
                f"https://api3.myrealtrip.com/product/products/{pid}/options?productId={pid}"
                f"&startDate={start_date}&endDate={end_date}&adults=2&children=0&isReservable=false&roomTypes="
            )
            r = requests.get(url, timeout=20)
            js = r.json()
            items = js.get('data') if isinstance(js, dict) else js
            items = items or []
            if items:
                first = items[0]
                title = (first.get('title') or '').strip()
                sale = (first.get('priceInfo', {}) or {}).get('salePrice', {})
                amount = sale.get('amount')
                suffix = sale.get('suffix') or ''
                price_text = None
                if isinstance(amount, (int, float)):
                    price_text = f"{int(amount):,}{suffix}"
                elif sale:
                    # fallback textual sale price
                    price_text = f"{sale}" if isinstance(sale, str) else None
                copy_lines = []
                if title:
                    copy_lines.append(title)
                if price_text:
                    copy_lines.append(f"지금 예약 · {price_text}")
                return '\n'.join(copy_lines) if copy_lines else '지금 예약하고 혜택 받기'

        # 기타: 기본 문구
        return '지금 예약하고 혜택 받기'
    except Exception as e:
        st.error(f"카피 추출 오류: {e}")
        return "지금 예약하고 혜택 받기"

@log_calls()
def create_resized_preview(image, target_width=1080, target_height=1920):
    """리사이즈 미리보기 생성"""
    from PIL import Image
    W, H = image.size
    scale = max(target_width/W, target_height/H)
    new = image.resize((int(W*scale), int(H*scale)), Image.LANCZOS)
    nw, nh = new.size
    left, top = (nw-target_width)//2, (nh-target_height)//2
    cover = new.crop((left, top, left+target_width, top+target_height))
    return cover

@log_calls()
def create_text_overlay_preview(image, text, font_size=64, font_color="white", 
                               border_width=3, border_color="black", 
                               position="top", bg_opacity=0.4):
    """텍스트 오버레이 미리보기 생성"""
    from PIL import Image, ImageDraw, ImageFont
    preview = image.copy()
    draw = ImageDraw.Draw(preview)
    
    # 폰트 로드 시도
    try:
        font = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', font_size)
    except:
        font = ImageFont.load_default()
    
    # 텍스트 크기 계산
    text_lines = text.split('\n')
    line_height = font_size + 8
    total_height = len(text_lines) * line_height
    
    # 위치 계산
    img_w, img_h = preview.size
    if position == "top":
        y_start = 80
    elif position == "middle":
        y_start = (img_h - total_height) // 2
    else:  # bottom
        y_start = img_h - total_height - 80
    
    # 배경 박스 그리기
    max_width = max([draw.textlength(line, font=font) for line in text_lines])
    box_padding = 20
    box_x1 = (img_w - max_width) // 2 - box_padding
    box_y1 = y_start - box_padding
    box_x2 = (img_w + max_width) // 2 + box_padding
    box_y2 = y_start + total_height + box_padding
    
    # 반투명 배경
    overlay = Image.new('RGBA', preview.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([box_x1, box_y1, box_x2, box_y2], 
                          fill=(0, 0, 0, int(255 * bg_opacity)))
    preview = Image.alpha_composite(preview.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(preview)
    
    # 텍스트 그리기
    for i, line in enumerate(text_lines):
        y = y_start + i * line_height
        text_width = draw.textlength(line, font=font)
        x = (img_w - text_width) // 2
        
        # 테두리
        for dx in [-border_width, 0, border_width]:
            for dy in [-border_width, 0, border_width]:
                if dx != 0 or dy != 0:
                    draw.text((x+dx, y+dy), line, font=font, fill=border_color)
        
        # 메인 텍스트
        draw.text((x, y), line, font=font, fill=font_color)
    
    return preview

@log_calls()
def generate_local_simulation_video(image, output_path: str, duration: int = 5, fps: int = 30):
    """선택 이미지로 간단한 시뮬레이션 영상 생성(크레딧 소진 없음)"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    base = create_resized_preview(image, target_width=1080, target_height=1920)
    width, height = 1080, 1920
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, float(fps), (width, height))
    total_frames = max(1, int(duration * fps))
    base_np = cv2.cvtColor(np.array(base), cv2.COLOR_RGB2BGR)
    # 아주 약한 줌인 모션
    for i in range(total_frames):
        t = i / max(1, total_frames - 1)
        scale = 1.0 + 0.04 * t
        sw, sh = int(width * scale), int(height * scale)
        frame = cv2.resize(base_np, (sw, sh), interpolation=cv2.INTER_LANCZOS4)
        x1 = (sw - width) // 2
        y1 = (sh - height) // 2
        crop = frame[y1:y1+height, x1:x1+width]
        writer.write(crop)
    writer.release()
    return output_path

@log_calls()
def safe_unlink(path: str, retries: int = 3, delay: float = 0.2) -> None:
    """Windows에서 파일 핸들 점유로 삭제 실패 시 재시도."""
    for _ in range(retries):
        try:
            if os.path.exists(path):
                os.unlink(path)
            return
        except PermissionError:
            time.sleep(delay)
    # 마지막 시도 후에도 실패하면 무시
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


@log_calls()
@st.cache_data(ttl=300)
def get_higgs_motions(api_key: str = None, api_secret: str = None) -> List[dict]:
    """Higgsfield 모션 목록을 API로 조회 (5분 캐시). UI 입력값이 있으면 우선."""
    try:
        api_key_eff = (api_key or os.getenv("HIGGS_API_KEY", "")).strip()
        api_secret_eff = (api_secret or os.getenv("HIGGS_SECRET", "")).strip()
        if not api_key_eff:
            return []
        url = "https://platform.higgsfield.ai/v1/motions"
        headers = {"hf-api-key": api_key_eff}
        if api_secret_eff:
            headers["hf-secret"] = api_secret_eff
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

@log_calls()
def resolve_image_url(selected_item: dict) -> str:
    """선택된 항목에서 원본 이미지 URL을 최대한 복구한다."""
    try:
        # 1) 직접 보유한 url 우선
        u = selected_item.get('url')
        if isinstance(u, str) and u.startswith('http'):
            return u
        # 2) 세션 candidates에서 filename 매칭으로 탐색
        candidates = st.session_state.get('candidates', [])
        sel_fname = selected_item.get('filename')
        if sel_fname:
            for c in candidates:
                if c.get('filename') == sel_fname:
                    cu = c.get('url')
                    if isinstance(cu, str) and cu.startswith('http'):
                        return cu
        # 3) 백업 키들 탐색
        for key in ('source_url', 'original_url', 'image_url'):
            uu = selected_item.get(key)
            if isinstance(uu, str) and uu.startswith('http'):
                return uu
    except Exception:
        pass
    return ''

@log_calls()
def generate_video_with_veo(image, prompt, progress_callback=None):
    """Veo로 영상 생성"""
    try:
        global client
        if client is None:
            try:
                client = init_gemini_client()
            except Exception as e:
                raise Exception(f"Gemini 초기화 실패: {e}")
        if progress_callback:
            progress_callback("Veo 영상 생성 시작...")
        
        # 지연 임포트 (types)
        from google.genai import types as _types

        op = client.models.generate_videos(
            model='veo-3.0-fast-generate-001',
            prompt=prompt,
            image=image,
            config=_types.GenerateVideosConfig(
                aspect_ratio='9:16', 
                resolution='720p', 
                person_generation='allow_adult'
            ),
        )
        
        # 폴링
        waited = 0
        max_wait = 600  # 10분 최대 대기
        while not op.done and waited < max_wait:
            if progress_callback:
                progress_callback(f"Veo 생성 중... ({waited}s)")
            time.sleep(30)
            waited += 30
            try:
                op = client.operations.get(op)
            except Exception as e:
                if progress_callback:
                    progress_callback(f"폴링 오류: {e}")
                break
        
        if not op.done:
            raise Exception(f"타임아웃 ({max_wait}초)")
        
        # 결과 확인
        if (hasattr(op, 'response') and op.response and 
            hasattr(op.response, 'generated_videos') and op.response.generated_videos and
            len(op.response.generated_videos) > 0):
            return op.response.generated_videos[0]
        else:
            raise Exception("생성된 영상이 없습니다")
            
    except Exception as e:
        raise Exception(f"영상 생성 오류: {e}")

# 메인 UI
def main():
    logger.info("Streamlit main loaded. session_keys=%s", list(st.session_state.keys()))
    st.title("🎬 Marketing Video Generator")
    st.markdown("**MyRealTrip 상품으로 자동 마케팅 영상 생성**")
    
    # (테스트 모드 제거됨)
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 상품 ID 입력 (세션 상태에 따라 기본값 설정)
        default_product_id = st.session_state.get('product_id', "4454757")
        product_id = st.text_input(
            "상품 ID 입력", 
            value=default_product_id,
            help="MyRealTrip 상품 ID를 입력하세요 (예: 4454757)",
            key="product_id_input"
        )
        
        # 직접 입력된 상품 ID를 우선적으로 사용
        if product_id and product_id.strip():
            # 세션의 product_id를 직접 입력값으로 업데이트
            if 'product_id' in st.session_state and st.session_state.product_id != product_id:
                # 기존 데이터 초기화
                if 'analyzed_images' in st.session_state:
                    del st.session_state['analyzed_images']
                if 'marketing_copy' in st.session_state:
                    del st.session_state['marketing_copy']
                st.success(f"✅ 상품 ID를 {product_id}로 변경했습니다!")
            
            st.session_state.product_id = product_id
        
        # 상품 유형 선택
        product_type = st.selectbox(
            "상품 유형",
            options=["travel", "accommodation", "overseas_hotel", "bnb"],
            index=0,
            format_func=lambda x: {"travel": "🧭 여행상품", "accommodation": "🏨 숙소(국내)", "overseas_hotel": "🌍 해외호텔", "bnb": "🏠 한인민박"}[x]
        )

        # 비여행 상품용 체크인/체크아웃/인원 입력 UI 제거 (기본값 내부 적용)
        
        # 새로고침 버튼
        if st.button("🔄 새로고침", help="상품 정보를 다시 불러옵니다"):
            if 'analyzed_images' in st.session_state:
                del st.session_state['analyzed_images']
            if 'marketing_copy' in st.session_state:
                del st.session_state['marketing_copy']
            if 'last_product_id' in st.session_state:
                del st.session_state['last_product_id']
            logger.info("Refresh requested. Cleared cached states.")
            st.rerun()
        
        # 예시 상품들
        st.markdown("**📋 예시 상품들:**")
        example_products = {
            "4454757": "상하이 디즈니랜드",
            "3147866": "런던 내셔널갤러리", 
            "3149960": "포트스테판 투어",
            "3442342": "새로운 상품"
        }
        
        for pid, name in example_products.items():
            if st.button(f"{name} ({pid})", key=f"example_{pid}"):
                # 기존 데이터 초기화
                if 'analyzed_images' in st.session_state:
                    del st.session_state['analyzed_images']
                if 'marketing_copy' in st.session_state:
                    del st.session_state['marketing_copy']
                if 'last_product_id' in st.session_state:
                    del st.session_state['last_product_id']
                
                # text_input을 강제로 업데이트하기 위해 키를 삭제
                if 'product_id_input' in st.session_state:
                    del st.session_state['product_id_input']
                
                # 새로운 상품 ID 설정
                st.session_state.product_id = pid
                logger.info("Example product selected. pid=%s, name=%s", pid, name)
                st.success(f"✅ 예시 상품 '{name} ({pid})'로 변경되었습니다!")
                st.rerun()
        
        # 최종 product_id는 이미 session_state에 설정됨
        final_product_id = st.session_state.get('product_id', product_id)
    
    # 메인 컨텐츠
    if final_product_id:
        st.markdown(f"### 📦 상품 ID: `{final_product_id}`")
        product_id = final_product_id  # 이후 코드에서 사용할 변수 통일
        
        # 1단계: 이미지 분석
        if st.button("🔍 이미지 분석 시작", type="primary"):
            logger.info("Image analysis requested. pid=%s, type=%s", product_id, product_type)
            with st.spinner("이미지 후보군 분석 중..."):
                if product_type in ("accommodation", "overseas_hotel"):
                    # 내부 기본값 사용 (체크인+7일, 1박, 성인2, 아동0)
                    today_ = date.today()
                    ci_str = (today_ + timedelta(days=7)).strftime('%Y-%m-%d')
                    co_str = (today_ + timedelta(days=8)).strftime('%Y-%m-%d')
                    adult_cnt = 2
                    child_cnt = 0
                    candidates, type_count, total_images = analyze_accommodation_images(
                        product_id, ci_str, co_str, adult_cnt, child_cnt
                    )
                elif product_type == "bnb":
                    today_ = date.today()
                    ci_str = (today_ + timedelta(days=7)).strftime('%Y-%m-%d')
                    co_str = (today_ + timedelta(days=8)).strftime('%Y-%m-%d')
                    adult_cnt = 2
                    child_cnt = 0
                    candidates, type_count, total_images = analyze_bnb_images(
                        product_id, ci_str, co_str, adult_cnt, child_cnt
                    )
                else:
                    candidates, type_count, total_images = analyze_images(product_id)
                
                if candidates:
                    logger.info("Image candidates discovered. total_images=%s, candidates=%s, type_count=%s", total_images, len(candidates), type_count)
                    st.success(f"✅ 총 {total_images}장 중 {len(candidates)}개 후보 발견!")
                    st.info(f"📊 이미지 타입: {type_count}")
                    
                    # 세션에 저장
                    st.session_state.candidates = candidates
                    st.session_state.product_id_current = product_id
                    
                    # 이미지 다운로드 및 분석
                    analyzed = download_and_analyze_images(candidates, product_id)
                    st.session_state.analyzed_images = analyzed
                    
                else:
                    logger.warning("No suitable images found. pid=%s, type=%s", product_id, product_type)
                    st.error("❌ 적합한 이미지를 찾을 수 없습니다.")
        
        # 2단계: 이미지 선택
        if 'analyzed_images' in st.session_state and st.session_state.get('product_id_current') == product_id:
            st.markdown("### 🖼️ 이미지 선택")
            
            analyzed = st.session_state.analyzed_images
            # REVIEW 타입 이미지는 UI에서 추가 필터링하여 제외
            try:
                analyzed = [it for it in analyzed if str(it.get('type', '')).upper() != 'REVIEW']
            except Exception:
                pass
            if not analyzed:
                st.warning("표시할 수 있는 NON_REVIEW(또는 비-리뷰) 이미지를 찾지 못했습니다. 상품 유형/ID를 변경하거나 다시 시도하세요.")
                return
            
            # 이미지 그리드 표시
            cols = st.columns(4)
            selected_image = None
            
            for i, item in enumerate(analyzed[:8]):  # 최대 8개
                with cols[i % 4]:
                    # 이미지 표시
                    st.image(item['image'], caption=f"#{i+1}", width="stretch")
                    
                    # 정보 표시
                    orientation = "세로" if item['is_portrait'] else "가로" if item['is_landscape'] else "정방"
                    st.caption(f"{item['width']}x{item['height']} ({orientation})")
                    
                    # 타입 표시
                    type_color = "🔵" if item['type'] == 'NON_REVIEW' else "🟢"
                    st.caption(f"{type_color} {item['type']}")
                    
                    # 선택 버튼
                    if st.button(f"선택", key=f"select_{i}"):
                        st.session_state.selected_image = item
                        logger.info("Image #%s selected. size=%sx%s type=%s", i+1, item['width'], item['height'], item['type'])
                        st.success(f"✅ 이미지 #{i+1} 선택됨!")
            
            # 3단계: 미리보기 & 커스터마이징
            if 'selected_image' in st.session_state:
                st.markdown("### 🎨 미리보기 & 커스터마이징")
                
                selected = st.session_state.selected_image
                
                # 마케팅 카피 추출 (상품 유형별)
                logger.info("Extracting marketing copy. pid=%s, type=%s", product_id, product_type)
                copy_text = extract_copy_from_api(product_id, product_type)
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    st.markdown("#### 📸 원본 이미지")
                    st.image(selected['image'], caption="선택된 원본", width="stretch")
                    st.caption(f"{selected['width']}x{selected['height']} ({selected['type']})")
                
                with col2:
                    st.markdown("#### 📐 리사이즈 미리보기")
                    resized_preview = create_resized_preview(selected['image'])
                    st.image(resized_preview, caption="1080x1920 크롭 결과", width="stretch")
                    st.caption("9:16 비율로 자동 크롭됨")
                
                with col3:
                    st.markdown("#### 🎨 텍스트 오버레이")
                    st.info("현재 버전에서는 텍스트 설정 기능이 비활성화되어 있습니다.")
                
                # 4단계: 영상 생성 설정
                st.markdown("### 🎬 영상 생성 설정")
                
                col_prompt1, col_prompt2 = st.columns([2, 1])
                
                with col_prompt1:
                    # 프롬프트 커스터마이징
                    prompt_template = st.text_area(
                        "영상 생성 프롬프트",
                        value=(
                            "Create a cinematic 9:16 travel video from this image. "
                            "Add gentle camera movement with slow push-in and subtle pan. "
                            "Include environmental motion like breeze, sparkles, or natural movement. "
                            "If people are visible, show them walking naturally. "
                            "Maintain the original colors and atmosphere. Vertical format, high quality."
                        ),
                        height=120
                    )
                
                with col_prompt2:
                    st.markdown("**🎯 생성 옵션**")
                    dry_run_flow = st.checkbox("크레딧 소진 없이 영상 로직만 검토 (드라이런)", value=True, help="실제 AI 호출 없이 시뮬레이션 영상으로 전체 흐름을 검토합니다.")
                    image_source = st.radio("영상 생성에 사용할 이미지", options=["resized", "original"], index=0, format_func=lambda x: {"resized": "📐 리사이즈(1080x1920)", "original": "🖼️ 원본 이미지"}[x])
                    
                    # AI 엔진 선택
                    ai_engine = st.selectbox(
                        "🤖 AI 엔진",
                        options=["higgs"],
                        index=0,
                        format_func=lambda x: {"higgs": "🧲 HiggsField"}[x],
                        help="HiggsField 엔진만 사용합니다"
                    )
                    
                    if ai_engine == "gemini_veo":
                        # Veo 모델 선택
                        model_choice = st.selectbox(
                            "Veo 모델",
                            options=["veo-3.0-fast-generate-001", "veo-3.0-generate-001"],
                            index=0,
                            format_func=lambda x: {"veo-3.0-fast-generate-001": "⚡ Fast (빠름)", 
                                                  "veo-3.0-generate-001": "🎨 Standard (고품질)"}[x]
                        )
                        
                        # 해상도 선택
                        resolution = st.selectbox(
                            "해상도",
                            options=["720p", "1080p"],
                            index=0
                        )
                    
                    elif ai_engine == "runway":
                        # Runway 모델 선택
                        runway_model = st.selectbox(
                            "Runway 모델",
                            options=["gen3a_turbo", "veo3"],
                            index=0,
                            format_func=lambda x: {
                                "gen3a_turbo": "🚀 Gen3a Turbo (빠름, 저렴 ~150크레딧)", 
                                "veo3": "🔮 VEO3 (고품질, 비싸 ~320크레딧)"
                            }[x],
                            help="Gen3a Turbo: 빠르고 저렴 vs VEO3: 느리지만 고품질"
                        )
                        
                        # Veo 전용 설정들은 그대로 유지
                        
                    elif ai_engine == "runway_ai":
                        # Runway AI 전용 옵션들
                        st.markdown("**🎬 Runway AI 설정**")
                    elif ai_engine == "higgs":
                        st.markdown("**🧲 HiggsField 설정**")
                        # 키 입력 UI (세션에 저장)
                        st.markdown("키 입력 (UI 값이 환경변수보다 우선 적용)")
                        st.session_state.HIGGS_API_KEY = st.text_input("HIGGS_API_KEY", value=st.session_state.get("HIGGS_API_KEY", ""), type="password")
                        st.session_state.HIGGS_SECRET = st.text_input("HIGGS_SECRET", value=st.session_state.get("HIGGS_SECRET", ""), type="password")

                        # 기본값만 노출. 고급 옵션은 API 명세 확정 후 추가
                        higgs_model = st.text_input("모델 ID", value="dop-turbo")
                        st.caption("모델/옵션은 임시값입니다. API 명세 수신 후 업데이트")
                        # 실시간 모션 목록 불러오기 (UI 키 우선)
                        motions = get_higgs_motions(
                            api_key=st.session_state.get("HIGGS_API_KEY", None),
                            api_secret=st.session_state.get("HIGGS_SECRET", None)
                        )
                        motion_names = [m.get('name') for m in motions if m.get('name')]
                        default_names = motion_names[:2] if motion_names else []
                        higgs_motions = st.multiselect(
                            "모션 선택 (Higgs Motions)",
                            options=motion_names if motion_names else ["push_in", "clouds"],
                            default=default_names if default_names else ["push_in", "clouds"],
                            help="Higgsfield 제공 모션 목록을 실시간 조회하여 선택합니다."
                        )
                        
                        video_duration = st.slider(
                            "비디오 길이 (초)",
                            min_value=2,
                            max_value=10,
                            value=5,
                            help="생성할 비디오의 길이를 설정하세요"
                        )
                        
                        motion_strength = st.slider(
                            "움직임 강도",
                            min_value=0.0,
                            max_value=1.0,
                            value=0.5,
                            step=0.1,
                            help="0.0: 최소 움직임, 1.0: 최대 움직임"
                        )
                        
                        use_seed = st.checkbox("시드값 사용 (재현성)", value=False)
                        seed_value = None
                        if use_seed:
                            seed_value = st.number_input(
                                "시드값",
                                min_value=0,
                                max_value=999999,
                                value=42,
                                help="같은 시드값으로 동일한 결과 재현 가능"
                            )

                        # (Higgs 전용: Runway 관련 옵션 숨김)
                
                # 영상 스타일 커스터마이징 섹션
                st.markdown("### 🎥 영상 스타일 커스터마이징")
                
                col_camera, col_motion, col_style = st.columns(3)
                
                with col_camera:
                    st.markdown("**📹 카메라 움직임**")
                    
                    camera_movement = st.selectbox(
                        "카메라 동작",
                        options=["push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "static", "orbit"],
                        index=0,
                        format_func=lambda x: {
                            "push_in": "📍 Push-in (줌인)",
                            "pull_out": "📤 Pull-out (줌아웃)", 
                            "pan_left": "⬅️ Pan Left (좌측 이동)",
                            "pan_right": "➡️ Pan Right (우측 이동)",
                            "tilt_up": "⬆️ Tilt Up (위로 틸트)",
                            "tilt_down": "⬇️ Tilt Down (아래로 틸트)",
                            "static": "🔒 Static (고정)",
                            "orbit": "🔄 Orbit (원형 이동)"
                        }[x],
                        help="카메라가 어떻게 움직이는지(줌/팬/틸트/고정)를 선택합니다."
                    )
                    
                    camera_speed = st.selectbox(
                        "카메라 속도",
                        options=["very_slow", "slow", "medium", "fast"],
                        index=1,
                        format_func=lambda x: {
                            "very_slow": "🐌 매우 느림",
                            "slow": "🚶 느림", 
                            "medium": "🏃 보통",
                            "fast": "⚡ 빠름"
                        }[x],
                        help="카메라 이동 속도를 설정합니다."
                    )
                    
                    camera_angle = st.selectbox(
                        "카메라 앵글",
                        options=["eye_level", "low_angle", "high_angle", "bird_eye", "worm_eye"],
                        index=0,
                        format_func=lambda x: {
                            "eye_level": "👁️ 눈높이",
                            "low_angle": "📐 로우앵글 (아래에서)",
                            "high_angle": "📐 하이앵글 (위에서)", 
                            "bird_eye": "🦅 조감도 (새의 시점)",
                            "worm_eye": "🐛 웜뷰 (지면에서)"
                        }[x],
                        help="피사체를 어떤 시점에서 촬영할지(눈높이/로우/하이/조감/웜뷰)를 설정합니다."
                    )

                    focal_length = st.selectbox(
                        "렌즈 초점거리",
                        options=["24mm", "35mm", "50mm", "85mm"],
                        index=1,
                        help="초점거리가 짧을수록 광각(넓은 화각), 길수록 망원(배경 압축) 효과가 납니다."
                    )
                
                with col_motion:
                    st.markdown("**🚶 인물 움직임**")
                    
                    person_motion = st.selectbox(
                        "인물 동작",
                        options=["none", "walking", "standing", "sitting", "running", "gesturing", "natural_micro"],
                        index=1,
                        format_func=lambda x: {
                            "none": "❌ 움직임 없음",
                            "walking": "🚶 걷기",
                            "standing": "🧍 서있기",
                            "sitting": "💺 앉아있기", 
                            "running": "🏃 뛰기",
                            "gesturing": "👋 손짓/제스처",
                            "natural_micro": "😊 자연스러운 미세동작"
                        }[x],
                        help="주요 인물의 움직임 강도/유형을 선택합니다."
                    )
                    
                    crowd_behavior = st.selectbox(
                        "군중/배경 인물",
                        options=["static", "ambient", "busy", "minimal"],
                        index=1,
                        format_func=lambda x: {
                            "static": "🔒 정적",
                            "ambient": "🌊 자연스러운 움직임",
                            "busy": "🏃‍♂️ 활발한 움직임",
                            "minimal": "😴 최소한의 움직임"
                        }[x],
                        help="배경 인물의 전반적인 움직임 밀도를 설정합니다."
                    )
                    
                    interaction = st.selectbox(
                        "인물 상호작용",
                        options=["none", "looking_around", "pointing", "talking", "enjoying"],
                        index=4,
                        format_func=lambda x: {
                            "none": "❌ 상호작용 없음",
                            "looking_around": "👀 주변 둘러보기",
                            "pointing": "👉 가리키기",
                            "talking": "💬 대화하기", 
                            "enjoying": "😊 즐기는 모습"
                        }[x],
                        help="인물이 무엇을 하는지(둘러보기/가리키기/대화/감상)를 지정합니다."
                    )

                    motion_blur = st.slider(
                        "모션 블러 강도",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.2,
                        step=0.05,
                        help="움직임에 따른 잔상(모션 블러) 정도를 조절합니다."
                    )

                    stabilization = st.checkbox("영상 흔들림 보정", value=True, help="카메라 흔들림을 줄이기 위한 안정화 효과를 적용합니다.")
                
                with col_style:
                    st.markdown("**🌟 환경 효과**")
                    
                    environmental_motion = st.multiselect(
                        "환경 움직임",
                        options=["wind", "water", "clouds", "leaves", "flags", "smoke", "sparkles", "birds"],
                        default=["wind", "clouds"],
                        format_func=lambda x: {
                            "wind": "💨 바람 효과",
                            "water": "🌊 물 움직임",
                            "clouds": "☁️ 구름 이동",
                            "leaves": "🍃 나뭇잎 흔들림",
                            "flags": "🚩 깃발 펄럭임", 
                            "smoke": "💨 연기/안개",
                            "sparkles": "✨ 반짝임 효과",
                            "birds": "🐦 새 날아다님"
                        }[x],
                        help="장면에 자연스러운 환경 움직임(바람/물/구름 등)을 추가합니다."
                    )
                    
                    lighting_mood = st.selectbox(
                        "조명 분위기",
                        options=["natural", "golden_hour", "blue_hour", "dramatic", "soft", "bright"],
                        index=0,
                        format_func=lambda x: {
                            "natural": "☀️ 자연광",
                            "golden_hour": "🌅 골든아워",
                            "blue_hour": "🌆 블루아워",
                            "dramatic": "🎭 드라마틱",
                            "soft": "💡 부드러운 조명",
                            "bright": "💡 밝은 조명"
                        }[x],
                        help="장면의 전반적인 조명 분위기를 선택합니다."
                    )
                    
                    video_style = st.selectbox(
                        "영상 스타일",
                        options=["cinematic", "documentary", "commercial", "artistic", "travel_vlog", "instagram"],
                        index=0,
                        format_func=lambda x: {
                            "cinematic": "🎬 영화적",
                            "documentary": "📺 다큐멘터리",
                            "commercial": "📺 광고용",
                            "artistic": "🎨 예술적",
                            "travel_vlog": "✈️ 여행 브이로그",
                            "instagram": "📱 인스타그램"
                        }[x],
                        help="연출 톤과 편집 감성(영화적/다큐/광고 등)을 설정합니다."
                    )

                    color_grade = st.selectbox(
                        "컬러 그레이딩",
                        options=["natural", "teal_orange", "warm", "cool", "black_white", "high_contrast"],
                        index=0,
                        format_func=lambda x: {
                            "natural": "🌈 내추럴",
                            "teal_orange": "🟦🟧 틸&오렌지",
                            "warm": "🔥 웜톤",
                            "cool": "❄️ 쿨톤",
                            "black_white": "⚫⚪ 흑백",
                            "high_contrast": "🌓 하이 콘트라스트"
                        }[x],
                        help="색감 톤을 지정합니다(내추럴/틸&오렌지/웜/쿨/흑백/하이 콘트라스트)."
                    )

                    film_grain = st.slider("필름 그레인", 0.0, 1.0, 0.0, 0.05, help="필름 질감의 입자감을 추가합니다.")
                    vignette = st.slider("비네트 강도", 0.0, 1.0, 0.0, 0.05, help="프레임 가장자리를 어둡게 해 시선을 중앙으로 모읍니다.")
                    depth_of_field = st.checkbox("피사계 심도(배경 흐림)", value=False, help="피사체는 또렷하게, 배경은 흐릿하게 만들어 입체감을 줍니다.")
                    bokeh_strength = 0.0
                    if depth_of_field:
                        bokeh_strength = st.slider("보케 강도", 0.0, 1.0, 0.4, 0.05, help="빛망울(보케)의 크기/강도를 조절합니다.")
                    
                # 자동 프롬프트 생성
                def generate_custom_prompt():
                    """사용자 설정을 기반으로 프롬프트 자동 생성 (리얼리즘 강화)"""
                    base_prompt = (
                        "Create a realistic, natural-looking 9:16 travel video from this image. "
                        "Emphasize photorealism and subtlety."
                    )
                    
                    # 카메라 움직임
                    camera_descriptions = {
                        "push_in": "Add a slow push-in camera movement",
                        "pull_out": "Add a pull-out camera movement revealing more of the scene",
                        "pan_left": "Add a smooth left panning movement",
                        "pan_right": "Add a smooth right panning movement", 
                        "tilt_up": "Add an upward tilting movement",
                        "tilt_down": "Add a downward tilting movement",
                        "static": "Keep the camera static with no movement",
                        "orbit": "Add a subtle orbital camera movement around the subject"
                    }
                    
                    camera_speeds = {
                        "very_slow": "very slowly",
                        "slow": "slowly", 
                        "medium": "at medium speed",
                        "fast": "quickly"
                    }
                    
                    camera_angles = {
                        "eye_level": "from eye level",
                        "low_angle": "from a low angle looking up",
                        "high_angle": "from a high angle looking down",
                        "bird_eye": "from a bird's eye view",
                        "worm_eye": "from ground level looking up"
                    }
                    
                    # 인물 동작
                    person_descriptions = {
                        "none": "Keep people completely still",
                        "walking": "Show people walking naturally",
                        "standing": "Show people standing with subtle movements",
                        "sitting": "Show people sitting comfortably",
                        "running": "Show people running or jogging",
                        "gesturing": "Show people making natural gestures",
                        "natural_micro": "Add natural micro-movements like breathing and small gestures"
                    }
                    
                    crowd_descriptions = {
                        "static": "Keep background people completely still",
                        "ambient": "Add natural ambient movement to background people",
                        "busy": "Show busy, active background movement", 
                        "minimal": "Add minimal, subtle background movement"
                    }
                    
                    # 환경 효과
                    env_descriptions = {
                        "wind": "gentle breeze moving elements",
                        "water": "water movement and ripples",
                        "clouds": "slow-moving clouds",
                        "leaves": "leaves rustling in the wind",
                        "flags": "flags waving gently",
                        "smoke": "subtle smoke or mist effects",
                        "sparkles": "magical sparkle effects",
                        "birds": "birds flying in the background"
                    }
                    
                    # 조명 분위기
                    lighting_descriptions = {
                        "natural": "with natural lighting",
                        "golden_hour": "with warm golden hour lighting",
                        "blue_hour": "with cool blue hour lighting",
                        "dramatic": "with dramatic lighting and shadows",
                        "soft": "with soft, diffused lighting",
                        "bright": "with bright, vibrant lighting"
                    }
                    
                    # 영상 스타일
                    style_descriptions = {
                        "cinematic": "Cinematic style with professional composition",
                        "documentary": "Documentary style with natural, realistic feel",
                        "commercial": "Commercial style with polished, marketing appeal",
                        "artistic": "Artistic style with creative composition",
                        "travel_vlog": "Travel vlog style with engaging, personal feel", 
                        "instagram": "Instagram-ready style with social media appeal"
                    }
                    
                    # 프롬프트 조합
                    prompt_parts = [base_prompt]
                    
                    # 카메라 설정
                    if camera_movement != "static":
                        camera_desc = f"{camera_descriptions[camera_movement]} {camera_speeds[camera_speed]} {camera_angles[camera_angle]}"
                        prompt_parts.append(camera_desc)
                    
                    # 인물 움직임
                    if person_motion != "none":
                        prompt_parts.append(person_descriptions[person_motion])
                    
                    prompt_parts.append(crowd_descriptions[crowd_behavior])
                    
                    # 환경 효과
                    if environmental_motion:
                        env_effects = [env_descriptions[env] for env in environmental_motion]
                        prompt_parts.append(f"Include {', '.join(env_effects)}")
                    
                    # 조명과 스타일
                    prompt_parts.append(f"{style_descriptions[video_style]} {lighting_descriptions[lighting_mood]}")
                    
                    # 렌즈/안정화/모션 블러
                    prompt_parts.append(f"Use a {focal_length} lens")
                    if stabilization:
                        prompt_parts.append("Apply stabilization to reduce shake")
                    if motion_blur > 0:
                        prompt_parts.append("Include natural motion blur appropriate to movement")

                    # 컬러/그레인/비네트/DOF
                    grade_texts = {
                        "natural": "with natural color grading",
                        "teal_orange": "with teal and orange color grading",
                        "warm": "with warm color tones",
                        "cool": "with cool color tones",
                        "black_white": "in black and white",
                        "high_contrast": "with high contrast color grading",
                    }
                    prompt_parts.append(grade_texts.get(color_grade, "with natural color grading"))
                    if film_grain > 0:
                        prompt_parts.append("add subtle film grain")
                    if vignette > 0:
                        prompt_parts.append("apply subtle vignette")
                    if depth_of_field:
                        prompt_parts.append("shallow depth of field with pleasing bokeh")
                    
                    # 기본 품질/리얼리즘 설정
                    prompt_parts.append(
                        "Maintain the original colors and atmosphere. Vertical format, high quality."
                    )
                    # 고정 종횡비(9:16) 강제 및 프레이밍 가이드
                    prompt_parts.append(
                        "Final output must be strictly 9:16 (1080x1920). If the source is not 9:16, perform a smart center-crop "
                        "or minimal padding to preserve composition; never stretch or squash the image."
                    )
                    # 리얼리즘/금지 사항 (AI 느낌 최소화)
                    prompt_parts.append(
                        "Photorealistic output. Avoid AI-like artifacts, oversaturation, over-sharpening, waxy skin, "
                        "flicker, jitter, warping, extra fingers/limbs, melting textures, or unintended text/logos."
                    )
                    prompt_parts.append(
                        "Preserve subject identity and geometry; do not add or remove objects, people, or change the scene layout."
                    )
                    prompt_parts.append(
                        "Keep motion subtle and physically plausible; no abrupt or surreal movements."
                    )
                    
                    return ". ".join(prompt_parts) + "."
                
                # 실시간 프롬프트 업데이트
                custom_prompt = generate_custom_prompt()
                
                # 프롬프트 미리보기
                st.markdown("### 📝 생성된 프롬프트 미리보기")
                with st.expander("🔍 자동 생성된 프롬프트 확인", expanded=True):
                    st.text_area(
                        "현재 설정으로 생성된 프롬프트",
                        value=custom_prompt,
                        height=100,
                        help="위의 설정들을 바탕으로 자동 생성된 프롬프트입니다. 수동으로 수정하려면 위의 프롬프트 입력창을 사용하세요."
                    )
                    
                    if st.button("📋 프롬프트 복사", help="생성된 프롬프트를 위의 입력창에 복사"):
                        st.session_state.custom_prompt = custom_prompt
                        st.success("✅ 프롬프트가 복사되었습니다! 위의 프롬프트 입력창을 확인하세요.")
                
                # 설정 요약
                st.markdown("### 📊 현재 설정 요약")
                
                col_summary1, col_summary2, col_summary3 = st.columns(3)
                
                with col_summary1:
                    st.markdown("**📹 카메라**")
                    st.info(f"""
                    **동작:** {camera_movement.replace('_', ' ').title()}
                    **속도:** {camera_speed.replace('_', ' ').title()}
                    **앵글:** {camera_angle.replace('_', ' ').title()}
                    """)
                
                with col_summary2:
                    st.markdown("**🚶 인물**")
                    st.info(f"""
                    **주인물:** {person_motion.replace('_', ' ').title()}
                    **배경인물:** {crowd_behavior.replace('_', ' ').title()}
                    **상호작용:** {interaction.replace('_', ' ').title()}
                    """)
                
                with col_summary3:
                    st.markdown("**🌟 환경**")
                    env_text = ", ".join([env.replace('_', ' ').title() for env in environmental_motion]) if environmental_motion else "없음"
                    st.info(f"""
                    **환경효과:** {env_text}
                    **조명:** {lighting_mood.replace('_', ' ').title()}
                    **스타일:** {video_style.replace('_', ' ').title()}
                    """)
                
                # 저장할 설정들 (업데이트)
                # 텍스트 기능 비활성화에 따라 빈 설정 저장
                st.session_state.text_settings = {}
                
                # 프롬프트 선택 (수동 vs 자동)
                use_custom_prompt = st.session_state.get('custom_prompt') == custom_prompt
                final_prompt = st.session_state.get('custom_prompt', custom_prompt) if use_custom_prompt else prompt_template
                
                # AI 엔진별 설정 저장
                video_settings = {
                    'ai_engine': ai_engine,
                    'prompt': final_prompt,
                    'camera_movement': camera_movement,
                    'camera_speed': camera_speed,
                    'camera_angle': camera_angle,
                    'focal_length': focal_length,
                    'person_motion': person_motion,
                    'crowd_behavior': crowd_behavior,
                    'interaction': interaction,
                    'motion_blur': motion_blur,
                    'stabilization': stabilization,
                    'environmental_motion': environmental_motion,
                    'lighting_mood': lighting_mood,
                    'video_style': video_style,
                    'color_grade': color_grade,
                    'film_grain': film_grain,
                    'vignette': vignette,
                    'depth_of_field': depth_of_field,
                    'bokeh_strength': bokeh_strength,
                    'custom_prompt': custom_prompt
                }
                
                if ai_engine == "higgs":
                    # Higgs 모션 목록 조회 및 선택값을 id로 매핑
                    motions = get_higgs_motions()
                    motion_name_to_id = {m.get('name'): m.get('id') for m in motions if m.get('name') and m.get('id')}
                    selected_names = locals().get('higgs_motions', [])
                    selected_motion_ids = [motion_name_to_id.get(n, n) for n in selected_names]

                    video_settings.update({
                        'higgs_model': locals().get('higgs_model', 'higgs-video-1'),
                        'higgs_motions': selected_motion_ids,
                        'higgs_style': locals().get('higgs_style', 'cinematic'),
                        'ratio': locals().get('higgs_ratio', '1080:1920'),
                        'duration': locals().get('video_duration', 5),
                        'motion_strength': locals().get('motion_strength', 0.5)
                    })
                
                st.session_state.video_settings = video_settings

                # 🧲 HiggsField 결과 조회(드라이런): job_set_id로 결과만 확인
                with st.expander("🧲 HiggsField 결과 조회(드라이런)", expanded=False):
                    job_set_id = st.text_input("Job Set ID", value="", help="Higgsfield에서 생성된 job_set_id를 입력하세요")
                    if st.button("조회", key="btn_higgs_poll"):
                        try:
                            from src.generators.higgs.video import HiggsVideoGenerator
                            gen = HiggsVideoGenerator(output_dir=Path("outputs"))
                            data = gen.get_job_set(job_set_id)
                            st.json(data)

                            # 결과 URL 추출
                            video_url = None
                            try:
                                for job in data.get("jobs", []):
                                    results = job.get("results") or {}
                                    for key in ("raw", "min"):
                                        obj = results.get(key) or {}
                                        u = obj.get("url")
                                        if isinstance(u, str) and u.startswith("http"):
                                            video_url = u
                                            break
                                    if video_url:
                                        break
                            except Exception:
                                pass

                            if video_url:
                                st.video(video_url)
                            else:
                                st.info("결과 URL을 찾지 못했습니다. 작업 상태가 완료되었는지 확인하세요.")
                        except Exception as e:
                            st.error(f"Higgs 조회 오류: {e}")
                    
                # 5단계: 영상 생성 실행
                if st.button("🚀 영상 생성 시작", type="primary", width="stretch"):
                    # 설정 가져오기
                    text_settings = st.session_state.get('text_settings', {})
                    video_settings = st.session_state.get('video_settings', {})
                    logger.info("Video generation triggered. engine=%s dry_run=%s", video_settings.get('ai_engine'), st.session_state.get('dry_run_flow', 'unknown'))
                    
                    # 진행 상황 표시
                    progress_container = st.container()
                    status_text = st.empty()
                    
                    try:
                        # 필요한 모듈 import
                        import tempfile
                        import os
                        
                        # 이미지 준비
                        status_text.info("📸 이미지 리사이즈 중...")
                        
                        # 리사이즈
                        resized_img = create_resized_preview(selected['image'])
                        
                        # 임시 파일로 저장
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                            # 선택된 소스에 따라 저장
                            if image_source == "original":
                                source_img = selected['image']
                            else:
                                source_img = resized_img
                            source_img.save(tmp_file.name, quality=92)
                            tmp_jpg = tmp_file.name
                            
                            # AI 엔진 선택
                            ai_engine = video_settings.get('ai_engine', 'gemini_veo')
                            prompt = video_settings.get('prompt', prompt_template)
                            
                            if dry_run_flow:
                                status_text.info("🧪 드라이런: 로컬 시뮬레이션 영상 생성 중 (크레딧 소진 없음)...")
                                sim_out = f"outputs/sim_{int(time.time())}.mp4"
                                os.makedirs("outputs", exist_ok=True)
                                logger.info("Generating local simulation video. out=%s", sim_out)
                                result_path = generate_local_simulation_video(resized_img, sim_out, duration=6, fps=30)
                                if os.path.exists(result_path):
                                    status_text.success("✅ 드라이런 완료!")
                                    with open(result_path, 'rb') as f:
                                        vb = f.read()
                                        st.video(vb)
                                        st.download_button("📥 시뮬레이션 영상 다운로드", vb, file_name="simulation.mp4", mime="video/mp4")
                                else:
                                    status_text.error("❌ 드라이런 영상 생성 실패")
                                return
                            
                            if ai_engine == "runway_ai":
                                status_text.info("🚀 Runway AI 설정 확인 중...")
                                logger.info("Runway AI flow started")
                                
                                # Runway AI API 키 확인
                                api_key = os.getenv("RUNWAY_API_KEY")
                                if not api_key:
                                    st.error("❌ RUNWAY_API_KEY 환경변수가 설정되지 않았습니다.")
                                    st.info("💡 터미널에서 다음 명령어로 설정하세요:")
                                    st.code(f'export RUNWAY_API_KEY="runway-api-key"')
                                    return
                                
                                # API 연결 테스트
                                import requests
                                headers = {
                                    'Authorization': f'Bearer {api_key}',
                                    'Content-Type': 'application/json',
                                    'X-Runway-Version': '2024-11-06'
                                }
                                
                                try:
                                    response = requests.get("https://api.dev.runwayml.com/v1/organization", 
                                                          headers=headers, timeout=10)
                                    
                                    if response.status_code == 200:
                                        org_info = response.json()
                                        credit_balance = org_info.get('creditBalance', 0)
                                        
                                        if credit_balance <= 0:
                                            st.warning("⚠️ Runway AI 크레딧 잔액이 부족합니다.")
                                            st.info("💳 크레딧을 충전하려면 [Runway ML](https://runwayml.com) 웹사이트를 방문하세요.")
                                            st.json(org_info)
                                            return
                                        else:
                                            st.success(f"✅ Runway AI 연결 성공! 크레딧 잔액: {credit_balance}")
                                    else:
                                        st.error(f"❌ Runway API 연결 실패: {response.status_code}")
                                        st.text(response.text)
                                        return
                                        
                                except Exception as e:
                                    st.error(f"❌ Runway API 연결 오류: {e}")
                                    return
                                
                                # 실제 비디오 생성 시작
                                status_text.info("🚀 Runway AI로 영상 생성 중...")
                                
                                try:
                                    # 필요한 모듈들 import
                                    import tempfile
                                    import os
                                    import requests
                                    from src.generators.runway.video import RunwayVideoGenerator
                                    
                                    runway_generator = RunwayVideoGenerator()
                                    
                                    # 임시 파일로 이미지 저장 (리사이즈된 이미지 사용)
                                    tmp_image_path = None
                                    try:
                                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                                            # 선택된 이미지를 1080x1920으로 리사이즈
                                            selected_img = st.session_state.selected_image['image']
                                            resized_img = create_resized_preview(selected_img)
                                            
                                            # 리사이즈된 이미지를 바이트로 변환
                                            img_bytes = io.BytesIO()
                                            resized_img.save(img_bytes, format='JPEG', quality=95)
                                            img_bytes.seek(0)
                                            tmp_file.write(img_bytes.getvalue())
                                            
                                            tmp_image_path = tmp_file.name
                                    except Exception as img_error:
                                        st.error(f"이미지 처리 오류: {img_error}")
                                        return
                                    
                                    # 출력 파일 경로 설정
                                    output_path = f"outputs/runway_video_{int(time.time())}.mp4"
                                    os.makedirs("outputs", exist_ok=True)
                                    
                                    # 비디오 생성 (선택된 모델 사용)
                                    selected_model = video_settings.get('runway_model', 'gen3a_turbo')
                                    selected_ratio = video_settings.get('ratio')
                                    dry_run = bool(video_settings.get('dry_run', True))
                                    force_live = not dry_run
                                    logger.info("Runway request: model=%s ratio=%s dry_run=%s", selected_model, selected_ratio, dry_run)
                                    result_path = runway_generator.generate_video_from_image(
                                        image_path=tmp_image_path,
                                        output_path=output_path,
                                        duration=8,  # 8초 고정
                                        prompt=prompt if prompt else "A beautiful video with natural motion",
                                        model=selected_model,
                                        ratio=selected_ratio,
                                        dry_run=dry_run,
                                        force_live=force_live
                                    )
                                    
                                    # 임시 파일 정리
                                    if tmp_image_path and os.path.exists(tmp_image_path):
                                        os.unlink(tmp_image_path)
                                    
                                    if os.path.exists(result_path):
                                        logger.info("Runway video generated at %s", result_path)
                                        status_text.success("✅ Runway AI 비디오 생성 완료!")
                                        st.success(f"🎬 비디오가 생성되었습니다: {result_path}")
                                        
                                        # 비디오 파일 표시
                                        with open(result_path, 'rb') as video_file:
                                            video_bytes = video_file.read()
                                            st.video(video_bytes)
                                        
                                        # 다운로드 버튼
                                        st.download_button(
                                            label="📥 비디오 다운로드",
                                            data=video_bytes,
                                            file_name=f"runway_video_{int(time.time())}.mp4",
                                            mime="video/mp4"
                                        )

                                        # 텍스트 오버레이 적용 (옵션)
                                        # 텍스트 오버레이 비활성화: 원본 영상만 제공
                                    else:
                                        logger.error("Runway video not found at %s", result_path)
                                        status_text.error("❌ 비디오 생성 실패")
                                        
                                except Exception as e:
                                    logger.exception("Runway flow error: %s", e)
                                    status_text.error(f"❌ Runway AI 오류: {e}")
                                    st.error(f"오류 상세: {str(e)}")
                                    
                                return
                                
                                # Runway AI는 여기서 완료, return으로 나머지 코드 스킵
                                safe_unlink(tmp_jpg)  # 임시 파일 삭제(재시도)
                                return
                            
                            # 기타 엔진 계속 (Veo 경로는 비활성화되어 사용하지 않음)
                            
                            # 임시 파일 정리
                            safe_unlink(tmp_jpg)

                            # HiggsField 분기 처리 (실제 생성 → 폴링)
                            if ai_engine == "higgs":
                                status_text.info("🧲 HiggsField로 영상 생성 요청 중...")
                                try:
                                    import requests
                                    # UI 입력값 우선, 없으면 환경변수 사용
                                    api_key = (st.session_state.get("HIGGS_API_KEY", "") or os.getenv("HIGGS_API_KEY", "")).strip()
                                    api_secret = (st.session_state.get("HIGGS_SECRET", "") or os.getenv("HIGGS_SECRET", "")).strip()
                                    if not api_key or not api_secret:
                                        st.error("❌ HIGGS_API_KEY/HIGGS_SECRET 환경변수가 필요합니다.")
                                        return

                                    # 입력 이미지: 선택 항목에서 원본 URL 자동 해석
                                    img_url = resolve_image_url(selected)
                                    if not isinstance(img_url, str) or not img_url.startswith("http"):
                                        st.error("❌ 선택한 이미지의 원본 URL을 찾을 수 없습니다.")
                                        return

                                    # 모션 id와 강도 구성
                                    sel_motion_ids = video_settings.get('higgs_motions', []) or []
                                    strength = float(video_settings.get('motion_strength', 0.5))
                                    motions_payload = [{"id": mid, "strength": strength} for mid in sel_motion_ids]

                                    # 모델/프롬프트/시드
                                    model = video_settings.get('higgs_model', 'dop-turbo')
                                    seed_val = st.session_state.get('seed_value') if 'seed_value' in st.session_state else None

                                    payload = {
                                        "webhook": None,
                                        "params": {
                                            "model": model,
                                            "prompt": prompt,
                                            "seed": int(seed_val) if isinstance(seed_val, int) else 500000,
                                            "motions": motions_payload,
                                            "input_images": [
                                                {"type": "image_url", "image_url": img_url}
                                            ],
                                            "enhance_prompt": True
                                        }
                                    }

                                    headers = {
                                        "Content-Type": "application/json",
                                        "hf-api-key": api_key,
                                        "hf-secret": api_secret
                                    }

                                    resp = requests.post(
                                        "https://platform.higgsfield.ai/v1/image2video/dop",
                                        headers=headers,
                                        json=payload,
                                        timeout=30
                                    )
                                    if resp.status_code >= 400:
                                        st.error(f"❌ Higgs 생성 실패: {resp.status_code}\n{resp.text}")
                                        return
                                    job = resp.json()
                                    job_set_id = job.get("id")
                                    if not job_set_id:
                                        st.error("❌ Higgs 응답에 id(job_set_id)가 없습니다.")
                                        st.json(job)
                                        return

                                    status_text.info(f"⏳ 생성 진행 중 (job_set_id={job_set_id}) …")
                                    # 폴링
                                    start_ts = time.time()
                                    video_url = None
                                    while time.time() - start_ts < 600:
                                        try:
                                            res = requests.get(
                                                f"https://platform.higgsfield.ai/v1/job-sets/{job_set_id}",
                                                headers={"hf-api-key": api_key, "hf-secret": api_secret},
                                                timeout=15
                                            )
                                            if res.status_code == 200:
                                                data = res.json()
                                                # 결과 URL 추출
                                                jobs = data.get("jobs", [])
                                                for j in jobs:
                                                    if str(j.get("status", "")).lower() == "completed":
                                                        results = j.get("results") or {}
                                                        for k in ("raw", "min"):
                                                            obj = results.get(k) or {}
                                                            u = obj.get("url")
                                                            if isinstance(u, str) and u.startswith("http"):
                                                                video_url = u
                                                                break
                                                    if video_url:
                                                        break
                                                if video_url:
                                                    break
                                            elif res.status_code == 422:
                                                pass
                                        except Exception:
                                            pass
                                        time.sleep(4)
                                        waited = int(time.time() - start_ts)
                                        status_text.info(f"⏳ 생성 대기 중… {waited}s")

                                    if not video_url:
                                        st.warning("⚠️ 제한 시간 내 결과 URL을 받지 못했습니다. job_set_id로 수동 조회해 주세요.")
                                        st.code(job_set_id)
                                        return

                                    status_text.success("✅ HiggsField 영상 생성 완료!")
                                    st.video(video_url)
                                    st.download_button("📥 영상 URL 복사", data=video_url, file_name="video_url.txt")
                                    return
                                except Exception as e:
                                    status_text.error(f"❌ HiggsField 오류: {e}")
                                    return
                    
                    except Exception as e:
                        status_text.error(f"❌ 영상 생성 실패: {e}")
                        st.error("🔄 잠시 후 다시 시도하거나, 다른 이미지를 선택해보세요.")
    
    else:
        st.info("👆 사이드바에서 상품 ID를 입력하거나 예시 상품을 선택하세요.")

if __name__ == "__main__":
    main()
