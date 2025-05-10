# db/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# Define the path to the database file within the db directory
DB_DIR = Path(__file__).parent
DATABASE_URL = f"sqlite:///{DB_DIR / 'edu_tutor.db'}"

# Ensure the db directory exists (though it should if this file is here)
os.makedirs(DB_DIR, exist_ok=True)

# Create the SQLAlchemy engine
# connect_args={'check_same_thread': False} is needed for SQLite to allow usage in multiple threads (like in FastAPI)
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create database tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Optional: Function to drop tables (for development/testing)
def drop_tables():
    Base.metadata.drop_all(bind=engine)