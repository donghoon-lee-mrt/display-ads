#!/usr/bin/env python3
"""
Smart Travel Marketing Video Generator Runner
여행 상품 사진을 분석하여 맞춤형 마케팅 영상 생성
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.smart_video_generator import SmartVideoGenerator

def main():
    # 테스트용 여행 이미지들
    test_cases = [
        {
            "name": "People Portrait",
            "url": "https://dry7pvlp22cox.cloudfront.net/mrt-images-prod/2024/09/26/Pyat/stQgJttsVT.jpg",
            "expected": "인물 중심 - 미묘한 움직임과 감정 표현"
        },
        {
            "name": "Landscape",
            "url": "https://example.com/landscape.jpg",  # 실제 URL로 교체 필요
            "expected": "풍경 - 자연스러운 환경 움직임"
        }
    ]
    
    if len(sys.argv) > 1:
        # 커맨드라인 인자가 있으면 해당 URL 처리
        image_url = sys.argv[1]
        output_name = sys.argv[2] if len(sys.argv) > 2 else "smart_marketing_video.mp4"
        
        print(f"🎬 Processing single image: {image_url}")
        
        generator = SmartVideoGenerator()
        result = generator.generate_marketing_video(image_url, output_name)
        print(f"✅ Result: {result}")
        
    else:
        # 테스트 케이스 실행
        print("🎬 Running Smart Video Generator Test Cases...")
        
        generator = SmartVideoGenerator()
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{'='*50}")
            print(f"Test Case {i}: {case['name']}")
            print(f"Expected: {case['expected']}")
            print(f"{'='*50}")
            
            try:
                output_name = f"test_case_{i}_{case['name'].lower().replace(' ', '_')}.mp4"
                result = generator.generate_marketing_video(case['url'], output_name)
                print(f"✅ Test {i} completed: {result}")
                
            except Exception as e:
                print(f"❌ Test {i} failed: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()