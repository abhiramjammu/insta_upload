import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

class VideoStatus(enum.Enum):
    PENDING_STAGING = "pending_staging"  # In Premiere folder (< 12 hours)
    STAGING = "staging"                  # In Staging folder (> 12 hours, waiting for 3 day mark)
    UPLOADED = "uploaded"                # Uploaded to Instagram, waiting to be deleted (> 7 days)
    DELETED = "deleted"                  # Permanently deleted
    FAILED = "failed"                    # Upload failed
    PAUSED = "paused"                    # Upload paused by user

class Video(Base):
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, nullable=False)
    original_path = Column(String, nullable=False)
    current_path = Column(String, nullable=False)
    
    exported_at = Column(DateTime, nullable=False, default=datetime.now) 
    staged_at = Column(DateTime, nullable=True) 
    uploaded_at = Column(DateTime, nullable=True) 
    deleted_at = Column(DateTime, nullable=True)
    
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING_STAGING)

# Database setup
DATABASE_URL = "sqlite:///instagram_bot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
