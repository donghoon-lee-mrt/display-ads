import os
import time
from google import genai
from google.genai import types


class GeminiURLVideoGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        
        self.client = genai.Client(api_key=self.api_key)

    def generate_video_from_url(self, image_url: str, output_path: str = "url_based_video.mp4") -> str:
        """이미지 URL을 직접 사용하여 영상 생성"""
        
        print("🎬 Starting URL-based video generation...")
        print(f"📸 Image URL: {image_url}")
        
        # 여행 마케팅용 프롬프트
        travel_prompt = """
        Transform this travel destination image into a compelling marketing video.
        
        Add natural, cinematic movement:
        - If there are people: subtle breathing, gentle head movements, natural expressions
        - If it's a landscape: gentle wind effects, water movement, cloud drifting
        - If it's architecture: atmospheric lighting changes, subtle environmental movement
        
        Make it feel alive and inspiring for travel marketing.
        Duration: 8 seconds, high quality, cinematic.
        The video should make viewers want to visit this destination.
        """
        
        try:
            print("🎬 Generating video from image URL...")
            
            # 방법 1: 이미지 URL을 직접 사용 (올바른 API)
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=travel_prompt,
                image_uri=image_url,
            )
            
            print(f"🚀 Video generation started: {operation.name}")
            
            # 생성 완료 대기
            max_generation_time = 300  # 5분
            wait_time = 0
            
            while not operation.done and wait_time < max_generation_time:
                print(f"⏳ Creating travel video from URL... ({wait_time}s)")
                time.sleep(10)
                wait_time += 10
                operation = self.client.operations.get(operation)
            
            if not operation.done:
                raise Exception("Video generation timeout")
            
            print("✅ Video generation completed!")
            
            # 결과 다운로드
            generated_video = operation.response.generated_videos[0]
            
            print("💾 Downloading video...")
            # 올바른 비디오 다운로드 방법
            video_data = self.client.files.download(generated_video.video)
            with open(output_path, 'wb') as f:
                f.write(video_data)
            
            print(f"🎉 URL-based travel video saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ URL-based generation failed: {e}")
            print("🔄 Trying simple prompt with URL reference...")
            
            # 방법 2: 단순 텍스트 프롬프트에 URL 언급
            fallback_prompt = f"""
            Create a cinematic travel marketing video based on this image: {image_url}
            
            {travel_prompt}
            """
            
            try:
                operation = self.client.models.generate_videos(
                    model="veo-3.0-generate-001",
                    prompt=fallback_prompt,
                )
                
                while not operation.done:
                    print("⏳ Creating fallback video...")
                    time.sleep(10)
                    operation = self.client.operations.get(operation)
                
                generated_video = operation.response.generated_videos[0]
                
                video_data = self.client.files.download(generated_video.video)
                with open(output_path, 'wb') as f:
                    f.write(video_data)
                
                print(f"💾 Fallback video saved: {output_path}")
                return output_path
                
            except Exception as fallback_error:
                print(f"❌ All methods failed: {fallback_error}")
                raise fallback_error


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini URL-based Video Generator")
    parser.add_argument("image_url", type=str, help="Image URL")
    parser.add_argument("--out", type=str, default="url_based_video.mp4")
    
    args = parser.parse_args()
    
    try:
        generator = GeminiURLVideoGenerator()
        result = generator.generate_video_from_url(args.image_url, args.out)
        print(f"🎉 Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
