import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def generate_blog_caption(video_path):
    """
    Uploads the video to Google Gemini, analyzes it, and generates a blog-style caption.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: No GEMINI_API_KEY found. Falling back to default caption.")
        return "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"

    genai.configure(api_key=api_key)
    
    # Upload the video using the File API
    print(f"Uploading {video_path} to Gemini for analysis...")
    try:
        video_file = genai.upload_file(path=video_path)
    except Exception as e:
        print(f"Failed to upload to Gemini: {e}")
        return "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"

    # Wait for the video to be processed by Google's servers
    while video_file.state.name == "PROCESSING":
        print("Waiting for Gemini to process the video...")
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
        
    if video_file.state.name == "FAILED":
        print("Gemini failed to process the video.")
        return "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"

    print("Video processed. Generating caption...")
    
    prompt = (
        "You are an expert Instagram social media manager. Watch this video and write a caption for it. "
        "The caption must be formatted exactly like this:\n"
        "1. Write exactly 10 lines analyzing the content and subject matter of the video.\n"
        "2. Write exactly 10 lines analyzing the video editing style, techniques, and pacing used.\n"
        "3. End with exactly 5 relevant hashtags.\n"
        "Make it engaging and suitable for a professional Instagram Reel."
    )
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([video_file, prompt])
        caption = response.text.strip()
        
        # Cleanup file from Google's servers
        genai.delete_file(video_file.name)
        return caption
    except Exception as e:
        print(f"Failed to generate caption: {e}")
        return "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"

if __name__ == "__main__":
    # Test
    # print(generate_blog_caption("out.mp4"))
    pass
