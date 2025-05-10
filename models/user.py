from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime
from db.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True) # Keep username as student_name
    student_class = Column(String, nullable=True) # New: Class (e.g., "10")
    student_board = Column(String, nullable=True) # New: Board (e.g., "CBSE")
    student_goals = Column(Text, nullable=True) # New: Goals
    student_strengths = Column(Text, nullable=True) # New: Strengths
    student_weaknesses = Column(Text, nullable=True) # New: Weaknesses
    student_learning_style = Column(String, nullable=True) # New: Learning Style (e.g., "Visual", "Auditory")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total_sessions = Column(Integer, default=0)
    cumulative_summary = Column(Text, nullable=True) # Stores chronological session summaries

class SessionMessage(Base):
    __tablename__ = "session_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# New model to store individual session summaries
class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, unique=True, nullable=False) # Ensure one summary per session
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
