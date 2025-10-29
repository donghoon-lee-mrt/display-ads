#!/usr/bin/env python3
"""
Runway AI 비디오 생성 실행 스크립트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from generators.runway.video import RunwayVideoGenerator

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Runway AI 비디오 생성')
    parser.add_argument('--product-id', required=True, help='상품 ID')
    parser.add_argument('--image', required=True, help='입력 이미지 경로')
    parser.add_argument('--duration', type=int, default=5, help='비디오 길이 (초)')
    parser.add_argument('--motion', type=float, default=0.5, help='움직임 강도 (0.0-1.0)')
    parser.add_argument('--prompt', help='추가 텍스트 프롬프트')
    parser.add_argument('--seed', type=int, help='시드값')
    
    args = parser.parse_args()
    
    # 출력 경로 설정
    output_dir = f"outputs/{args.product_id}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/runway_raw.mp4"
    
    try:
        print(f"🎬 Runway AI로 비디오 생성 시작...")
        print(f"📋 상품 ID: {args.product_id}")
        print(f"🖼️ 입력 이미지: {args.image}")
        print(f"⏱️ 길이: {args.duration}초")
        print(f"🎯 움직임 강도: {args.motion}")
        if args.prompt:
            print(f"📝 프롬프트: {args.prompt}")
        
        generator = RunwayVideoGenerator()
        result = generator.generate_video_from_image(
            image_path=args.image,
            output_path=output_path,
            duration=args.duration,
            motion_strength=args.motion,
            prompt=args.prompt,
            seed=args.seed
        )
        
        print(f"✅ Runway AI 비디오 생성 성공!")
        print(f"📁 출력: {result}")
        
    except Exception as e:
        print(f"❌ Runway AI 비디오 생성 실패: {e}")
        exit(1)


if __name__ == "__main__":
    main()
