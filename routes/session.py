# routes/session.py
from fastapi import APIRouter, HTTPException, Depends, status, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime 

from db.database import get_db
from services.ai_service import AIService
from models.user import UserProfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sessions",
    tags=["Session Management"],
)

class SessionEndRequest(BaseModel):
    user_id: str

class SessionEndResponse(BaseModel):
    message: str
    user_id: str
    session_id: str
    summary_updated: bool # Renamed from summary_updated for clarity

# Pydantic models moved from log.py
class SessionCreate(BaseModel):
    user_id: str

class SessionResponse(BaseModel):
    session_id: str
    timestamp: datetime
    first_message: Optional[str] = None

    class Config:
        from_attributes = True # Ensure compatibility if needed

class MessageCreate(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None
    stream: bool = False

class MessageResponse(BaseModel):
    user_id: str
    session_id: str
    response_text: str
    response_id: str

@router.post("/create", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreate, db: Session = Depends(get_db)):
    """
    Create a new conversation session for a user.
    """
    print(request)
    try:
        logger.info(f"Creating new session for user_id: {request.user_id}")
        
        ai_service = AIService.get_instance(db, request.user_id)
        session_id = ai_service.create_session(request.user_id)
        
        return SessionResponse(
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )

@router.post("/message", response_model=MessageResponse)
async def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    """
    Create a new message in a session and get AI response.
    If session_id is not provided, the most recent active session will be used.
    If stream=True, returns a StreamingResponse instead of a MessageResponse.
    """
    try:
        logger.info(f"Processing message for user_id: {message.user_id}, session_id: {message.session_id or 'Default'}, stream: {message.stream}")
        ai_service = AIService.get_instance(db, message.user_id)

        # Handle streaming response if requested
        if message.stream:
            from fastapi.responses import StreamingResponse
            
            # Let generate_response handle getting/creating the session_id with streaming enabled
            response_generator, response_id = ai_service.generate_response(
                message.user_id,
                message.message,
                message.session_id,  # Pass None if not provided, generate_response handles it
                stream=True
            )
            
            # Return a streaming response
            return StreamingResponse(
                response_generator,
                media_type="application/json"  # Changed to application/json since we're sending JSON objects
            )
        else:
            # Standard non-streaming response
            response_text, response_id = ai_service.generate_response(
                message.user_id,
                message.message,
                message.session_id  # Pass None if not provided, generate_response handles it
            )
            
            final_session_id = message.session_id or ai_service.get_active_session(message.user_id) or "newly_created" # Heuristic

            return MessageResponse(
                user_id=message.user_id,
                session_id=final_session_id, # Best guess or value returned from generate_response if modified
                response_text=response_text,
                response_id=response_id
            )
    except ValueError as e: # Catch specific errors if needed
        logger.error(f"Validation error processing message for {message.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing message for {message.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get("/list/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(user_id: str, limit: int = 5, db: Session = Depends(get_db)):
    """
    Get a list of sessions for a user.
    """
    logger.info(f"Retrieving sessions for user_id: {user_id}")
    
    # Get or create an AIService instance for this user
    ai_service = AIService.get_instance(db, user_id)
    
    # Get sessions for this user
    sessions = ai_service.get_user_sessions(user_id, limit)
    
    return sessions

@router.get("/history/{user_id}/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_history(user_id: str, session_id: str, db: Session = Depends(get_db)):
    """
    Get the complete conversation history for a specific session.
    """
    logger.info(f"Retrieving conversation history for user_id: {user_id}, session_id: {session_id}")
    
    # Get or create an AIService instance for this user
    ai_service = AIService.get_instance(db, user_id)
    
    # Get conversation history
    history = ai_service.get_session_history(user_id, session_id)
    
    return history

@router.post("/{session_id}/end", response_model=SessionEndResponse, status_code=status.HTTP_200_OK)
async def end_session_and_summarize(
    request: SessionEndRequest,
    session_id: str = Path(..., description="The ID of the session to end"),
    db: Session = Depends(get_db)
):
    """
    End session: save messages, clear memory, trigger LLM-based update
    of the cumulative summary in the user profile, increment session count.
    """
    user_id = request.user_id
    logger.info(f"Request to end session {session_id} for user {user_id} (LLM summary update)")

    summary_update_successful = False
    final_message = "Session end processed."

    try:
        ai_service = AIService.get_instance(db, user_id)

        # 1. End the session in memory (save remaining messages, clear memory)
        session_was_active = ai_service.end_session(user_id, session_id)
        # (Logging inside end_session handles active/inactive status)
        final_message = "Session ended, messages saved." if session_was_active else "Session not active (already ended/invalid)."


        # 2. Trigger LLM-based summary update
        # summarize_session now returns True/False
        summary_update_successful = ai_service.summarize_session(user_id, session_id)

        if summary_update_successful:
            logger.info(f"LLM successfully updated cumulative summary for {user_id} after session {session_id}.")
            final_message += " Cumulative summary updated by AI."
        else:
            logger.warning(f"LLM-based summary update failed for session {session_id}. Profile summary may be unchanged or incomplete.")
            final_message += " Summary update via AI failed."

        # 3. Increment total_sessions count (only if summary update was successful? Or always after ending?)
        # Let's increment regardless of summary success, as the session *did* end.
        user_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if user_profile:
            user_profile.total_sessions = (user_profile.total_sessions or 0) + 1
            try:
                db.commit()
                logger.info(f"Incremented total_sessions for {user_id} to {user_profile.total_sessions}")
                final_message += " Session count incremented."
            except Exception as commit_error:
                logger.error(f"DB error committing total_sessions for {user_id}: {commit_error}", exc_info=True)
                db.rollback()
                final_message += " Failed to increment session count (DB error)."
        else:
            logger.error(f"UserProfile {user_id} not found for incrementing total_sessions.")
            final_message += " User profile not found to increment session count."


        return SessionEndResponse(
            message=final_message,
            user_id=user_id,
            session_id=session_id,
            summary_updated=summary_update_successful # Reflects success of LLM update + DB save
        )

    except Exception as e:
        logger.error(f"Unhandled error during end_session_and_summarize (LLM) for {session_id}, user {user_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process end of session {session_id}: {str(e)}"
        )