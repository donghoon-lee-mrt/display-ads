#!/usr/bin/env python3
"""
Runway AI 크레딧 잔액 확인 스크립트
"""

import os
import requests

# API 설정
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
if not RUNWAY_API_KEY:
    print("❌ RUNWAY_API_KEY 환경변수가 설정되지 않았습니다!")
    exit(1)

BASE_URL = "https://api.dev.runwayml.com"
HEADERS = {
    'Authorization': f'Bearer {RUNWAY_API_KEY}',
    'Content-Type': 'application/json',
    'X-Runway-Version': '2024-11-06'
}

def check_credits():
    """크레딧 잔액 확인"""
    try:
        print("💳 Runway AI 크레딧 잔액 확인 중...")
        
        response = requests.get(
            f"{BASE_URL}/v1/me",
            headers=HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API 연결 성공!")
            print(f"📊 계정 정보:")
            
            # 크레딧 정보 출력
            if 'credits' in result:
                credits = result['credits']
                print(f"   💰 크레딧 잔액: {credits}")
            else:
                print(f"   📋 전체 응답: {result}")
                
            return result
            
        else:
            print(f"❌ API 오류: {response.status_code}")
            print(f"   응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def check_models():
    """사용 가능한 모델 확인"""
    try:
        print("\n🎬 사용 가능한 모델 확인 중...")
        
        response = requests.get(
            f"{BASE_URL}/v1/models",
            headers=HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 모델 목록:")
            
            for model in models.get('models', []):
                name = model.get('name', 'Unknown')
                cost = model.get('cost_per_second', 'Unknown')
                print(f"   🎯 {name}: {cost} 크레딧/초")
                
            return models
        else:
            print(f"❌ 모델 조회 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 모델 조회 오류: {e}")
        return None

if __name__ == "__main__":
    print("💳 Runway AI 계정 정보 확인")
    print("=" * 50)
    
    # 크레딧 확인
    account_info = check_credits()
    
    # 모델 확인
    models_info = check_models()
    
    print("\n" + "=" * 50)
    if account_info and 'credits' in account_info:
        credits = account_info['credits']
        print(f"💡 결론:")
        print(f"   현재 크레딧: {credits}")
        
        if credits > 0:
            print(f"   🎯 Gen3a Turbo 예상 비용: ~100-200 크레딧")
            print(f"   🎯 VEO3 예상 비용: ~300-400 크레딧")
            
            if credits >= 400:
                print(f"   ✅ VEO3 사용 가능")
            elif credits >= 200:
                print(f"   ⚠️  Gen3a Turbo만 사용 가능")
            elif credits >= 100:
                print(f"   ⚠️  Gen3a Turbo 1번만 시도 가능")
            else:
                print(f"   ❌ 크레딧 부족 - 충전 필요")
        else:
            print(f"   ❌ 크레딧 없음 - 충전 필요")
    else:
        print(f"💡 크레딧 정보를 확인할 수 없습니다.")
        print(f"   Runway 웹사이트에서 직접 확인하세요:")
        print(f"   https://runwayml.com/dashboard")
