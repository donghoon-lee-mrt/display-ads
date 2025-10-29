import os
import time
from dataclasses import dataclass
from typing import Optional
from google import genai
from google.genai import types


@dataclass
class VeoSpec:
    duration: int = 5
    resolution: str = "1080p"
    prompt: str = "A person in the image moving naturally with subtle breathing and head movements"


class GeminiVeoGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")
        
        self.client = genai.Client(api_key=self.api_key)

    def generate_from_prompt(self, prompt: str, output_path: str = "veo_output.mp4") -> str:
        """Generate video from text prompt using Veo 3"""
        print(f"🎬 Starting video generation...")
        print(f"📝 Prompt: {prompt}")
        
        # Start video generation
        operation = self.client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=prompt,
        )
        
        print(f"⏳ Operation started: {operation.name}")
        
        # Poll until completion
        while not operation.done:
            print("⏳ Waiting for video generation to complete...")
            time.sleep(10)
            operation = self.client.operations.get(operation)
        
        print("✅ Video generation completed!")
        
        # Download the generated video
        generated_video = operation.response.generated_videos[0]
        self.client.files.download(file=generated_video.video)
        generated_video.video.save(output_path)
        
        print(f"💾 Video saved to: {output_path}")
        return output_path

    def generate_from_image_url(self, image_url: str, prompt: str, output_path: str = "veo_output.mp4") -> str:
        """Generate video from image URL + text prompt"""
        # For image-to-video, we need to upload the image first
        print(f"🖼️ Processing image: {image_url}")
        
        # Download image
        import requests
        r = requests.get(image_url, timeout=30)
        r.raise_for_status()
        
        # Upload to Gemini
        temp_path = "temp_image.jpg"
        with open(temp_path, "wb") as f:
            f.write(r.content)
        
        # Upload image to Gemini Files API
        with open(temp_path, "rb") as f:
            uploaded_file = self.client.files.upload(file=f, mime_type="image/jpeg")
        print(f"📤 Image uploaded: {uploaded_file.name}")
        
        # Generate video with image + prompt
        operation = self.client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=prompt,
            image=uploaded_file,
        )
        
        print(f"⏳ Operation started: {operation.name}")
        
        # Poll until completion
        while not operation.done:
            print("⏳ Waiting for video generation to complete...")
            time.sleep(10)
            operation = self.client.operations.get(operation)
        
        print("✅ Video generation completed!")
        
        # Download the generated video
        generated_video = operation.response.generated_videos[0]
        self.client.files.download(file=generated_video.video)
        generated_video.video.save(output_path)
        
        # Cleanup
        os.remove(temp_path)
        
        print(f"💾 Video saved to: {output_path}")
        return output_path


def generate_video_from_image(image_url: str, prompt: str, output_path: str = "gemini_veo_output.mp4") -> str:
    """Convenience function"""
    generator = GeminiVeoGenerator()
    return generator.generate_from_image_url(image_url, prompt, output_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate video using Gemini Veo 3")
    parser.add_argument("--image", type=str, help="Image URL for image-to-video")
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt")
    parser.add_argument("--out", type=str, default="gemini_veo_output.mp4", help="Output path")
    
    args = parser.parse_args()
    
    generator = GeminiVeoGenerator()
    
    if args.image:
        result = generator.generate_from_image_url(args.image, args.prompt, args.out)
    else:
        result = generator.generate_from_prompt(args.prompt, args.out)
    
    print(f"🎉 Done! Video: {result}")