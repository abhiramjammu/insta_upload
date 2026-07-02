import os
import shutil
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from database import SessionLocal, Video, VideoStatus, init_db
from sqlalchemy import func
import time

from video_processor import process_video_ffmpeg
from ai_captioner import generate_blog_caption

load_dotenv()

PREMIERE_FOLDER = os.getenv("PREMIERE_FOLDER", "D:/adobe premiere pro 2025")
ARCHIVE_FOLDER = os.getenv("ARCHIVE_FOLDER", "D:/adobe upload after three days")
CLOUD_QUEUE_DIR = os.path.join(os.path.dirname(__file__), "cloud_queue")

# Ensure folders exist
os.makedirs(PREMIERE_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
os.makedirs(CLOUD_QUEUE_DIR, exist_ok=True)

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
                        shutil.copy2(filepath, new_path)
                        video.current_path = new_path
                        video.status = VideoStatus.STAGING
                        video.staged_at = datetime.now()
                        session.commit()
                        print(f"Moved {filename} to staging.")
                    except Exception as e:
                        print(f"Error moving {filename}: {e}")
    finally:
        session.close()

def push_to_cloud():
    """Checks staging folder for videos older than 3 days, edits them, and pushes them to cloud queue."""
    session = SessionLocal()
    try:
        videos = session.query(Video).filter_by(status=VideoStatus.STAGING).all()
        if not videos:
            return

        # Check if any video is ready (3 days old)
        ready_videos = [v for v in videos if (datetime.now() - v.exported_at).total_seconds() / (3600 * 24) >= 3]
        if not ready_videos:
            return

        # Only process ONE video per run to spread out load
        video = ready_videos[0]
        
        print(f"Processing {video.filename} for the Cloud Queue...")
        
        # Target paths in cloud queue
        base_name = str(video.id)
        queue_video_path = os.path.join(CLOUD_QUEUE_DIR, f"{base_name}.mp4")
        queue_text_path = os.path.join(CLOUD_QUEUE_DIR, f"{base_name}.txt")
        
        # 1. Video Editing (Trimming, Padding, Rounded Edges, Text Tracking)
        try:
            process_video_ffmpeg(video.current_path, queue_video_path)
        except Exception as e:
            print(f"FFmpeg processing failed: {e}")
            return

        # 2. AI Captioning
        try:
            caption = generate_blog_caption(queue_video_path)
        except Exception as e:
            print(f"Caption generation failed: {e}")
            caption = "Auto-uploaded via InstaFlow #insta #reels #video #edit #viral"
            
        with open(queue_text_path, "w", encoding="utf-8") as f:
            f.write(caption)

        print(f"Pushing {video.filename} to GitHub Cloud Queue...")
        try:
            subprocess.run(['git', 'add', 'cloud_queue/'], check=True, cwd=os.path.dirname(__file__))
            subprocess.run(['git', 'commit', '-m', f"Add video {base_name} to cloud queue"], check=True, cwd=os.path.dirname(__file__))
            subprocess.run(['git', 'push'], check=True, cwd=os.path.dirname(__file__))
            
            video.status = VideoStatus.UPLOADED  # 'UPLOADED' now means pushed to Cloud Queue
            video.uploaded_at = datetime.now()
            video.caption = caption
            session.commit()
            print(f"Successfully pushed {video.filename} to GitHub.")
            
            # Delete the original file from the Premiere Pro folder now that it's queued
            if video.original_path and os.path.exists(video.original_path):
                os.remove(video.original_path)
                print(f"Deleted original file from Premiere Pro: {video.original_path}")
                
        except subprocess.CalledProcessError as e:
            print(f"Git push failed: {e}. Reverting...")
            if os.path.exists(queue_video_path): os.remove(queue_video_path)
            if os.path.exists(queue_text_path): os.remove(queue_text_path)
            
    finally:
        session.close()

def process_deletions():
    """Checks videos pushed to cloud older than 7 days and deletes them from local disk"""
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
                        print(f"Deleted local archive of {video.filename} from disk.")
                    except Exception as e:
                        print(f"Error deleting {video.filename}: {e}")
    finally:
        session.close()

def run_all_jobs():
    init_db()
    scan_premiere_folder()
    push_to_cloud()
    process_deletions()

if __name__ == "__main__":
    run_all_jobs()
