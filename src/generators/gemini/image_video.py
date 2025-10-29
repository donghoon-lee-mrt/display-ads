import os
import time
import requests
from google import genai
from google.genai import types
import cv2
import tempfile


class GeminiImageVideoGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        
        self.client = genai.Client(api_key=self.api_key)
        
        # 여행 마케팅 전용 프롬프트 템플릿
        self.travel_prompts = {
            "people_activity": "The person in this travel photo comes alive with natural movement - gentle breathing, subtle head movements, looking around with wonder and excitement. The scene should feel like a living travel moment that inspires wanderlust.",
            
            "landscape": "This beautiful travel destination comes to life with gentle natural movements - leaves swaying, water flowing, clouds drifting. The scene should evoke the peaceful beauty that travelers seek.",
            
            "cultural_site": "This cultural landmark becomes a living scene with subtle atmospheric changes - gentle lighting shifts, distant movement of visitors, flags or fabric moving in the breeze. The scene should inspire cultural exploration.",
            
            "food_scene": "This delicious travel cuisine comes alive with appetizing details - steam rising, sauce glistening, garnishes moving slightly. The scene should make viewers crave this culinary experience."
        }

    def analyze_image_content(self, image_url: str) -> str:
        """이미지 내용을 분석하여 적절한 프롬프트 선택"""
        print(f"🔍 Analyzing image content...")
        
        # 간단한 휴리스틱으로 이미지 타입 결정
        # 실제로는 Gemini Vision으로 분석할 수 있지만, 우선 기본 전략 사용
        
        if "people" in image_url.lower() or "person" in image_url.lower():
            return "people_activity"
        elif "food" in image_url.lower() or "dish" in image_url.lower():
            return "food_scene"  
        elif "temple" in image_url.lower() or "palace" in image_url.lower() or "museum" in image_url.lower():
            return "cultural_site"
        else:
            return "landscape"

    def generate_video_from_image(self, image_url: str, output_path: str = "gemini_travel_video.mp4") -> str:
        """Gemini API로 이미지 기반 여행 마케팅 영상 생성"""
        
        print("🎬 Starting Gemini image-based video generation...")
        print(f"📸 Image URL: {image_url}")
        
        try:
            # 1. 이미지 다운로드
            print("⬇️ Downloading image...")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            print(f"💾 Image saved to: {temp_path}")
            
            # 2. 이미지 분석 및 프롬프트 선택
            content_type = self.analyze_image_content(image_url)
            prompt = self.travel_prompts[content_type]
            
            print(f"🎯 Content type: {content_type}")
            print(f"📝 Using prompt: {prompt}")
            
            # 3. Gemini에 파일 업로드 (올바른 API 방식)
            print("📤 Uploading to Gemini...")
            
            try:
                # 최신 API 방식 시도
                uploaded_file = self.client.files.upload(temp_path)
                print(f"✅ File uploaded successfully: {uploaded_file.name}")
                
            except Exception as upload_error:
                print(f"❌ Upload failed: {upload_error}")
                raise upload_error
            
            # 4. 파일 처리 대기
            print("⏳ Waiting for file processing...")
            max_wait = 60  # 최대 60초 대기
            wait_time = 0
            
            while uploaded_file.state.name == "PROCESSING" and wait_time < max_wait:
                time.sleep(2)
                wait_time += 2
                uploaded_file = self.client.files.get(uploaded_file.name)
                print(f"⏳ Processing... ({wait_time}s)")
            
            if uploaded_file.state.name == "FAILED":
                raise Exception(f"File processing failed: {uploaded_file.error}")
            
            if uploaded_file.state.name == "PROCESSING":
                print("⚠️ File still processing, proceeding anyway...")
            
            print(f"✅ File ready: {uploaded_file.state.name}")
            
            # 5. 영상 생성
            print("🎬 Generating video with Veo...")
            
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=prompt,
                image=uploaded_file,
            )
            
            print(f"🚀 Video generation started: {operation.name}")
            
            # 6. 생성 완료 대기
            max_generation_time = 300  # 5분
            wait_time = 0
            
            while not operation.done and wait_time < max_generation_time:
                print(f"⏳ Creating your travel video... ({wait_time}s)")
                time.sleep(10)
                wait_time += 10
                operation = self.client.operations.get(operation)
            
            if not operation.done:
                raise Exception("Video generation timeout")
            
            print("✅ Video generation completed!")
            
            # 7. 결과 다운로드
            generated_video = operation.response.generated_videos[0]
            
            print("💾 Downloading video...")
            # 올바른 다운로드 방식 (video_bytes 사용)
            with open(output_path, 'wb') as f:
                f.write(generated_video.video.video_bytes)
            
            print(f"🎉 Travel marketing video saved: {output_path}")
            
            # 8. 정리
            self.client.files.delete(uploaded_file.name)
            os.unlink(temp_path)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Image-based generation failed: {e}")
            print("🔄 Trying text-only fallback...")
            
            # 텍스트 기반 폴백
            fallback_prompt = f"A cinematic travel marketing video: {prompt}. Professional quality, 8 seconds duration."
            
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=fallback_prompt,
            )
            
            while not operation.done:
                print("⏳ Creating fallback video...")
                time.sleep(10)
                operation = self.client.operations.get(operation)
            
            generated_video = operation.response.generated_videos[0]
            with open(output_path, 'wb') as f:
                f.write(generated_video.video.video_bytes)
            
            print(f"💾 Fallback video saved: {output_path}")
            return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini Image-based Video Generator")
    parser.add_argument("image_url", type=str, help="Image URL")
    parser.add_argument("--out", type=str, default="gemini_travel_video.mp4")
    
    args = parser.parse_args()
    
    try:
        generator = GeminiImageVideoGenerator()
        result = generator.generate_video_from_image(args.image_url, args.out)
        print(f"🎉 Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
