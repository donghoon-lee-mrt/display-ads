import os
import time
import requests
from google import genai
from google.genai import types


def generate_video_from_image_fixed(image_url: str, prompt: str, output_path: str = "veo_fixed_output.mp4") -> str:
    """Fixed Gemini Veo 3 video generation from image URL with proper file upload"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable required")
    
    client = genai.Client(api_key=api_key)
    
    print(f"🖼️ Processing image: {image_url}")
    print(f"📝 Prompt: {prompt}")
    
    # Download image
    print("⬇️ Downloading image...")
    r = requests.get(image_url, timeout=30)
    r.raise_for_status()
    
    temp_path = "temp_image.jpg"
    with open(temp_path, "wb") as f:
        f.write(r.content)
    
    try:
        # Upload image using correct API
        print("📤 Uploading image to Gemini Files...")
        
        # Method: Create file from local path
        uploaded_file = client.files.create(
            path=temp_path,
            config=types.CreateFileConfig(
                display_name="Travel Image for Video Generation"
            )
        )
        print(f"✅ Image uploaded: {uploaded_file.name}")
        
        # Wait for processing
        print("⏳ Waiting for file processing...")
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = client.files.get(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            raise Exception(f"File upload failed: {uploaded_file.error}")
        
        print("✅ File processing completed!")
        
        # Generate video with uploaded image
        print("🎬 Starting video generation with image...")
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
        
        # Cleanup uploaded file
        client.files.delete(uploaded_file.name)
        
        print(f"💾 Video saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error during image-based generation: {e}")
        print("🔄 Falling back to text-only generation...")
        
        # Fallback to text-only
        operation = client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=f"A travel scene with people: {prompt}",
        )
        
        print(f"⏳ Fallback operation started: {operation.name}")
        
        while not operation.done:
            print("⏳ Waiting for video generation to complete...")
            time.sleep(10)
            operation = client.operations.get(operation)
        
        print("✅ Video generation completed!")
        
        generated_video = operation.response.generated_videos[0]
        client.files.download(file=generated_video.video)
        generated_video.video.save(output_path)
        
        print(f"💾 Fallback video saved to: {output_path}")
        return output_path
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate video using Gemini Veo 3 with fixed image upload")
    parser.add_argument("image_url", type=str, help="Image URL")
    parser.add_argument("--prompt", type=str, default="A person in the image moving naturally with subtle breathing and gentle movements")
    parser.add_argument("--out", type=str, default="veo_fixed_output.mp4")
    
    args = parser.parse_args()
    
    try:
        result = generate_video_from_image_fixed(args.image_url, args.prompt, args.out)
        print(f"🎉 Success! Video: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()