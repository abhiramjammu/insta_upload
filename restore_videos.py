import os
import shutil
from database import SessionLocal, Video, VideoStatus

PREMIERE_FOLDER = "D:/adobe premiere pro 2025"
ARCHIVE_FOLDER = "D:/adobe upload after three days"

def restore_videos():
    session = SessionLocal()
    try:
        # Get all videos currently in STAGING
        videos = session.query(Video).filter(Video.status == VideoStatus.STAGING).all()
        count = 0
        
        for video in videos:
            if video.current_path and os.path.exists(video.current_path):
                # Target path in premiere folder
                new_path = os.path.join(PREMIERE_FOLDER, video.filename)
                
                print(f"Moving {video.filename} back to Premiere Pro folder...")
                try:
                    # Move the file back
                    shutil.move(video.current_path, new_path)
                    
                    # Update database
                    video.current_path = new_path
                    video.status = VideoStatus.PENDING_STAGING
                    count += 1
                except Exception as e:
                    print(f"Failed to move {video.filename}: {e}")
                    
        session.commit()
        print(f"\nSuccessfully moved {count} videos back to {PREMIERE_FOLDER}!")
        
    finally:
        session.close()

if __name__ == "__main__":
    restore_videos()
