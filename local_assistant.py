import os
import time
from datetime import datetime
from dotenv import load_dotenv

from video_processor import process_video_ffmpeg
from ai_captioner import generate_blog_caption

load_dotenv()

PREMIERE_FOLDER = os.getenv("PREMIERE_FOLDER", "D:/adobe premiere pro 2025")
OUTPUT_FOLDER = os.getenv("ARCHIVE_FOLDER", "D:/adobe upload after three days")

# Ensure folders exist
os.makedirs(PREMIERE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def process_old_videos():
    """Scans for videos older than 3 days, processes them, and moves them to the output folder."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning Premiere folder for videos older than 3 days...")
    
    if not os.path.exists(PREMIERE_FOLDER):
        return

    for filename in os.listdir(PREMIERE_FOLDER):
        if not filename.lower().endswith(('.mp4', '.mov')):
            continue
            
        filepath = os.path.join(PREMIERE_FOLDER, filename)
        
        try:
            stat = os.stat(filepath)
            file_time = datetime.fromtimestamp(stat.st_mtime)
            
            # Check if older than 3 days (3 * 24 * 3600 seconds)
            age_seconds = (datetime.now() - file_time).total_seconds()
            if age_seconds < (3 * 24 * 3600):
                continue
                
            print(f"\nFound video older than 3 days: {filename}")
            
            # Output paths
            base_name = os.path.splitext(filename)[0]
            output_mp4 = os.path.join(OUTPUT_FOLDER, f"{base_name}.mp4")
            output_txt = os.path.join(OUTPUT_FOLDER, f"{base_name}.txt")
            
            # 1. Edit the video (Applies 75% scale, moving bg, rounded corners, trimming, '3ditz' watermark)
            print("Applying edits (this may take a minute)...")
            try:
                process_video_ffmpeg(filepath, output_mp4)
            except Exception as e:
                print(f"FFmpeg processing failed for {filename}: {e}")
                continue
                
            # 2. Generate the caption
            print("Generating AI caption...")
            try:
                caption = generate_blog_caption(output_mp4)
            except Exception as e:
                print(f"Caption generation failed: {e}")
                caption = "Automated Edit #insta #reels #video #edit #viral"
                
            # 3. Save caption to a text file with the same name
            with open(output_txt, "w", encoding="utf-8") as f:
                f.write(caption)
                
            # 4. Cleanup: Delete the original video so we don't process it again
            print("Cleaning up original file...")
            os.remove(filepath)
            
            print(f"SUCCESS: {filename} is ready in {OUTPUT_FOLDER}")
            
        except Exception as e:
            print(f"Error handling {filename}: {e}")

if __name__ == "__main__":
    process_old_videos()
