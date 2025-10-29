import os
import time
import requests
import tempfile
from google import genai
from google.genai import types


class GeminiOfficialVideoGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        
        self.client = genai.Client(api_key=self.api_key)

    def generate_video_from_image_url(self, image_url: str, output_path: str = "official_veo_video.mp4") -> str:
        """공식 문서 방식으로 이미지 URL에서 영상 생성"""
        
        print("🎬 Starting Official Gemini Video Generation...")
        print(f"📸 Image URL: {image_url}")
        
        try:
            # Step 1: 이미지 다운로드 및 업로드
            print("⬇️ Downloading image...")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            print(f"💾 Image saved: {temp_path}")
            
            # Step 2: Gemini에 파일 업로드 (공식 방식)
            print("📤 Uploading to Gemini...")
            uploaded_file = self.client.files.upload(file=temp_path)
            print(f"✅ File uploaded: {uploaded_file.name}")
            
            # 파일 처리 대기
            print("⏳ Waiting for file processing...")
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = self.client.files.get(uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                raise Exception(f"File processing failed")
            
            print(f"✅ File ready: {uploaded_file.state.name}")
            
            # Step 3: 여행 마케팅 프롬프트
            travel_prompt = """
            Transform this travel destination into a cinematic marketing video.
            
            Create natural, inspiring movement:
            - If there are people: subtle breathing, gentle expressions, natural movement
            - If it's a landscape: gentle wind effects, soft lighting changes
            - If it's architecture: atmospheric ambience, subtle environmental effects
            
            Make it feel alive and compelling for travel marketing.
            Duration: 8 seconds, cinematic quality, inspiring wanderlust.
            """
            
            # Step 4: 영상 생성 (공식 문서 방식)
            print("🎬 Generating video with Veo 3...")
            
            operation = self.client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=travel_prompt,
                image=uploaded_file,  # 업로드된 파일 객체 직접 사용
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",  # 세로형 (인스타그램/틱톡용)
                    resolution="720p",
                    person_generation="allow_adult"
                )
            )
            
            print(f"🚀 Video generation started: {operation.name}")
            
            # Step 5: 작업 완료 대기 (공식 폴링 방식)
            print("⏳ Polling operation status...")
            while not operation.done:
                print("⏳ Waiting for video generation to complete...")
                time.sleep(10)
                operation = self.client.operations.get(operation)
            
            print("✅ Video generation completed!")
            
            # Step 6: 다운로드 (공식 방식)
            print("💾 Downloading video...")
            generated_video = operation.response.generated_videos[0]
            
            # 공식 문서 방식: files.download + save
            self.client.files.download(file=generated_video.video)
            generated_video.video.save(output_path)
            
            print(f"🎉 Official video saved: {output_path}")
            
            # Step 7: 정리
            self.client.files.delete(uploaded_file.name)
            os.unlink(temp_path)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Official method failed: {e}")
            import traceback
            traceback.print_exc()
            
            # 폴백: 텍스트 기반
            print("🔄 Falling back to text-only generation...")
            try:
                fallback_prompt = f"""
                Create a cinematic travel marketing video inspired by this scene: {image_url}
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Official Gemini Video Generator")
    parser.add_argument("image_url", type=str, help="Image URL")
    parser.add_argument("--out", type=str, default="official_travel_video.mp4")
    
    args = parser.parse_args()
    
    try:
        generator = GeminiOfficialVideoGenerator()
        result = generator.generate_video_from_image_url(args.image_url, args.out)
        if result:
            print(f"🎉 SUCCESS: {result}")
        else:
            print("❌ FAILED")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
