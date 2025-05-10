# models/tutor.py
from pydantic import BaseModel, Field
from typing import Optional, List

class TutorTextRequest(BaseModel):
    """Request model for text-based interaction with the AI tutor."""
    user_id: str = Field(..., description="Unique identifier for the user")
    text: str = Field(..., description="Text input from the user")

class TutorResponse(BaseModel):
    """Response model for the AI tutor's reply."""
    user_id: str = Field(..., description="Unique identifier for the user")
    response_text: str = Field(..., description="Text response from the AI tutor")
    audio_url: Optional[str] = Field(None, description="URL to the generated audio response, if available")
    response_id: str = Field(..., description="Unique identifier for this response")

class SessionSummaryRequest(BaseModel):
    """Request model for generating a session summary."""
    user_id: str = Field(..., description="Unique identifier for the user")
    session_id: str = Field(..., description="Unique identifier for the session to summarize")

class SessionSummaryResponse(BaseModel):
    """Response model for a session summary."""
    user_id: str = Field(..., description="Unique identifier for the user")
    session_id: str = Field(..., description="Unique identifier for the summarized session")
    summary_text: str = Field(..., description="Generated summary of the session")
    success: bool = Field(..., description="Whether the summary generation was successful")
