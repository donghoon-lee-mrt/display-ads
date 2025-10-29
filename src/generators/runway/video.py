#!/usr/bin/env python3
"""
Runway AI를 사용한 이미지-비디오 생성
"""

import os
import requests
import time
from typing import Optional, Dict, Any
from PIL import Image
import json


class RunwayVideoGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RUNWAY_API_KEY")
        if not self.api_key:
            raise ValueError("RUNWAY_API_KEY 환경변수가 필요합니다")
        
        self.base_url = "https://api.dev.runwayml.com"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Runway-Version': '2024-11-06'
        }
        # 글로벌 세이프가드: RUNWAY_LIVE=1 일 때만 실제 호출 허용
        self.live_mode = os.getenv('RUNWAY_LIVE', '0') == '1'
    
    def generate_video_from_image(
        self, 
        image_path: str, 
        output_path: str,
        duration: int = 8,
        motion_strength: float = 0.5,
        seed: Optional[int] = None,
        prompt: Optional[str] = None,
        model: str = "gen3a_turbo",
        ratio: Optional[str] = None,
        dry_run: bool = False,
        force_live: bool = False
    ) -> str:
        """
        이미지에서 비디오 생성
        
        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 비디오 경로
            duration: 비디오 길이 (초) - VEO3는 8초 고정
            motion_strength: 움직임 강도 (0.0-1.0)
            seed: 시드값 (재현성을 위해)
            prompt: 추가 텍스트 프롬프트
            
        Returns:
            str: 생성된 비디오 경로
        """
        try:
            # 로그를 웹앱과 터미널 모두에 출력
            try:
                import streamlit as st
                st.info(f"🎬 Runway AI로 비디오 생성 시작...")
                st.info(f"📁 입력: {image_path}")
                st.info(f"📁 출력: {output_path}")
            except:
                pass
            
            print(f"🎬 Runway AI로 비디오 생성 시작...")
            print(f"📁 입력: {image_path}")
            print(f"📁 출력: {output_path}")
            
            # 1단계: 이미지를 base64로 인코딩
            base64_image = self._encode_image_to_base64(image_path)
            
            try:
                import streamlit as st
                st.info(f"📤 이미지 인코딩 완료")
            except:
                pass
            print(f"📤 이미지 인코딩 완료")
            
            # 모델별 허용 duration 규칙 적용
            request_duration = duration
            if model == 'veo3':
                request_duration = 8
            elif model == 'gen3a_turbo':
                # gen3a_turbo: 5 또는 10만 허용 (명세)
                if request_duration not in [5, 10]:
                    request_duration = 10

            # 요청 페이로드(로그용)
            payload_preview: Dict[str, Any] = {
                'model': model,
                'ratio': ratio,
                'duration': request_duration,
                'seed': seed,
                'promptText': (prompt[:160] + '...') if (prompt and len(prompt) > 160) else prompt,
                'promptImage': f"data:image/jpeg;base64,(length={len(base64_image) if base64_image else 0})"
            }

            # 드라이런/세이프가드: API 호출 없이 로직만 검증하고 플레이스홀더 비디오 생성
            # force_live=True 이면 환경변수 없이도 라이브 호출 허용
            effective_dry_run = dry_run or (not self.live_mode and not force_live)
            if effective_dry_run:
                try:
                    import streamlit as st
                    st.info("🧪 드라이런 모드: Runway API 호출 없이 로직 검증")
                    if not self.live_mode and not force_live:
                        st.warning("🔐 RUNWAY_LIVE=1 미설정 → 강제 드라이런 모드")
                    st.json(payload_preview)
                except:
                    pass
                print("🧪 드라이런 모드 실행 (페이로드 미전송):")
                print(json.dumps(payload_preview, ensure_ascii=False))

                # 플레이스홀더 비디오 생성 (선택 비율에 맞춘 짧은 샘플)
                self._create_placeholder_video(output_path, ratio)
                return output_path

            # 2단계: 비디오 생성 작업 시작 (실제 API 호출)
            if not self.live_mode and not force_live:
                raise RuntimeError("RUNWAY_LIVE=1 이 설정되지 않아 라이브 호출이 차단되었습니다.")
            task_id = self._start_generation_task(
                base64_image=base64_image,
                duration=request_duration,
                seed=seed,
                prompt=prompt,
                model=model,
                ratio=ratio
            )
            print(f"🚀 생성 작업 시작: {task_id}")
            
            # 3단계: 작업 완료 대기
            video_url = self._wait_for_completion(task_id)
            print(f"✅ 생성 완료: {video_url}")
            
            # 4단계: 비디오 다운로드
            self._download_video(video_url, output_path)
            print(f"💾 다운로드 완료: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Runway AI 비디오 생성 실패: {e}")
            raise
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """이미지를 base64로 인코딩 (크기 제한)"""
        import base64
        from PIL import Image
        
        # 이미지 크기 확인 및 조정
        with Image.open(image_path) as img:
            # 최대 크기 제한 (16MB 이하로)
            max_size = (1920, 1080)  # 더 작은 크기로 제한
            
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
                
                # 임시로 리사이즈된 이미지 저장
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    img.save(tmp.name, 'JPEG', quality=85, optimize=True)
                    temp_path = tmp.name
            else:
                temp_path = image_path
        
        # 파일 크기 확인
        import os
        file_size = os.path.getsize(temp_path)
        if file_size > 16 * 1024 * 1024:  # 16MB 초과
            raise Exception(f"이미지 파일이 너무 큽니다: {file_size / 1024 / 1024:.1f}MB (최대 16MB)")
        
        # base64 인코딩
        with open(temp_path, 'rb') as f:
            image_data = f.read()
        
        # 임시 파일 정리
        if temp_path != image_path:
            os.unlink(temp_path)
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_image}"
    
    def _start_generation_task(
        self, 
        base64_image: str, 
        duration: int = 8, 
        seed: Optional[int] = None,
        prompt: Optional[str] = None,
        model: str = "gen3a_turbo",
        ratio: Optional[str] = None
    ) -> str:
        """비디오 생성 작업 시작"""
        # Runway API 문서에 따른 올바른 페이로드 (해상도 추가)
        payload = {
            'model': model,  # 사용자가 선택한 모델 사용
            'promptImage': base64_image
        }
        
        # 모델별 지원 해상도 설정 (UI에서 전달된 ratio가 있으면 우선 적용)
        if ratio:
            payload['ratio'] = ratio
        else:
            if model == 'gen3a_turbo':
                payload['ratio'] = '768:1280'  # 세로 (3:5, 세로 전용)
            elif model == 'veo3':
                payload['ratio'] = '720:1280'  # 세로 (9:16)
            elif model == 'gen4_turbo':
                payload['ratio'] = '720:1280'  # 세로 (9:16)

        # duration 설정 (명세 준수)
        if model == 'veo3':
            payload['duration'] = 8
        elif model == 'gen3a_turbo':
            payload['duration'] = duration if duration in [5, 10] else 10
        else:
            # gen4_turbo 등: 명세상 5/8/10 허용. 전달된 값 우선, 없으면 10
            payload['duration'] = duration if duration in [5, 8, 10] else 10
        
        # 선택적 파라미터들
        if prompt:
            payload['promptText'] = prompt
        if seed is not None:
            payload['seed'] = seed
        
        response = requests.post(
            f"{self.base_url}/v1/image_to_video",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        
        # 오류 상세 정보 출력
        if response.status_code != 200:
            try:
                import streamlit as st
                error_detail = response.json() if response.text else "응답 없음"
                st.error(f"❌ Runway API 오류 ({response.status_code}): {error_detail}")
                print(f"❌ 요청 페이로드: {payload}")
                print(f"❌ 응답 상태: {response.status_code}")
                print(f"❌ 응답 내용: {response.text}")
            except:
                print(f"❌ 요청 페이로드: {payload}")
                print(f"❌ 응답 상태: {response.status_code}")
                print(f"❌ 응답 내용: {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        
        # Streamlit에서도 보이도록 로그 출력
        try:
            import streamlit as st
            st.info(f"🔍 Runway API 응답: {result}")
            print(f"🔍 API 응답: {result}")  # 터미널 로그
        except:
            print(f"🔍 API 응답: {result}")  # 터미널 로그만
        
        # 가능한 키들 확인
        if 'task_id' in result:
            return result['task_id']
        elif 'id' in result:
            return result['id']
        elif 'taskId' in result:
            return result['taskId']
        else:
            error_msg = f"응답에서 task ID를 찾을 수 없습니다. 응답 키: {list(result.keys())}, 전체 응답: {result}"
            try:
                import streamlit as st
                st.error(f"❌ {error_msg}")
                print(f"❌ {error_msg}")
            except:
                print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def _wait_for_completion(self, task_id: str, max_wait_time: int = 1800) -> str:
        """작업 완료 대기 (최대 30분)"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # 작업 상태 확인
            response = requests.get(
                f"{self.base_url}/v1/tasks/{task_id}",  # v1 추가
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            status = result.get('status')
            
            # 웹앱과 터미널 모두에 상태 표시
            try:
                import streamlit as st
                elapsed = int(time.time() - start_time)
                st.info(f"⏳ 상태: {status} (대기 시간: {elapsed}초)")
            except:
                pass
            print(f"⏳ 상태: {status}")
            
            if status in ['completed', 'COMPLETED', 'SUCCEEDED']:
                # 비디오 URL 찾기 (여러 응답 형태 대응)
                video_url = self._extract_video_url(result)
                if video_url:
                    return video_url
                # 응답에서 비디오 URL을 찾을 수 없는 경우
                try:
                    import streamlit as st
                    st.info(f"🔍 완료된 작업 응답: {result}")
                except:
                    pass
                print(f"🔍 완료된 작업 응답: {result}")
                raise Exception(f"비디오 URL을 찾을 수 없습니다. 응답: {result}")
            elif status in ['failed', 'FAILED']:
                raise Exception(f"비디오 생성 실패: {result.get('error', '알 수 없는 오류')}")
            
            # 10초 대기
            time.sleep(10)
        
        raise Exception("비디오 생성 시간 초과 (30분)")
    
    def _download_video(self, video_url: str, output_path: str):
        """생성된 비디오 다운로드"""
        response = requests.get(video_url, timeout=120)
        response.raise_for_status()
        
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(response.content)

    def _extract_video_url(self, result: Any) -> Optional[str]:
        """Runway 작업 응답에서 비디오 URL을 최대한 유연하게 추출"""
        try:
            # 딕셔너리 최상위 후보 키
            if isinstance(result, dict):
                for key in ['video_url', 'videoUrl', 'output_url', 'url']:
                    val = result.get(key)
                    if isinstance(val, str) and val.startswith('http'):
                        return val

                # 'output' / 'outputs' / 'assets' 등 다양한 컨테이너 처리
                containers = [
                    result.get('output'),
                    result.get('outputs'),
                    result.get('assets'),
                    result.get('result'),
                ]
                for cont in containers:
                    # 문자열이면 바로 URL로 간주
                    if isinstance(cont, str) and cont.startswith('http'):
                        return cont
                    # 딕셔너리면 URL 키를 탐색
                    if isinstance(cont, dict):
                        for key in ['url', 'video_url', 'videoUrl']:
                            val = cont.get(key)
                            if isinstance(val, str) and val.startswith('http'):
                                return val
                    # 리스트면 각 요소 검사
                    if isinstance(cont, list):
                        for item in cont:
                            if isinstance(item, str) and item.startswith('http'):
                                return item
                            if isinstance(item, dict):
                                for key in ['url', 'video_url', 'videoUrl']:
                                    val = item.get(key) if hasattr(item, 'get') else None
                                    if isinstance(val, str) and val.startswith('http'):
                                        return val

            # 문자열 전체가 곧 URL인 경우
            if isinstance(result, str) and result.startswith('http'):
                return result
        except Exception as e:
            print(f"⚠️ 비디오 URL 파싱 중 오류: {e}")
        return None

    def _create_placeholder_video(self, output_path: str, ratio: Optional[str]):
        """드라이런용 플레이스홀더 비디오 생성 (2초, 검은 화면)
        ratio에 맞춰 해상도를 설정한다.
        """
        # 기본 세로 비율
        width, height = self._resolution_from_ratio(ratio or '720:1280')
        duration = 2
        try:
            import ffmpeg  # ffmpeg-python
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            (
                ffmpeg
                .input(f"color=c=black:s={width}x{height}:d={duration}", f='lavfi')
                .output(output_path, vcodec='libx264', pix_fmt='yuv420p', r=30, movflags='+faststart', loglevel='error')
                .overwrite_output()
                .run()
            )
            try:
                import streamlit as st
                st.success(f"✅ 플레이스홀더 비디오 생성: {output_path} ({width}x{height})")
            except:
                pass
        except Exception as e:
            print(f"⚠️ ffmpeg 생성 실패, OpenCV 대체 시도: {e}")
            try:
                import cv2
                import numpy as np
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(output_path, fourcc, 30.0, (width, height))
                if not writer.isOpened():
                    raise RuntimeError("OpenCV VideoWriter open failed")
                black = np.zeros((height, width, 3), dtype=np.uint8)
                total_frames = duration * 30
                for _ in range(total_frames):
                    writer.write(black)
                writer.release()
                try:
                    import streamlit as st
                    st.success(f"✅ (OpenCV) 플레이스홀더 생성: {output_path} ({width}x{height})")
                except:
                    pass
            except Exception as e2:
                print(f"⚠️ OpenCV 생성도 실패: {e2}")
                # 최종 실패 시 최소한의 파일로 대체 (유효하지 않을 수 있음)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(b'')

    def _resolution_from_ratio(self, ratio: str) -> tuple[int, int]:
        """ratio 문자열을 해상도 (width, height)로 변환"""
        try:
            left, right = ratio.split(':')
            w, h = int(left), int(right)
            # 최소 해상도 보정 (너무 작은 경우 스트리밍 이슈 방지)
            return max(w, 320), max(h, 320)
        except Exception:
            # 기본 720x1280 (세로 9:16)
            return 720, 1280


def main():
    """테스트용 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Runway AI 비디오 생성')
    parser.add_argument('--image', required=True, help='입력 이미지 경로')
    parser.add_argument('--output', required=True, help='출력 비디오 경로')
    parser.add_argument('--duration', type=int, default=5, help='비디오 길이 (초)')
    parser.add_argument('--motion', type=float, default=0.5, help='움직임 강도 (0.0-1.0)')
    parser.add_argument('--prompt', help='추가 텍스트 프롬프트')
    parser.add_argument('--seed', type=int, help='시드값')
    
    args = parser.parse_args()
    
    try:
        generator = RunwayVideoGenerator()
        result = generator.generate_video_from_image(
            image_path=args.image,
            output_path=args.output,
            duration=args.duration,
            motion_strength=args.motion,
            prompt=args.prompt,
            seed=args.seed
        )
        print(f"✅ 성공: {result}")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        exit(1)


if __name__ == "__main__":
    main()
