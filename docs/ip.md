# Implementation Plan — Option G-A (추천)

## 1) 선택 아키텍처
- Workflows(오케스트레이션) + Pub/Sub(큐) + Cloud Run/Run Jobs(수집·합성) + GCS(저장) + Vision OCR + Vertex AI(Text) + Monitoring + Secret Manager
- 근거: 경량/확장성/관측성 균형, 브랜딩 제어(FFmpeg 템플릿) 용이

## 2) 상위 플로우(텍스트 다이어그램)
[URL] → [Cloud Run Fetch] → [GCS raw/] → [Vision OCR] → [Vertex 카피/검수] → [Run Jobs FFmpeg 합성] → [GCS final/]

## 3) 모듈 계획
- Ingest(Cloud Run): URL 유효성/응답 검사 → 이미지·JSON 저장(GCS raw/)
- Validate(Cloud Run): 9:16·해상도·필수 필드·금칙어 1차 점검
- Transform(Vision/Vertex): OCR → 키프레이즈/가격 라벨링 → 4문장 생성·검수
- Synthesize(Run Jobs): FFmpeg(drawtext/zoompan/ducking)로 15초/4컷 합성, 자막 번인
- Package(Cloud Run): MP4/SRT/썸네일/manifest 생성, 메타 업데이트
- Notify: (v0 제외)
- Observe: 처리시간·실패율·OCR 신뢰도 대시보드

## 4) 스토리지 설계(GCS)
- gs://<project>-marketing-raw/{run_id}/... (원본 이미지, source.json)
- gs://<project>-marketing-proc/{run_id}/... (OCR 결과, 텍스트 중간물)
- gs://<project>-marketing-final/{run_id}/{mp4|srt|thumb|manifest.json}
- run_id: yyyyMMdd_HHmmss_XXXX(난수4)

## 5) 설정/시크릿
- Secret Manager: API 키(외부 호출시)
- 템플릿 설정 JSON: 폰트/컬러/자막 위치/여백/안전영역

## 6) API/트리거
- HTTP 입력(Cloud Run): { url, meta?, priority? }
- Pub/Sub: batch 처리(옵션), 재시도 설정
- Workflows: 실시간/10분 배치 트리거
- 외부 정보 API: base=https://api3.myrealtrip.com/traveler-experiences/api/web/v2/traveler, endpoint=/products/{product_id}/header

## 7) 합성(FFmpeg) 스펙
- 캔버스: 1080×1920, 15초, 4컷 기본
- 효과: Ken Burns(zoompan), 자막 번인(drawtext), BGM 덕킹
- 산출: MP4(H.264), SRT, 썸네일(JPEG), manifest(JSON)

## 8) 실패/재시도
- 각 스텝 지수 백오프(최대 3회) → 실패 시 보류 큐(topic: hold) 이동
- 재실행: run_id 기준 재처리 엔드포인트 제공

## 9) 관측/알림
- 로깅: 구조화 로그(JSON), 민감값 마스킹(price/promo)
- 메트릭: 처리시간, 실패율, OCR 신뢰도, 평균 렌더시간
- 알림: (v0 제외)

## 10) 보안
- 최소권한 IAM, 버킷 분리(raw/proc/final), Signed URL
- 서비스 계정 단일 책임 원칙

## 11) 비용 대략치(초기)
- Vision OCR/Vertex 단가 저용량 구간, Run Jobs 소량 사용(일 10건) → 월 수십달러 예상

## 12) DECISION
- 버킷 네이밍 규칙 확정, 보존기간(Lifecycle)
- 템플릿 JSON 스키마(폰트/컬러/자막 안전영역)
- (보류) 알림 채널/권한 — v0 제외

## 13) QUESTION
- 정보 API 인증·제한(쿼터/속도) 정책?
- BGM 소스 경로 및 라이선스 증빙 방법?
- 재처리 기준/라벨(수동 제외규칙)?