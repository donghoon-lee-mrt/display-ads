import os
import time
import requests
import tempfile
from google import genai
from google.genai import types


def test_image_video_generation():
    """최종 테스트: 실제 이미지로 영상 생성"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # 미얀마 사원 이미지
    image_url = "https://dry7pvlp22cox.cloudfront.net/mrt-images-prod/2024/09/26/Pyat/stQgJttsVT.jpg"
    
    print("🎬 Final Test: Image-based Video Generation")
    print(f"📸 Image: {image_url}")
    
    try:
        # 1. 이미지 다운로드
        print("⬇️ Downloading image...")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # 2. 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name
        
        print(f"💾 Image saved: {temp_path}")
        
        # 3. 파일 업로드 (여러 방법 시도)
        print("📤 Uploading to Gemini...")
        
        uploaded_file = None
        upload_methods = [
            # 방법 1: 단순 경로
            lambda: client.files.upload(temp_path),
            # 방법 2: file 파라미터
            lambda: client.files.upload(file=temp_path),
            # 방법 3: path 파라미터
            lambda: client.files.upload(path=temp_path),
        ]
        
        for i, method in enumerate(upload_methods, 1):
            try:
                print(f"🔄 Trying upload method {i}...")
                uploaded_file = method()
                print(f"✅ Upload successful with method {i}: {uploaded_file.name}")
                break
            except Exception as e:
                print(f"❌ Method {i} failed: {e}")
                continue
        
        if not uploaded_file:
            raise Exception("All upload methods failed")
        
        # 4. 파일 처리 대기
        print("⏳ Waiting for file processing...")
        max_wait = 60
        wait_time = 0
        
        while uploaded_file.state.name == "PROCESSING" and wait_time < max_wait:
            time.sleep(2)
            wait_time += 2
            uploaded_file = client.files.get(uploaded_file.name)
            print(f"⏳ Processing... ({wait_time}s)")
        
        if uploaded_file.state.name == "FAILED":
            raise Exception(f"File processing failed: {uploaded_file.error}")
        
        print(f"✅ File ready: {uploaded_file.state.name}")
        
        # 5. 영상 생성 (여러 방법 시도)
        print("🎬 Generating video...")
        
        prompt = """
        Transform this Myanmar temple scene into a cinematic travel video.
        
        Add subtle, natural movement:
        - Gentle wind effects on trees and leaves
        - Soft lighting changes as if clouds are passing
        - Peaceful, meditative atmosphere
        - The person should have subtle breathing and slight head movement
        
        Create a compelling 8-second travel marketing video that inspires wanderlust.
        High quality, cinematic, professional.
        """
        
        video_methods = [
            # 방법 1: image 파라미터
            lambda: client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=prompt,
                image=uploaded_file,
            ),
            # 방법 2: 다른 파라미터명 시도
            lambda: client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=prompt,
                input_image=uploaded_file,
            ),
        ]
        
        operation = None
        for i, method in enumerate(video_methods, 1):
            try:
                print(f"🔄 Trying video generation method {i}...")
                operation = method()
                print(f"✅ Video generation started with method {i}: {operation.name}")
                break
            except Exception as e:
                print(f"❌ Method {i} failed: {e}")
                continue
        
        if not operation:
            raise Exception("All video generation methods failed")
        
        # 6. 생성 완료 대기
        print("⏳ Creating video...")
        max_generation_time = 300  # 5분
        wait_time = 0
        
        while not operation.done and wait_time < max_generation_time:
            print(f"⏳ Generating Myanmar temple video... ({wait_time}s)")
            time.sleep(15)
            wait_time += 15
            operation = client.operations.get(operation)
        
        if not operation.done:
            raise Exception("Video generation timeout")
        
        print("✅ Video generation completed!")
        
        # 7. 다운로드
        generated_video = operation.response.generated_videos[0]
        output_path = "myanmar_temple_final.mp4"
        
        print("💾 Downloading video...")
        
        # 다운로드 방법들 시도
        download_methods = [
            # 방법 1: video_bytes 속성
            lambda: generated_video.video.video_bytes,
            # 방법 2: files.download
            lambda: client.files.download(generated_video.video),
            # 방법 3: 직접 접근
            lambda: generated_video.video.data if hasattr(generated_video.video, 'data') else None,
        ]
        
        video_data = None
        for i, method in enumerate(download_methods, 1):
            try:
                print(f"🔄 Trying download method {i}...")
                video_data = method()
                if video_data:
                    print(f"✅ Download successful with method {i}")
                    break
                else:
                    print(f"⚠️ Method {i} returned None")
            except Exception as e:
                print(f"❌ Method {i} failed: {e}")
                continue
        
        if video_data:
            with open(output_path, 'wb') as f:
                f.write(video_data)
            print(f"🎉 SUCCESS! Video saved: {output_path}")
        else:
            print("❌ All download methods failed")
        
        # 8. 정리
        client.files.delete(uploaded_file.name)
        os.unlink(temp_path)
        
        return output_path if video_data else None
        
    except Exception as e:
        print(f"❌ Final test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_image_video_generation()
    if result:
        print(f"🎉 FINAL SUCCESS: {result}")
    else:
        print("❌ FINAL FAILURE")
