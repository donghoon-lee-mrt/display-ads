import os
import time
import requests
from google import genai
from google.genai import types


def generate_video_from_image_simple(image_url: str, prompt: str, output_path: str = "veo_output.mp4") -> str:
    """Simple Gemini Veo 3 video generation from image URL"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable required")
    
    client = genai.Client(api_key=api_key)
    
    print(f"🖼️ Processing image: {image_url}")
    print(f"📝 Prompt: {prompt}")
    
    # Download image
    r = requests.get(image_url, timeout=30)
    r.raise_for_status()
    
    temp_path = "temp_image.jpg"
    with open(temp_path, "wb") as f:
        f.write(r.content)
    
    try:
        # Upload image - trying different approaches
        print("📤 Uploading image...")
        
        # Method 1: Direct file upload
        try:
            uploaded_file = client.files.upload(temp_path)
            print(f"✅ Image uploaded: {uploaded_file.name}")
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
            # Method 2: With file object
            try:
                with open(temp_path, "rb") as f:
                    uploaded_file = client.files.upload(f)
                print(f"✅ Image uploaded: {uploaded_file.name}")
            except Exception as e2:
                print(f"Method 2 failed: {e2}")
                # Method 3: Text-only generation (fallback)
                print("🔄 Falling back to text-only generation...")
                operation = client.models.generate_videos(
                    model="veo-3.0-generate-001",
                    prompt=f"Based on a travel image showing people: {prompt}",
                )
                
                print(f"⏳ Operation started: {operation.name}")
                
                # Poll until completion
                while not operation.done:
                    print("⏳ Waiting for video generation to complete...")
                    time.sleep(10)
                    operation = client.operations.get(operation)
                
                print("✅ Video generation completed!")
                
                # Download video
                generated_video = operation.response.generated_videos[0]
                client.files.download(file=generated_video.video)
                generated_video.video.save(output_path)
                
                print(f"💾 Video saved to: {output_path}")
                return output_path
        
        # If upload succeeded, generate with image
        operation = client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=prompt,
            image=uploaded_file,
        )
        
        print(f"⏳ Operation started: {operation.name}")
        
        # Poll until completion
        while not operation.done:
            print("⏳ Waiting for video generation to complete...")
            time.sleep(10)
            operation = client.operations.get(operation)
        
        print("✅ Video generation completed!")
        
        # Download video
        generated_video = operation.response.generated_videos[0]
        client.files.download(file=generated_video.video)
        generated_video.video.save(output_path)
        
        print(f"💾 Video saved to: {output_path}")
        return output_path
        
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate video using Gemini Veo 3 (simple)")
    parser.add_argument("image_url", type=str, help="Image URL")
    parser.add_argument("--prompt", type=str, default="A person in the image moving naturally with subtle breathing and gentle movements")
    parser.add_argument("--out", type=str, default="veo_simple_output.mp4")
    
    args = parser.parse_args()
    
    try:
        result = generate_video_from_image_simple(args.image_url, args.prompt, args.out)
        print(f"🎉 Success! Video: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()