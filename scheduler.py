import os
import shutil
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import SessionLocal, Video, VideoStatus, init_db

load_dotenv()

PREMIERE_FOLDER = os.getenv("PREMIERE_FOLDER", "D:\\adobe premiere pro 2025")
ARCHIVE_FOLDER = os.getenv("ARCHIVE_FOLDER", "D:\\adobe upload after three days")

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
            # Get file creation/modification time
            stat = os.stat(filepath)
            file_time = datetime.fromtimestamp(stat.st_mtime)
            
            # Check if exists in DB
            video = session.query(Video).filter_by(filename=filename).first()
            if not video:
                # Add to DB
                video = Video(
                    filename=filename,
                    original_path=filepath,
                    current_path=filepath,
                    exported_at=file_time,
                    status=VideoStatus.PENDING_STAGING
                )
                session.add(video)
                session.commit()
            
            # Check if > 12 hours old to move to staging
            if video.status == VideoStatus.PENDING_STAGING:
                age_hours = (datetime.now() - video.exported_at).total_seconds() / 3600
                if age_hours >= 12:
                    # Move to staging
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
    """Checks staging folder for videos older than 3 days and uploads them"""
    session = SessionLocal()
    try:
        videos = session.query(Video).filter_by(status=VideoStatus.STAGING).all()
        for video in videos:
            age_days = (datetime.now() - video.exported_at).total_seconds() / (3600 * 24)
            if age_days >= 3:
                print(f"Uploading {video.filename} to Instagram...")
                # TODO: Call actual Instagram Graph API here
                
                # Mock success:
                video.status = VideoStatus.UPLOADED
                video.uploaded_at = datetime.now()
                session.commit()
                print(f"Successfully uploaded {video.filename}.")
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
