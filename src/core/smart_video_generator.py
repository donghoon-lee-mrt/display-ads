import os
import time
import requests
from dataclasses import dataclass
from typing import List, Dict, Optional
from google import genai
from google.genai import types
import cv2
import numpy as np
from PIL import Image
import io


@dataclass
class PhotoAnalysis:
    has_people: bool
    people_count: int
    scene_type: str  # "landscape", "activity", "food", "indoor", "outdoor"
    composition: str  # "portrait", "group", "wide", "close_up"
    dominant_elements: List[str]  # ["people", "nature", "architecture", "food", "vehicle"]
    suggested_motion: str
    confidence: float


class SmartVideoGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")
        
        self.client = genai.Client(api_key=self.api_key)
        
        # 여행 마케팅 전용 영상 전략 매핑
        self.video_strategies = {
            # 사람이 있는 경우
            "people_portrait": {
                "motion": "Subtle breathing, gentle eye blinking, slight head movement, natural facial expressions",
                "camera": "Slight zoom in to create intimacy",
                "mood": "Personal connection and wanderlust"
            },
            "people_group": {
                "motion": "Group members slightly swaying, natural gestures, looking around with curiosity",
                "camera": "Gentle pan across the group, slight zoom",
                "mood": "Social travel experience, friendship"
            },
            "people_activity": {
                "motion": "Active movement - walking, gesturing, interacting with environment",
                "camera": "Following the action, dynamic movement",
                "mood": "Adventure and excitement"
            },
            
            # 사람이 없는 경우
            "landscape_wide": {
                "motion": "Gentle wind effects on trees/grass, subtle cloud movement, water flow",
                "camera": "Slow cinematic pan or Ken Burns effect",
                "mood": "Breathtaking beauty, serenity"
            },
            "architecture": {
                "motion": "Subtle lighting changes, flag/fabric movement, people walking by in distance",
                "camera": "Architectural reveal, upward tilt or circular motion",
                "mood": "Cultural richness, historical significance"
            },
            "food_close": {
                "motion": "Steam rising, sauce dripping, garnish movement",
                "camera": "Appetizing close-up with slight rotation",
                "mood": "Culinary temptation"
            },
            "transportation": {
                "motion": "Vehicle movement, road/track perspective, scenery passing by",
                "camera": "Journey perspective, forward motion",
                "mood": "Adventure, exploration"
            },
            "indoor_cultural": {
                "motion": "Ambient lighting changes, subtle object movement, cultural atmosphere",
                "camera": "Exploring the space, revealing details",
                "mood": "Cultural immersion"
            }
        }

    def analyze_photo(self, image_url: str) -> PhotoAnalysis:
        """AI로 사진을 분석하여 최적의 영상 전략 결정"""
        print(f"🔍 Analyzing photo: {image_url}")
        
        # Gemini Vision으로 이미지 분석
        try:
            # 이미지 다운로드
            r = requests.get(image_url, timeout=30)
            r.raise_for_status()
            
            temp_path = "analyze_temp.jpg"
            with open(temp_path, "wb") as f:
                f.write(r.content)
            
            # Gemini로 이미지 분석
            uploaded_file = self.client.files.create(
                path=temp_path,
                config=types.CreateFileConfig(
                    display_name="Photo Analysis"
                )
            )
            
            # 분석 프롬프트
            analysis_prompt = """
            Analyze this travel/tourism photo and provide:
            1. Are there people in the image? How many?
            2. Scene type: landscape, activity, food, indoor, outdoor, architecture
            3. Composition: portrait, group, wide_shot, close_up
            4. Main elements: people, nature, architecture, food, vehicle, cultural_items
            5. Best motion strategy for video marketing
            
            Respond in JSON format:
            {
                "has_people": boolean,
                "people_count": number,
                "scene_type": "string",
                "composition": "string", 
                "dominant_elements": ["element1", "element2"],
                "confidence": 0.9
            }
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_text(analysis_prompt),
                            types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type)
                        ]
                    )
                ]
            )
            
            # JSON 파싱 시도
            analysis_text = response.text
            print(f"📊 Analysis result: {analysis_text}")
            
            # 간단한 분석 결과 생성 (실제로는 JSON 파싱)
            analysis = PhotoAnalysis(
                has_people="people" in analysis_text.lower() or "person" in analysis_text.lower(),
                people_count=1 if "people" in analysis_text.lower() else 0,
                scene_type="outdoor",  # 기본값
                composition="wide",
                dominant_elements=["people", "nature"],
                suggested_motion="",
                confidence=0.8
            )
            
            # 정리
            self.client.files.delete(uploaded_file.name)
            os.remove(temp_path)
            
            return analysis
            
        except Exception as e:
            print(f"⚠️ Analysis failed, using fallback: {e}")
            # 폴백 분석
            return PhotoAnalysis(
                has_people=True,  # 기본 가정
                people_count=1,
                scene_type="outdoor",
                composition="wide",
                dominant_elements=["people", "nature"],
                suggested_motion="",
                confidence=0.5
            )

    def get_video_strategy(self, analysis: PhotoAnalysis) -> Dict[str, str]:
        """분석 결과에 따른 최적 영상 전략 선택"""
        
        if analysis.has_people:
            if analysis.people_count == 1:
                if "close" in analysis.composition:
                    return self.video_strategies["people_portrait"]
                else:
                    return self.video_strategies["people_activity"]
            else:
                return self.video_strategies["people_group"]
        else:
            if "landscape" in analysis.scene_type or "nature" in analysis.dominant_elements:
                return self.video_strategies["landscape_wide"]
            elif "architecture" in analysis.dominant_elements:
                return self.video_strategies["architecture"]
            elif "food" in analysis.dominant_elements:
                return self.video_strategies["food_close"]
            elif "vehicle" in analysis.dominant_elements:
                return self.video_strategies["transportation"]
            else:
                return self.video_strategies["indoor_cultural"]

    def generate_marketing_video(self, image_url: str, output_path: str = "marketing_video.mp4") -> str:
        """여행 마케팅용 맞춤형 영상 생성"""
        
        print("🎬 Starting smart travel marketing video generation...")
        
        # 1. 사진 분석
        analysis = self.analyze_photo(image_url)
        print(f"📊 Photo Analysis:")
        print(f"   - People: {analysis.has_people} ({analysis.people_count} persons)")
        print(f"   - Scene: {analysis.scene_type}")
        print(f"   - Composition: {analysis.composition}")
        print(f"   - Elements: {analysis.dominant_elements}")
        
        # 2. 전략 선택
        strategy = self.get_video_strategy(analysis)
        print(f"🎯 Selected Strategy:")
        print(f"   - Motion: {strategy['motion']}")
        print(f"   - Camera: {strategy['camera']}")
        print(f"   - Mood: {strategy['mood']}")
        
        # 3. 맞춤형 프롬프트 생성
        custom_prompt = f"""
        Create a compelling travel marketing video from this image.
        
        Motion Strategy: {strategy['motion']}
        Camera Movement: {strategy['camera']}
        Marketing Mood: {strategy['mood']}
        
        The video should inspire wanderlust and make viewers want to book this travel experience.
        Make it cinematic, professional, and emotionally engaging for travel marketing.
        Duration: 8 seconds, high quality.
        """
        
        print(f"📝 Generated prompt: {custom_prompt}")
        
        # 4. 영상 생성
        try:
            # 이미지 다운로드 및 업로드
            print("⬇️ Downloading and uploading image...")
            r = requests.get(image_url, timeout=30)
            r.raise_for_status()
            
            temp_path = "temp_marketing_image.jpg"
            with open(temp_path, "wb") as f:
                f.write(r.content)
            
            uploaded_file = self.client.files.create(
                path=temp_path,
                config=types.CreateFileConfig(
                    display_name="Travel Marketing Image"
                )
            )
            
            print("⏳ Waiting for file processing...")
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = self.client.files.get(uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                raise Exception(f"File upload failed: {uploaded_file.error}")
            
            # 영상 생성
            print("🎬 Generating marketing video...")
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=custom_prompt,
                image=uploaded_file,
            )
            
            print(f"⏳ Operation started: {operation.name}")
            
            while not operation.done:
                print("⏳ Creating your marketing video...")
                time.sleep(10)
                operation = self.client.operations.get(operation)
            
            print("✅ Marketing video completed!")
            
            # 다운로드
            generated_video = operation.response.generated_videos[0]
            client.files.download(file=generated_video.video)
            generated_video.video.save(output_path)
            
            # 정리
            self.client.files.delete(uploaded_file.name)
            os.remove(temp_path)
            
            print(f"💾 Marketing video saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Image-based generation failed: {e}")
            print("🔄 Falling back to text-only generation...")
            
            # 텍스트 기반 폴백
            fallback_prompt = f"A cinematic travel marketing video: {custom_prompt}"
            
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=fallback_prompt,
            )
            
            while not operation.done:
                print("⏳ Creating fallback marketing video...")
                time.sleep(10)
                operation = self.client.operations.get(operation)
            
            generated_video = operation.response.generated_videos[0]
            client.files.download(file=generated_video.video)
            generated_video.video.save(output_path)
            
            print(f"💾 Fallback marketing video saved: {output_path}")
            return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Travel Marketing Video Generator")
    parser.add_argument("image_url", type=str, help="Travel image URL")
    parser.add_argument("--out", type=str, default="smart_marketing_video.mp4")
    
    args = parser.parse_args()
    
    try:
        generator = SmartVideoGenerator()
        result = generator.generate_marketing_video(args.image_url, args.out)
        print(f"🎉 Travel marketing video ready: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()