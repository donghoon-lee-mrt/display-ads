#!/usr/bin/env python3
"""
Runway API 엔드포인트 탐색
"""

import requests
import json

# API 키와 헤더 설정
api_key = "key_e47c2bf2faaa272d7ae0086589f5606a26167010670823c0d6cd7a8eb4731ba4b62a4172ebe5346c37a5f10ae9fb73598bbd6cdbb1451d1828417384904c238b"
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'X-Runway-Version': '2024-11-06'
}

base_url = "https://api.dev.runwayml.com"

# 가능한 엔드포인트들 테스트
endpoints_to_test = [
    ("GET", "/v1/generations"),
    ("GET", "/v1/tasks"),
    ("POST", "/v1/generations"),
    ("POST", "/v1/generations/image-to-video"),
    ("POST", "/v1/generations/text-to-video"),
    ("POST", "/v1/image-to-video"),
    ("POST", "/v1/text-to-video"),
]

print("🔍 Runway API 엔드포인트 탐색...")
print("="*50)

for method, endpoint in endpoints_to_test:
    try:
        url = f"{base_url}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        else:  # POST
            # 간단한 테스트 데이터
            test_data = {
                "model": "gen3a_turbo",
                "prompt": "test"
            }
            response = requests.post(url, headers=headers, json=test_data, timeout=10)
        
        print(f"📡 {method} {endpoint}")
        print(f"   상태: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ 성공!")
            try:
                result = response.json()
                print(f"   📄 응답: {json.dumps(result, indent=2)[:200]}...")
            except:
                print(f"   📄 응답: {response.text[:100]}...")
        elif response.status_code == 400:
            print(f"   ⚠️ 잘못된 요청 (엔드포인트는 존재)")
            print(f"   📄 오류: {response.text[:100]}...")
        elif response.status_code == 404:
            print(f"   ❌ 존재하지 않는 엔드포인트")
        else:
            print(f"   📄 응답: {response.text[:100]}...")
            
    except Exception as e:
        print(f"   💥 오류: {e}")
    
    print()

print("="*50)
print("💡 크레딧이 0이므로 실제 생성은 불가능하지만, 엔드포인트 구조를 파악할 수 있습니다.")
