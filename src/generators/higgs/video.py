import os
import time
import json
import pathlib
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import requests


@dataclass
class HiggsSpec:
    """영상 생성 스펙 정의.

    실제 API 스키마를 받기 전까지는 최소 필드만 유지한다.
    """

    model: str = "higgs-video-1"
    prompt: str = ""
    aspect_ratio: str = "9:16"
    resolution: str = "1080x1920"
    duration_seconds: int = 14


class HiggsVideoGenerator:
    """HiggsField 영상 생성 어댑터(스켈레톤).

    실제 엔드포인트/스키마 수신 후 _create_task/_poll_task/_download_result를 업데이트한다.
    """

    def __init__(self, output_dir: pathlib.Path) -> None:
        self.output_dir = pathlib.Path(output_dir)
        # Higgsfield job-sets: https://platform.higgsfield.ai
        self.api_key = os.getenv("HIGGS_API_KEY", "")
        self.api_secret = os.getenv("HIGGS_SECRET", "")
        self.base_url = os.getenv("HIGGS_BASE_URL", "https://platform.higgsfield.ai")
        self.api_version = os.getenv("HIGGS_API_VERSION", "v1")

        if not self.api_key:
            raise RuntimeError("HIGGS_API_KEY가 설정되지 않았습니다. 환경변수를 설정하세요.")
        # 시크릿은 일부 조회 엔드포인트에서 생략 가능하도록 허용

        self.session = requests.Session()

    # ---------- Public API ----------
    def generate(self, spec: HiggsSpec, *, image_path: Optional[str] = None) -> pathlib.Path:
        """영상 생성 전체 플로우.

        1) 작업 생성 → 2) 상태 폴링 → 3) 결과 다운로드
        """

        task_id = self._create_task(spec=spec, image_path=image_path)
        result = self._poll_task(task_id=task_id, timeout_sec=900, interval_sec=5)
        video_url = result.get("video_url")
        if not video_url:
            raise RuntimeError("HiggsField 결과에 video_url이 없습니다.")

        output_path = self.output_dir / f"higgs_{int(time.time())}.mp4"
        self._download_result(url=video_url, output_path=output_path)
        return output_path

    # ---------- Internal helpers (to be finalized with real API spec) ----------
    def _headers(self) -> Dict[str, str]:
        # Per docs: use 'hf-api-key' and 'hf-secret'
        headers = {
            "hf-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        if self.api_secret:
            headers["hf-secret"] = self.api_secret
        return headers

    def _create_task(self, spec: HiggsSpec, image_path: Optional[str]) -> str:
        # 생성 엔드포인트는 공개 문서에 없어 안전하게 미구현 처리
        raise NotImplementedError("HiggsField 생성 API는 미구현입니다. 기존 job_set_id로 폴링을 사용하세요.")

    def _poll_task(self, task_id: str, *, timeout_sec: int, interval_sec: int) -> Dict[str, Any]:
        # GET /v1/job-sets/{job_set_id}
        status_url = f"{self.base_url}/{self.api_version}/job-sets/{task_id}"
        waited = 0
        while waited <= timeout_sec:
            resp = self.session.get(status_url, headers=self._headers(), timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                status = self._aggregate_status(data)
                if status == "completed":
                    video_url = self._extract_first_video_url(data)
                    return {"video_url": video_url, "raw": data}
                if status in ("failed", "error"):
                    raise RuntimeError(f"HiggsField 작업 실패: {json.dumps(data, ensure_ascii=False)}")
            elif resp.status_code == 422:
                # not ready / invalid
                pass
            time.sleep(interval_sec)
            waited += interval_sec
        raise TimeoutError("HiggsField 작업이 시간 내 완료되지 않았습니다.")

    @staticmethod
    def _aggregate_status(job_set: Dict[str, Any]) -> str:
        try:
            jobs: List[Dict[str, Any]] = job_set.get("jobs", [])
            statuses = {str(job.get("status", "")).lower() for job in jobs}
            if not statuses:
                return "unknown"
            if statuses == {"completed"}:
                return "completed"
            if {"failed", "error"} & statuses:
                return "failed"
            if statuses & {"queued", "processing", "running"}:
                return "running"
            return "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def _extract_first_video_url(job_set: Dict[str, Any]) -> Optional[str]:
        try:
            for job in job_set.get("jobs", []):
                results = job.get("results") or {}
                for key in ("raw", "min"):
                    obj = results.get(key) or {}
                    url = obj.get("url")
                    if isinstance(url, str) and url.startswith("http"):
                        return url
        except Exception:
            pass
        return None

    def get_job_set(self, job_set_id: str) -> Dict[str, Any]:
        status_url = f"{self.base_url}/{self.api_version}/job-sets/{job_set_id}"
        resp = self.session.get(status_url, headers=self._headers(), timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"HiggsField 조회 실패: {resp.status_code} {resp.text}")
        return resp.json()

    def _download_result(self, url: str, output_path: pathlib.Path) -> None:
        with self.session.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)




