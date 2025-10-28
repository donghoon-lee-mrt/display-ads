# 🚀 Marketing Video Generator 설치 및 실행 가이드

이 가이드는 다른 사용자가 이 프로젝트를 쉽게 설정하고 실행할 수 있도록 도와줍니다.

## 📋 시스템 요구사항

- **Python**: 3.8 이상
- **운영체제**: macOS, Linux, Windows
- **메모리**: 최소 4GB RAM (8GB 권장)
- **디스크 공간**: 최소 2GB 여유 공간

## 🛠 설치 단계

### 1단계: 프로젝트 다운로드
```bash
# 프로젝트 폴더를 원하는 위치에 복사
cd /your/desired/path
# marketing_1 폴더를 여기에 복사
```

### 2단계: Python 가상환경 설정
```bash
cd marketing_1

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### 3단계: 패키지 설치
```bash
# 필수 패키지 설치
pip install -r requirements.txt

# FFmpeg 설치 (비디오 처리용)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# Windows:
# https://ffmpeg.org/download.html 에서 다운로드
```

### 4단계: API 키 설정

#### Google API 키 설정
1. [Google AI Studio](https://aistudio.google.com/app/apikey)에서 API 키 생성
2. 환경 변수 설정:
```bash
# macOS/Linux:
export GOOGLE_API_KEY="your-api-key-here"

# Windows:
set GOOGLE_API_KEY=your-api-key-here
```

#### 기타 API 키 (선택사항)
- **Runway API**: Runway 비디오 생성 기능 사용 시 필요
- **VEO API**: VEO 비디오 생성 기능 사용 시 필요

## 🚀 실행 방법

### 메인 웹 애플리케이션 실행
```bash
# 가상환경이 활성화된 상태에서
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

### 개별 스크립트 실행
```bash
# Gemini VEO 비디오 생성
python scripts/run_gemini_veo.py "https://example.com/image.jpg"

# 스마트 비디오 생성
python scripts/run_smart_video.py

# AI 모션 효과
python scripts/run_ai_motion.py "https://example.com/image.jpg"

# 이미지 슬라이드쇼
python scripts/run_image_slideshow.py 12345  # 상품 ID
```

## 📁 프로젝트 구조 이해

```
marketing_1/
├── app.py                  # 메인 Streamlit 웹앱
├── requirements.txt        # Python 패키지 목록
├── SETUP_GUIDE.md         # 이 가이드 파일
├── README.md              # 프로젝트 설명
│
├── src/                   # 소스 코드
│   ├── core/              # 핵심 비즈니스 로직
│   ├── generators/        # AI 비디오 생성기들
│   │   ├── gemini/       # Google Gemini 관련
│   │   ├── runway/       # Runway AI 관련
│   │   └── veo/          # VEO 관련
│   └── utils/            # 유틸리티 함수들
│
├── scripts/              # 실행 스크립트들
├── media/                # 미디어 파일들
│   ├── samples/         # 샘플 파일들
│   ├── templates/       # 템플릿 파일들
│   └── archive/         # 완료된 작업물들
│
├── outputs/              # 생성된 비디오 결과물
├── data/                 # 데이터 파일들
├── docs/                 # 프로젝트 문서들
└── tests/                # 테스트 파일들
```

## 🔧 문제 해결

### 일반적인 오류

#### 1. ModuleNotFoundError
```
ModuleNotFoundError: No module named 'streamlit'
```
**해결책**: 가상환경이 활성화되었는지 확인하고 패키지를 다시 설치
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. API 키 오류
```
Error: API key not found
```
**해결책**: 환경 변수가 제대로 설정되었는지 확인
```bash
echo $GOOGLE_API_KEY  # macOS/Linux
echo %GOOGLE_API_KEY%  # Windows
```

#### 3. FFmpeg 오류
```
FFmpeg not found
```
**해결책**: FFmpeg가 설치되었고 PATH에 있는지 확인
```bash
ffmpeg -version
```

#### 4. 메모리 부족 오류
**해결책**: 
- 비디오 해상도를 낮춤
- 다른 애플리케이션을 종료하여 메모리 확보

### 로그 확인
```bash
# 로그 파일 위치
ls logs/

# 실시간 로그 확인
tail -f logs/*.log
```

## 🎯 사용 팁

### 1. 첫 실행 시
- 간단한 이미지로 테스트해보세요
- 네트워크 연결이 안정적인지 확인하세요
- API 키가 유효한지 확인하세요

### 2. 성능 최적화
- 고해상도 이미지는 처리 시간이 오래 걸립니다
- 배치 처리 시 한 번에 너무 많은 작업을 하지 마세요
- 메모리 사용량을 모니터링하세요

### 3. 결과물 관리
- 생성된 비디오는 `outputs/` 폴더에 저장됩니다
- 정기적으로 불필요한 파일을 정리하세요

## 📞 지원

문제가 발생하면:
1. 이 가이드의 문제 해결 섹션을 확인하세요
2. 로그 파일을 확인하세요
3. GitHub Issues에 문제를 보고하세요

## 🔄 업데이트

프로젝트 업데이트 시:
```bash
# 가상환경 활성화
source .venv/bin/activate

# 패키지 업데이트
pip install -r requirements.txt --upgrade
```

---

**즐거운 비디오 제작 되세요! 🎬✨**