# Docker 실행 가이드

## 🐳 빠른 시작

### 1. Docker Compose 사용 (권장)

```bash
# 환경변수 설정 (.env 파일 생성)
cat > .env << EOF
HIGGS_API_KEY=your-higgs-api-key
GOOGLE_API_KEY=your-google-api-key
EOF

# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 2. Docker CLI 사용

```bash
# 이미지 빌드
docker build -t display-ads:latest .

# 3000번 포트 사용 중인 프로세스 종료 (macOS/Linux)
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# 컨테이너 실행
docker run -d \
  --name display-ads-app \
  -p 3000:3000 \
  -e HIGGS_API_KEY="your-higgs-api-key" \
  -e GOOGLE_API_KEY="your-google-api-key" \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/logs:/app/logs \
  display-ads:latest

# 로그 확인
docker logs -f display-ads-app

# 중지 및 제거
docker stop display-ads-app
docker rm display-ads-app
```

## 📍 접속

브라우저에서 http://localhost:3000 접속

## 🔧 문제 해결

### 포트 충돌
3000번 포트를 사용 중인 프로세스가 있으면 자동으로 종료됩니다.
수동으로 종료하려면:

```bash
# macOS/Linux
lsof -ti:3000 | xargs kill -9

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### 컨테이너 재시작
```bash
docker-compose restart
# 또는
docker restart display-ads-app
```

### 로그 확인
```bash
# Docker Compose
docker-compose logs -f

# Docker CLI
docker logs -f display-ads-app

# 호스트 시스템에서
tail -f logs/app.log
```

### 이미지 재빌드
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache

# 또는
docker build --no-cache -t display-ads:latest .
```

## 💾 데이터 영속성

다음 디렉토리가 호스트 시스템에 마운트됩니다:
- `./outputs` - 생성된 비디오 파일
- `./logs` - 애플리케이션 로그
- `./media` - 미디어 템플릿 및 샘플

## 🎯 환경변수

필수 환경변수:
- `HIGGS_API_KEY` - Higgs API 키
- `GOOGLE_API_KEY` - Google API 키 (선택사항)

Streamlit 설정 (자동 설정됨):
- `STREAMLIT_SERVER_PORT=3000`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`
- `STREAMLIT_SERVER_HEADLESS=true`

## 🔒 보안 주의사항

⚠️ `.env` 파일을 Git에 커밋하지 마세요!
⚠️ 프로덕션 환경에서는 Docker Secrets 또는 환경변수 관리 도구 사용을 권장합니다.
