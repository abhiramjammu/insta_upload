import os
import shutil
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from database import SessionLocal, Video, VideoStatus, init_db
from instagrapi import Client
from sqlalchemy import func

from video_processor import process_video_ffmpeg
from ai_captioner import generate_blog_caption

load_dotenv()

PREMIERE_FOLDER = os.getenv("PREMIERE_FOLDER", "D:/adobe premiere pro 2025")
ARCHIVE_FOLDER = os.getenv("ARCHIVE_FOLDER", "D:/adobe upload after three days")

# Ensure folders exist
os.makedirs(PREMIERE_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    return datetime.now(pytz.utc).astimezone(IST)

def can_upload_now(session):
    """Checks if we are allowed to upload based on time, daily limits, and gaps."""
    now_ist = get_ist_now()
    
    # 1. Night Blackout (12:00 AM to 6:00 AM)
    if 0 <= now_ist.hour < 6:
        print(f"[{now_ist.strftime('%H:%M')}] Night blackout active. Skipping uploads.")
        return False
        
    # 2. Daily Limit (Max 2 per day)
    today_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).replace(tzinfo=None)
    uploads_today = session.query(func.count(Video.id)).filter(
        Video.status == VideoStatus.UPLOADED,
        Video.uploaded_at >= today_start
    ).scalar()
    
    if uploads_today >= 2:
        print(f"[{now_ist.strftime('%H:%M')}] Daily limit of 2 reached. Skipping uploads.")
        return False
        
    # 3. Minimum Gap (12 hours)
    last_upload = session.query(Video).filter(Video.status == VideoStatus.UPLOADED).order_by(Video.uploaded_at.desc()).first()
    if last_upload and last_upload.uploaded_at:
        hours_since = (datetime.now() - last_upload.uploaded_at).total_seconds() / 3600
        if hours_since < 12:
            print(f"[{now_ist.strftime('%H:%M')}] Minimum gap not met ({hours_since:.1f}h < 12h). Skipping uploads.")
            return False
            
    return True

def scan_premiere_folder():
    """Scans the premiere folder for new videos and adds them to DB, or moves them to staging if >12h"""
    session = SessionLocal()
    try:
        if not os.path.exists(PREMIERE_FOLDER):
            return

        for filename in os.listdir(PREMIERE_FOLDER):
            if not filename.lower().endswith(('.mp4', '.mov')):
                continue
                
            filepath = os.path.join(PREMIERE_FOLDER, filename)
            stat = os.stat(filepath)
            file_time = datetime.fromtimestamp(stat.st_mtime)
            
            # Only process videos created after June 1st, 2026
            if file_time < datetime(2026, 6, 1):
                continue
            
            video = session.query(Video).filter_by(filename=filename).first()
            if not video:
                video = Video(
                    filename=filename,
                    original_path=filepath,
                    current_path=filepath,
                    exported_at=file_time,
                    status=VideoStatus.PENDING_STAGING
                )
                session.add(video)
                session.commit()
            
            # Check if > 12 hours old
            if video.status == VideoStatus.PENDING_STAGING:
                age_hours = (datetime.now() - video.exported_at).total_seconds() / 3600
                if age_hours >= 12:
                    new_path = os.path.join(ARCHIVE_FOLDER, filename)
                    try:
                        shutil.move(filepath, new_path)
                        video.current_path = new_path
                        video.status = VideoStatus.STAGING
                        video.staged_at = datetime.now()
                        session.commit()
                        print(f"Moved {filename} to staging.")
                    except Exception as e:
                        print(f"Error moving {filename}: {e}")
    finally:
        session.close()

def process_uploads():
    """Checks staging folder for videos older than 3 days and uploads them via instagrapi"""
    session = SessionLocal()
    try:
        videos = session.query(Video).filter_by(status=VideoStatus.STAGING).all()
        if not videos:
            return

        # Check if any video is ready before checking limits
        ready_videos = [v for v in videos if (datetime.now() - v.exported_at).total_seconds() / (3600 * 24) >= 3]
        if not ready_videos:
            return

        # Enforce all timing constraints (IST Timezone, 12h Gap, Max 2/day, Night Blackout)
        if not can_upload_now(session):
            return

        username = os.getenv("IG_USERNAME")
        password = os.getenv("IG_PASSWORD")
        
        if not username or not password:
            print("Missing IG_USERNAME or IG_PASSWORD in .env. Skipping upload.")
            return

        print("Logging into Instagram...")
        cl = Client()
        try:
            cl.login(username, password)
        except Exception as e:
            print(f"Instagram Login Failed: {e}")
            return

        # Only process ONE video per run to respect the 12-hour gap rule on the next cycle
        video = ready_videos[0]
        
        print(f"Processing {video.filename} for upload...")
        
        # 1. Video Editing (Trimming, Padding, Rounded Edges)
        output_trimmed = os.path.join(ARCHIVE_FOLDER, f"trimmed_{video.filename}")
        try:
            process_video_ffmpeg(video.current_path, output_trimmed)
        except Exception as e:
            print(f"FFmpeg processing failed: {e}")
            return

        # 2. AI Captioning
        try:
            caption = generate_blog_caption(output_trimmed)
        except Exception as e:
            print(f"Caption generation failed: {e}")
            caption = "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"

        print(f"Uploading {video.filename} as a Reel...")
        try:
            cl.clip_upload(
                output_trimmed,
                caption
            )
            video.status = VideoStatus.UPLOADED
            video.uploaded_at = datetime.now()
            video.caption = caption
            session.commit()
            print(f"Successfully uploaded {video.filename}.")
            
            # Clean up the trimmed file
            if os.path.exists(output_trimmed):
                os.remove(output_trimmed)
                
        except Exception as e:
            print(f"Upload failed for {video.filename}: {e}")
            video.status = VideoStatus.FAILED
            session.commit()
    finally:
        session.close()

def process_deletions():
    """Checks uploaded videos older than 7 days and deletes them"""
    session = SessionLocal()
    try:
        videos = session.query(Video).filter_by(status=VideoStatus.UPLOADED).all()
        for video in videos:
            if video.uploaded_at:
                age_days = (datetime.now() - video.uploaded_at).total_seconds() / (3600 * 24)
                if age_days >= 7:
                    try:
                        if os.path.exists(video.current_path):
                            os.remove(video.current_path)
                        video.status = VideoStatus.DELETED
                        video.deleted_at = datetime.now()
                        session.commit()
                        print(f"Deleted {video.filename} from disk.")
                    except Exception as e:
                        print(f"Error deleting {video.filename}: {e}")
    finally:
        session.close()

def run_all_jobs():
    init_db()
    scan_premiere_folder()
    process_uploads()
    process_deletions()

if __name__ == "__main__":
    run_all_jobs()
