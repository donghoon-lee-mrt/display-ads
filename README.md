# 🎬 Marketing Video Generator

AI 기반 마케팅 비디오 자동 생성 시스템

## 📋 개요

이 프로젝트는 여러 AI 서비스(Gemini, Runway, VEO)를 활용하여 마케팅 비디오를 자동으로 생성하는 Streamlit 웹 애플리케이션입니다.

## 🚀 주요 기능

- **다중 AI 엔진 지원**: Gemini, Runway, VEO 등 다양한 AI 서비스 통합
- **실시간 미리보기**: Streamlit 기반 웹 인터페이스
- **자동 비디오 생성**: 이미지에서 비디오로 자동 변환
- **템플릿 시스템**: 재사용 가능한 비디오 템플릿
- **배치 처리**: 여러 제품에 대한 일괄 비디오 생성

## 📁 프로젝트 구조

```
marketing_1/
├── README.md                    # 프로젝트 설명서
├── app.py                      # 메인 Streamlit 애플리케이션
├── requirements.txt            # Python 패키지 의존성
│
├── src/                        # 소스 코드
│   ├── core/                   # 핵심 비즈니스 로직
│   ├── generators/             # AI 비디오 생성기들
│   │   ├── gemini/            # Google Gemini 관련
│   │   ├── runway/            # Runway AI 관련
│   │   └── veo/               # VEO 관련
│   └── utils/                  # 유틸리티 함수들
│
├── scripts/                    # 실행 스크립트들
├── media/                      # 미디어 파일들
│   ├── samples/               # 샘플 파일들
│   ├── templates/             # 템플릿 파일들
│   └── archive/               # 완료된 작업물들
│
├── outputs/                    # 생성된 비디오 결과물
├── data/                       # 데이터 파일들
├── docs/                       # 프로젝트 문서들
├── tmp/                        # 임시 파일들
└── tests/                      # 테스트 파일들
```

## 🛠 설치 및 실행

⚠️ **자세한 설치 가이드는 [SETUP_GUIDE.md](./SETUP_GUIDE.md)를 참조하세요!**

### 빠른 시작
```bash
# 1. 가상환경 설정
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 2. 패키지 설치
pip install -r requirements.txt

# 3. API 키 설정
export GOOGLE_API_KEY="your-api-key"

# 4. 애플리케이션 실행
streamlit run app.py
```

## 🔧 사용법

1. **웹 브라우저**에서 `http://localhost:8501` 접속
2. **제품 ID** 입력 또는 **이미지 업로드**
3. **AI 엔진** 선택 (Gemini/Runway/VEO)
4. **비디오 생성** 버튼 클릭
5. **결과 확인** 및 다운로드

## 📊 지원하는 AI 서비스

- **Google Gemini**: 텍스트-비디오, 이미지-비디오 생성
- **Runway**: 고품질 비디오 생성 및 편집
- **VEO**: 빠른 비디오 프로토타이핑

## 🎯 주요 스크립트

- `run_gemini_veo.py`: Gemini VEO 실행
- `run_runway_video.py`: Runway 비디오 생성
- `run_smart_video.py`: 스마트 비디오 생성
- `run_ai_motion.py`: AI 모션 효과 적용

## 📈 출력 형식

- **비디오 파일**: MP4 형식 (1080x1920, 9:16 비율)
- **썸네일**: JPG 형식
- **메타데이터**: JSON 형식으로 생성 정보 저장

## 🔍 문제 해결

### 일반적인 오류
- **API 키 오류**: 환경 변수 설정 확인
- **메모리 부족**: 비디오 해상도 조정
- **네트워크 오류**: 인터넷 연결 및 방화벽 확인

### 로그 확인
```bash
# 로그 파일 위치
logs/
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch
3. Commit your Changes
4. Push to the Branch
5. Open a Pull Request

## 🔧 디버깅 완료 사항

✅ **모든 import 경로 수정 완료**
- scripts 폴더의 모든 실행 파일들이 새로운 모듈 구조에 맞게 업데이트됨
- `src/generators/`, `src/utils/`, `src/core/` 경로로 정리

✅ **requirements.txt 보완**
- streamlit, numpy, matplotlib 등 누락된 패키지 추가
- 모든 필수 의존성 패키지 포함

✅ **사용자 가이드 제공**
- 상세한 설치 가이드: [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- 문제 해결 방법 및 팁 포함

## 📄 라이선스

이 프로젝트는 개인 사용을 위한 프로젝트입니다.

## 📞 연락처

프로젝트 관련 문의사항은 GitHub Issues를 통해 남겨주세요.