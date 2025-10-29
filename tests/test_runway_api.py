#!/usr/bin/env python3
"""
Runway API 연결 테스트
"""

import os
import requests

# API 키 설정
api_key = "key_e47c2bf2faaa272d7ae0086589f5606a26167010670823c0d6cd7a8eb4731ba4b62a4172ebe5346c37a5f10ae9fb73598bbd6cdbb1451d1828417384904c238b"

# 헤더 설정 (X-Runway-Version 필수!)
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'X-Runway-Version': '2024-11-06'  # 최신 API 버전
}

# 기본 API 연결 테스트
base_url = "https://api.dev.runwayml.com"

print("🚀 Runway API 연결 테스트...")
print(f"📡 Base URL: {base_url}")
print(f"🔑 API Key: {api_key[:20]}...")

# 조직 정보 확인 (가능한 엔드포인트)
try:
    response = requests.get(f"{base_url}/v1/organization", headers=headers, timeout=30)
    print(f"📊 상태 코드: {response.status_code}")
    print(f"📋 응답 헤더: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✅ API 연결 성공!")
        print(f"📄 응답 내용: {response.json()}")
    else:
        print(f"❌ API 연결 실패: {response.status_code}")
        print(f"📄 오류 내용: {response.text}")
        
except Exception as e:
    print(f"❌ 연결 오류: {e}")

print("\n" + "="*50)

# 사용 가능한 엔드포인트 확인
endpoints_to_test = [
    "/v1/tasks",
    "/v1/models", 
    "/v1/generate",
    "/v1/image-to-video",
    "/v1/text-to-video"
]

for endpoint in endpoints_to_test:
    try:
        print(f"🔍 테스트 엔드포인트: {endpoint}")
        response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
        print(f"   상태: {response.status_code}")
        if response.status_code != 404:
            print(f"   응답: {response.text[:100]}...")
    except Exception as e:
        print(f"   오류: {e}")
    print()
