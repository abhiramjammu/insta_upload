from flask import Flask, render_template, request, jsonify, send_file
import os
from database import SessionLocal, Video, VideoStatus, init_db
from scheduler import run_all_jobs
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

# Initialize DB on start
init_db()

# Start background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=run_all_jobs, trigger="interval", minutes=1)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/videos')
def get_videos():
    session = SessionLocal()
    try:
        videos = session.query(Video).filter(Video.status != VideoStatus.DELETED).all()
        video_list = []
        for v in videos:
            video_list.append({
                "id": v.id,
                "filename": v.filename,
                "status": v.status.value,
                "exported_at": v.exported_at.isoformat() if v.exported_at else None,
                "staged_at": v.staged_at.isoformat() if v.staged_at else None,
                "uploaded_at": v.uploaded_at.isoformat() if v.uploaded_at else None
            })
        return jsonify(video_list)
    finally:
        session.close()

@app.route('/api/video/<int:video_id>/post_now', methods=['POST'])
def post_now(video_id):
    session = SessionLocal()
    try:
        video = session.query(Video).get(video_id)
        if video and video.status in [VideoStatus.PENDING_STAGING, VideoStatus.STAGING]:
            print(f"Manual override: Uploading {video.filename} NOW!")
            video.status = VideoStatus.UPLOADED
            video.uploaded_at = datetime.now()
            session.commit()
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Video not found or already uploaded"})
    finally:
        session.close()

@app.route('/api/video/<int:video_id>/delete', methods=['POST'])
def delete_video(video_id):
    session = SessionLocal()
    try:
        video = session.query(Video).get(video_id)
        if video:
            if os.path.exists(video.current_path):
                os.remove(video.current_path)
            video.status = VideoStatus.DELETED
            video.deleted_at = datetime.now()
            session.commit()
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Video not found"})
    finally:
        session.close()

@app.route('/stream/<int:video_id>')
def stream_video(video_id):
    session = SessionLocal()
    try:
        video = session.query(Video).get(video_id)
        if video and os.path.exists(video.current_path):
            return send_file(video.current_path, mimetype='video/mp4')
        return "Not found", 404
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
