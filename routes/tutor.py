# routes/tutor.py
from fastapi import APIRouter, HTTPException, status, Depends
from models.tutor import TutorTextRequest, TutorResponse 
from services.ai_service import AIService
import logging
from sqlalchemy.orm import Session 
from db.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assistant", 
    tags=["Assistant Interaction"], 
)

@router.post("/chat", response_model=TutorResponse) 
async def interact_with_assistant_text(
    request: TutorTextRequest, 
    db: Session = Depends(get_db)
):
     """
     Handles text-based interaction with the AI assistant.
     Input: JSON body with user_id and text.
     Output: JSON body with response_text and response_id.
     """
     logger.info(f"Received chat request for user: {request.user_id}")

     try:
         # Get or create an AIService instance for this user
         ai_service = AIService.get_instance(db, request.user_id)
         # Generate response using the AI service
         assistant_response_text, response_id = ai_service.generate_response(request.user_id, request.text)
     except Exception as e:
         logger.error(f"Error generating assistant response: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate assistant response")


     logger.info(f"Sending text response for user: {request.user_id}")
     return TutorResponse(
         user_id=request.user_id,
         response_text=assistant_response_text,
         audio_url=None, 
         response_id=response_id
     )

