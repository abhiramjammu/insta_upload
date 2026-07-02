import os
import shutil
from datetime import datetime
from dotenv import load_dotenv
from database import SessionLocal, Video, VideoStatus, init_db
from instagrapi import Client

load_dotenv()

PREMIERE_FOLDER = os.getenv("PREMIERE_FOLDER", "D:/adobe premiere pro 2025")
ARCHIVE_FOLDER = os.getenv("ARCHIVE_FOLDER", "D:/adobe upload after three days")

# Ensure folders exist
os.makedirs(PREMIERE_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

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

        # Check if any video is ready before logging in
        ready_videos = [v for v in videos if (datetime.now() - v.exported_at).total_seconds() / (3600 * 24) >= 3]
        if not ready_videos:
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

        for video in ready_videos:
            print(f"Uploading {video.filename} as a Reel...")
            try:
                cl.clip_upload(
                    video.current_path,
                    video.caption if video.caption else "Auto-uploaded via InstaFlow"
                )
                video.status = VideoStatus.UPLOADED
                video.uploaded_at = datetime.now()
                session.commit()
                print(f"Successfully uploaded {video.filename}.")
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
