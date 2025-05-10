# routes/user.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from db.database import get_db
from models.user import UserProfile
import logging
import uuid # Add uuid for generating user_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserProfileCreate(BaseModel):
    # user_id: str # Removed, will be auto-generated
    username: str
    student_class: str
    student_board: str
    student_goals: str | None = None
    student_strengths: str | None = None
    student_weaknesses: str | None = None
    student_learning_style: str | None = None

class UserProfileResponse(BaseModel):
    user_id: str
    username: str | None = None
    student_class: str | None = None
    student_board: str | None = None
    student_goals: str | None = None
    student_strengths: str | None = None
    student_weaknesses: str | None = None
    student_learning_style: str | None = None
    total_sessions: int
    cumulative_summary: str | None = None
    # summary: str = "" # Removed summary

    class Config:
        from_attributes = True

router = APIRouter(
    prefix="/users",
    tags=["User Management"],
)

@router.post("/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_user_profile(profile: UserProfileCreate, db: Session = Depends(get_db)):
    """
    Create a new user profile.
    """
    # Generate a unique user_id
    user_id = str(uuid.uuid4())
    logger.info(f"Creating new user profile for user_id: {user_id}")

    # Check if user already exists (unlikely with UUID, but good practice)
    existing_user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if existing_user:
        logger.error(f"Generated duplicate user_id {user_id}, this should not happen.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate a unique user ID."
        )

    # Create new user profile with all fields
    new_profile = UserProfile(
        user_id=user_id,
        username=profile.username,
        student_class=profile.student_class,
        student_board=profile.student_board,
        student_goals=profile.student_goals,
        student_strengths=profile.student_strengths,
        student_weaknesses=profile.student_weaknesses,
        student_learning_style=profile.student_learning_style
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    
    return new_profile

@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """
    Get a user profile by user_id.
    """
    logger.info(f"Retrieving user profile for user_id: {user_id}")
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        logger.warning(f"User with user_id {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id {user_id} not found"
        )
    
    return profile

@router.put("/{user_id}", response_model=UserProfileResponse)
async def update_user_profile(user_id: str, profile: UserProfileCreate, db: Session = Depends(get_db)):
    """
    Update a user profile.
    """
    logger.info(f"Updating user profile for user_id: {user_id}")
    
    db_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not db_profile:
        logger.warning(f"User with user_id {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id {user_id} not found"
        )
    
    # Update fields
    db_profile.username = profile.username # Mandatory field
    db_profile.student_class = profile.student_class # Mandatory field
    db_profile.student_board = profile.student_board # Mandatory field
    db_profile.student_goals = profile.student_goals
    db_profile.student_strengths = profile.student_strengths
    db_profile.student_weaknesses = profile.student_weaknesses
    db_profile.student_learning_style = profile.student_learning_style

    db.commit()
    db.refresh(db_profile)
    
    return db_profile