import os
import time
import requests
from google import genai
from google.genai import types


class GeminiCorrectVideoGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        
        self.client = genai.Client(api_key=self.api_key)

    def generate_video_from_image_url(self, image_url: str, output_path: str = "correct_veo_video.mp4") -> str:
        """공식 문서의 올바른 방식으로 이미지→영상 생성"""
        
        print("🎬 Starting Correct Gemini Video Generation...")
        print(f"📸 Image URL: {image_url}")
        
        try:
            # Step 1: 이미지를 바이트로 다운로드 (공식 문서 방식)
            print("⬇️ Downloading image as bytes...")
            image_bytes = requests.get(image_url).content
            print(f"💾 Image downloaded: {len(image_bytes)} bytes")
            
            # Step 2: 이미지를 Image 객체로 변환 (bytes + mimeType)
            print("🔄 Building types.Image object...")
            image_obj = types.Image(imageBytes=image_bytes, mimeType="image/jpeg")
            print("✅ Image object created successfully")
            
            # Step 3: 여행 마케팅 프롬프트
            travel_prompt = """
            Transform this travel destination image into a compelling marketing video.
            
            Create natural, cinematic movement:
            - If there are people: subtle breathing, gentle head movements, natural expressions
            - If it's a landscape: gentle wind effects, soft lighting changes, cloud movement
            - If it's architecture: atmospheric lighting, subtle environmental effects
            - Make it feel alive and inspiring for travel marketing
            
            Duration: 8 seconds, high quality, cinematic style.
            The video should inspire wanderlust and make viewers want to visit this destination.
            """
            
            # Step 4: 영상 생성 (올바른 방식)
            print("🎬 Generating video with correct method...")
            
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=travel_prompt,
                image=image_obj,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",  # 세로형 (인스타그램/틱톡용)
                    resolution="720p",
                    person_generation="allow_adult"
                )
            )
            
            print(f"🚀 Video generation started: {operation.name}")
            
            # Step 5: 작업 완료 대기
            print("⏳ Waiting for video generation...")
            while not operation.done:
                print("⏳ Creating travel marketing video...")
                time.sleep(10)
                operation = self.client.operations.get(operation)
            
            print("✅ Video generation completed!")
            
            # Step 6: 다운로드 (공식 방식)
            print("💾 Downloading generated video...")
            generated_video = operation.response.generated_videos[0]
            
            # 공식 문서 방식
            self.client.files.download(file=generated_video.video)
            generated_video.video.save(output_path)
            
            print(f"🎉 SUCCESS! Video saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Correct method failed: {e}")
            
            # 상세 오류 정보
            if "INVALID_ARGUMENT" in str(e):
                print("💡 Tip: Image format or size issue")
            elif "RESOURCE_EXHAUSTED" in str(e):
                print("💡 Tip: API quota exceeded, wait or get new key")
            elif "PERMISSION_DENIED" in str(e):
                print("💡 Tip: Check API key permissions")
            
            import traceback
            traceback.print_exc()
            
            # 폴백: 텍스트 기반
            print("🔄 Trying text-only fallback...")
            try:
                fallback_prompt = f"""
                Create a cinematic travel marketing video.
                Scene: A beautiful Myanmar temple with golden architecture and peaceful atmosphere.
                {travel_prompt}
                """
                
                operation = self.client.models.generate_videos(
                    model="veo-3.0-generate-001",
                    prompt=fallback_prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio="9:16",
                        resolution="720p"
                    )
                )
                
                while not operation.done:
                    print("⏳ Creating fallback video...")
                    time.sleep(10)
                    operation = self.client.operations.get(operation)
                
                generated_video = operation.response.generated_videos[0]
                self.client.files.download(file=generated_video.video)
                generated_video.video.save(output_path)
                
                print(f"💾 Fallback video saved: {output_path}")
                return output_path
                
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
                return None


def test_image_analysis(image_url: str):
    """이미지 분석 테스트 (디버깅용)"""
    
    print("🔍 Testing image analysis first...")
    
    try:
        client = genai.Client()
        image_bytes = requests.get(image_url).content
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                image_part,
                "Describe this travel destination image in detail. What do you see?"
            ]
        )
        
        print(f"✅ Image analysis successful:")
        print(f"📝 {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Image analysis failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Correct Gemini Video Generator")
    parser.add_argument("image_url", type=str, help="Image URL")
    parser.add_argument("--out", type=str, default="correct_travel_video.mp4")
    parser.add_argument("--test-only", action="store_true", help="Only test image analysis")
    
    args = parser.parse_args()
    
    try:
        if args.test_only:
            # 이미지 분석만 테스트
            test_image_analysis(args.image_url)
        else:
            # 전체 영상 생성
            generator = GeminiCorrectVideoGenerator()
            result = generator.generate_video_from_image_url(args.image_url, args.out)
            if result:
                print(f"🎉 FINAL SUCCESS: {result}")
            else:
                print("❌ FINAL FAILURE")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
