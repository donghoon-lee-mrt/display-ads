#!/usr/bin/env python3
"""
Runway AI Task 상태 확인 스크립트
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

# 확인할 Task ID
TASK_ID = "3a7e1765-99fe-4f18-9e36-37acf0951ce8"

def check_task_status(task_id: str):
    """Task 상태 확인"""
    try:
        print(f"🔍 Task ID 확인 중: {task_id}")
        
        response = requests.get(
            f"{BASE_URL}/v1/tasks/{task_id}",
            headers=HEADERS,
            timeout=30
        )
        
        print(f"📡 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Task 정보:")
            print(f"   상태: {result.get('status', 'Unknown')}")
            print(f"   진행률: {result.get('progress', 'Unknown')}%")
            
            if 'video_url' in result:
                print(f"   🎬 영상 URL: {result['video_url']}")
                return result['video_url']
            elif 'output' in result and isinstance(result['output'], list) and len(result['output']) > 0:
                video_url = result['output'][0]
                print(f"   🎬 영상 URL: {video_url}")
                return video_url
            else:
                print(f"   📋 전체 응답: {result}")
                return None
                
        else:
            print(f"❌ API 오류: {response.status_code}")
            print(f"   응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def download_video(video_url: str, output_path: str):
    """영상 다운로드"""
    try:
        print(f"📥 영상 다운로드 중: {video_url}")
        
        response = requests.get(video_url, timeout=120)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        print(f"✅ 다운로드 완료: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        return False

if __name__ == "__main__":
    print("🎬 Runway AI Task 상태 확인")
    print("=" * 50)
    
    # Task 상태 확인
    video_url = check_task_status(TASK_ID)
    
    if video_url:
        print("\n🎉 영상이 완성되었습니다!")
        
        # 다운로드 시도
        output_path = f"outputs/recovered_runway_video_{TASK_ID[:8]}.mp4"
        os.makedirs("outputs", exist_ok=True)
        
        if download_video(video_url, output_path):
            print(f"\n🎊 영상 복구 성공!")
            print(f"📁 저장 위치: {output_path}")
        else:
            print(f"\n⚠️  영상은 존재하지만 다운로드 실패")
            print(f"🌐 브라우저에서 직접 다운로드: {video_url}")
    else:
        print("\n😞 영상이 아직 완성되지 않았거나 실패한 것 같습니다.")
        print("💡 Runway 웹사이트에서 직접 확인해보세요:")
        print("   https://runwayml.com/dashboard")
