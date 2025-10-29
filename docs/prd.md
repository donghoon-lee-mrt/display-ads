# PRD — Short-form 자동 생성 PoC (marketing_1)

## 0) Problem Sync — Q&A 요약
- 문제: 하나의 URL에서 이미지·정보를 읽어 15초(1080×1920) 숏폼을 자동 제작, OCR/AI로 문구 추출·자막 입히기
- 해결 의도: IG/YouTube용 영상 일 10개 자동 생산, 제작 리소스 최소화
- 기대 변화: 기획·편집 수작업 축소, 일관 포맷과 운영 가시성 확보
- 현재 제약: Google Cloud/Workspace만 사용 (GCS, Vision, Vertex, Workflows 등)
- 합의 상태: ✅

## 1) 목표(Goals)
- URL 1건 입력 → ≤ 2분 내 15초 MP4(1080×1920) + SRT + 썸네일 자동 산출
- 자막 스크립트 4문장 자동 생성(이모지/CTA 규칙 포함), 금칙어·톤 규칙 준수
- 일 10건 규모 안정 처리(자동 재시도/보류 큐), 단순 검수 흐름 유지(v0, 알림 제외)

## 2) 범위(Scope)
- In: URL 수집, OCR, 카피 생성/검수, 합성(FFmpeg), 산출물 패키징, 관측/알림
- Out: 플랫폼 업로드 자동화(IG/YouTube 업로드는 v1 이후)

## 3) 성공지표(Success Metrics)
- Dry-run(샘플 20건): 렌더 성공 ≥ 90%, OCR 평균 신뢰도 ≥ 85%
- v0: 1 URL → ≤ 2분 산출, 검수 패스율 ≥ 80%
- 파일럿: 일 10건 안정 처리, 자동 회복 ≥ 95%
- v1: 금칙어·톤 준수 ≥ 95%, 평균 렌더 ≤ 60초/건

## 4) 제약(Constraints)
- 인프라: Google Cloud/Workspace만 사용 (GCS, Vision, Vertex, Workflows, Cloud Run/Run Jobs 등)
- 해상도/규격: 1080×1920, 길이 15초, 4컷 기본
- 보안: Secret Manager(자격/키), 최소권한 IAM, 로그 민감값(가격/쿠폰) 마스킹

## 5) 사용자/시나리오(User & Journeys)
- 사용자: PO/운영(요청·검수), 에디터(톤·금칙어), 엔지니어(파이프라인)
- 여정(요약): "URL 투입 → 자동 처리 → 썸네일 생성 → 링크 열람/검수 → 저장"

## 6) 입력/출력 정의(IO)
- 입력: URL(일 10건), 이미지(최대 약 110장), 정보 API(JSON: title, desc, price, promo, cta; base=https://api3.myrealtrip.com/traveler-experiences/api/web/v2/traveler, endpoint=/products/{product_id}/header)
- 출력: MP4(1080×1920), SRT, 썸네일, manifest(JSON)
- 자리표시자: {{title}}, {{price}}, {{promo}}, {{cta_text}}, {{cta_url_short}} 등 포함(이미지는 header.images[].url 사용)

## 7) 상위 아키텍처(Option)
- 추천 G-A: Workflows + Pub/Sub + Cloud Run/Run Jobs + GCS + Vision + Vertex + Monitoring + Secret Manager — 경량·확장·관측성 균형
- 대안 G-B: Cloud Functions + Cloud Tasks 체인(간단·경량)
- 대안 G-C: Transcoder API 병행(품질/용량 튜닝)

## 8) 운영/관측
- 재시도: 지수 백오프 3회 후 보류 큐로 이동, 수동 재실행 경로 제공
- 관측: 처리시간, 실패율, OCR 신뢰도 대시보드; 주간 리포트(문서/스프레드시트)
- 알림: (v0 제외)

## 9) 위험/트레이드오프
- 초기 템플릿·룰(폰트/컬러/자막 규칙) 설계 공수 필요
- Functions/Tasks 분산 시 추적성 일부 저하 가능
- Transcoder 병행 시 관리 포인트/비용 증가 가능

## 10) 미리보기 산출물(Outcome Preview)
- 선택/합의: ① 자막 스크립트 초안(15초, 4문장, 이모지·CTA 규칙) + ② 시퀀스 표(컷/길이/이미지/모션/자막/오디오) 5~7행
- 수용 기준: 자리표시자 포함, 업로드 규격(1080×1920) 그대로

## 11) 비기능 요구사항(NFR)
- 성능: 1건 ≤ 2분(v0), 평균 렌더 ≤ 60초(v1)
- 신뢰성: 자동 회복 ≥ 95%, 실패 큐 재처리 지원
- 보안/프라이버시: 최소권한 IAM, 비밀 관리, 민감정보 마스킹

## 12) DECISION
- 템플릿 폰트/컬러/브랜딩 룰 초안 확정(파일 형식: JSON)
- BGM/효과음 라이선스 정책(사내 에셋 vs 무료 라이브러리)
- (보류) 알림 채널/레이아웃 — v0 제외

## 13) QUESTION
- 정보 API의 스키마 최종 확정(title/desc/price/promo/cta 상세 필드?)
- 금칙어/톤 규칙의 구체 기준(예시와 허용/금지 리스트)
- 대상 플랫폼별 안전영역/자막 가이드(IG Reels vs Shorts 차이)
