import os
import glob
from instagrapi import Client
from datetime import datetime
import pytz

CLOUD_QUEUE_DIR = "cloud_queue"
SESSION_FILE = "session.json"
LAST_UPLOAD_FILE = "last_upload.txt"

def get_ist_now():
    IST = pytz.timezone('Asia/Kolkata')
    return datetime.now(pytz.utc).astimezone(IST)

def can_upload_now():
    """Checks if we are allowed to upload based on time and gaps."""
    now_ist = get_ist_now()
    
    # 1. Night Blackout (12:00 AM to 6:00 AM)
    if 0 <= now_ist.hour < 6:
        print(f"[{now_ist.strftime('%H:%M')}] Night blackout active. Skipping uploads.")
        return False
        
    # 2. Minimum Gap (12 hours)
    if os.path.exists(LAST_UPLOAD_FILE):
        with open(LAST_UPLOAD_FILE, "r") as f:
            last_time_str = f.read().strip()
            if last_time_str:
                try:
                    last_upload = datetime.fromisoformat(last_time_str)
                    hours_since = (now_ist - last_upload).total_seconds() / 3600
                    if hours_since < 12:
                        print(f"[{now_ist.strftime('%H:%M')}] Minimum gap not met ({hours_since:.1f}h < 12h). Skipping uploads.")
                        return False
                except Exception as e:
                    print(f"Failed to parse last_upload.txt: {e}")
                    
    return True

def upload_from_queue():
    if not os.path.exists(CLOUD_QUEUE_DIR):
        print(f"No {CLOUD_QUEUE_DIR} directory found.")
        return
        
    mp4_files = glob.glob(os.path.join(CLOUD_QUEUE_DIR, "*.mp4"))
    if not mp4_files:
        print("Queue is empty. Nothing to upload.")
        return
        
    if not can_upload_now():
        return
        
    # Pick the first video in the queue
    video_path = mp4_files[0]
    base_name = os.path.splitext(video_path)[0]
    caption_path = base_name + ".txt"
    
    caption = "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"
    if os.path.exists(caption_path):
        with open(caption_path, "r", encoding="utf-8") as f:
            caption = f.read().strip()
            
    if not os.path.exists(SESSION_FILE):
        print(f"CRITICAL ERROR: {SESSION_FILE} not found! Cannot log in without it.")
        return
        
    print(f"Logging in to Instagram using {SESSION_FILE}...")
    cl = Client()
    try:
        cl.load_settings(SESSION_FILE)
        # Verify login if necessary
        # cl.login(username, password) # Not needed if session is fully valid
        
        # A quick check to see if we are logged in successfully
        cl.get_timeline_feed()
        print("Login verified!")
    except Exception as e:
        print(f"Failed to authenticate using session file: {e}")
        return
        
    print(f"Uploading {os.path.basename(video_path)} to Instagram...")
    try:
        cl.clip_upload(video_path, caption)
        print("Upload successful!")
        
        # Mark the time
        with open(LAST_UPLOAD_FILE, "w") as f:
            f.write(get_ist_now().isoformat())
            
        # Delete from disk so GitHub Actions can git rm it
        os.remove(video_path)
        if os.path.exists(caption_path):
            os.remove(caption_path)
            
        print("Video removed from queue. The GitHub Action will now commit this deletion.")
        
    except Exception as e:
        print(f"Failed to upload video: {e}")

if __name__ == "__main__":
    upload_from_queue()
