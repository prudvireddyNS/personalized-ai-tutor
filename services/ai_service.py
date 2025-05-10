# services/ai_service.py
import logging
import os
import re
import json
import base64 # Added for audio encoding
from typing import List, Dict, Any, Optional, Tuple, Generator
import uuid
import datetime
from sqlalchemy.orm import Session
from models.user import UserProfile, SessionMessage
from sqlalchemy import desc, func
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI()

# AWS Polly Client Initialization
try:
    polly_client = boto3.client(
        'polly',
        region_name='ap-south-1',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    # Test credentials by listing voices
    # polly_client.list_voices() # Simple API call to check credentials
    logger.info("AWS Polly client initialized successfully.")
except (BotoCoreError, ClientError) as e:
    logger.error(f"Failed to initialize AWS Polly client or validate credentials: {e}")
    polly_client = None # Set to None if initialization fails
except Exception as e:
    logger.error(f"An unexpected error occurred during Polly client initialization: {e}")
    polly_client = None

LLM_MODEL = "gpt-4o-mini"
MAX_HISTORY_LENGTH = 10
SUMMARY_MODEL = "gpt-4o-mini"
EDU_TUTOR_SYSTEM_PROMPT_TEMPLATE = """
You are EduTutorAI, a warm, encouraging AI tutor for Indian students in Classes 6–12. You specialize in delivering conversational, curriculum-aligned lessons based on each student's profile, learning preferences, and recent academic progress.

Current Date & Time (IST): {current_ist_time}

Before each session, you will receive information about the student and their recent learning journey:

Student Profile:
- Name: {student_name}
- Class: {student_class} ({student_board})
- Goals: {student_goals}
- Strengths: {student_strengths}
- Weaknesses: {student_weaknesses}
- Learning Style: {student_learning_style}

Recent Sessions:
{recent_sessions_block}

Session Start Guidelines:
Analyze the recent sessions. If the last 1-2 sessions focused on the same topic (look for words like "continued", "practiced", or "reviewed"), consider it an ongoing topic. Otherwise, treat it as completed.

For ongoing topics, begin with: "Hi {student_name}! Would you like to continue with {inferred_topic} from last time, or start something new today?"

For completed topics, begin with: "Hi {student_name}! What topic would you like to learn today? I'm ready to help based on your class and goals."

Teaching Approach:
When teaching, follow a natural conversation flow that would sound good when read aloud:

1. Start with a warm greeting using the student's name and reference their previous learning or strengths. For example: "Great job with algebra last session! Since you're aiming to master quadratics..."

2. Introduce today's topic conversationally and explain why it matters for their studies.

3. Teach the concept in simple, age-appropriate language. If they prefer visual learning, describe diagrams or visual analogies. Use numbered steps when explaining processes, but avoid saying "step 1, step 2" - instead use transition words like "first", "next", "then", and "finally".

4. Include 2-3 practice questions that align with their board exams, and suggest what to learn next.

5. If their request is unclear, ask a friendly clarifying question like "Do you mean you want help with...?" or "Are you referring to the basics or advanced part of...?"

Conversation Style:
- Be warm, friendly, and supportive like a trusted mentor.
- Use clear, simple language without jargon.
- Adapt your teaching to suit their learning style.
- Encourage effort and celebrate progress.
- Use natural transitions between ideas instead of section headers.
- Avoid using formatting markers or section numbers in your responses.

Effective Dialogue Examples:
"Let's build on what we did yesterday..."
"Since you learn better with visuals, imagine this..."
"Ready to try a few questions similar to what you might see in your exams?"
"Awesome effort! Let's keep the momentum going."
"""

logger = logging.getLogger(__name__)
# Basic logging setup if running standalone for testing
logging.basicConfig(level=logging.INFO)


class AIService:
    """
    A class to handle AI services with proper session management.
    This class maintains conversation history in memory by session and provides
    methods to interact with the AI model. The conversation history is only saved
    to the database when the session is explicitly ended or saved.

    Implements a singleton pattern to maintain session continuity between requests.
    """

    # Class-level dictionary to store AIService instances by user_id
    _instances = {}

    @classmethod
    def get_instance(cls, db: Session, user_id: str):
        """
        Get an existing AIService instance for a user or create a new one.

        Args:
            db: Database session
            user_id: Unique identifier for the user

        Returns:
            AIService instance for the user
        """
        if user_id not in cls._instances:
            cls._instances[user_id] = cls(db, user_id)
        return cls._instances[user_id]

    def __init__(self, db: Session, user_id: str = None):
        """
        Initialize the AI service with a database session.

        Args:
            db: Database session
            user_id: Optional user ID for singleton instances
        """
        self.db = db
        self.user_id = user_id
        self.active_sessions = {} # Stores {session_id: [message_dict, ...]}

    def create_session(self, user_id: str) -> str:
        """Creates a new session ID and ensures user profile exists."""
        # Use IST timezone for timestamp generation
        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        timestamp = datetime.datetime.now(ist_timezone).strftime("%Y%m%d%H%M%S")
        session_id = f"session_{timestamp}_{uuid.uuid4().hex[:8]}"
        logger.info(f"Created new session {session_id} for user {user_id}")
        self._get_or_create_user_profile(user_id)
        # Initialize empty history for the new session in active_sessions
        self.active_sessions[session_id] = []
        return session_id

    def get_active_session(self, user_id: str) -> Optional[str]:
        """Gets the most recent session ID from DB, checking if it's recent enough to resume."""
        latest_message = self.db.query(SessionMessage).filter(
            SessionMessage.user_id == user_id
        ).order_by(desc(SessionMessage.timestamp)).first()

        if latest_message:
            # Use IST timezone for time comparison
            ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            now = datetime.datetime.now(ist_timezone)
            # Ensure message timestamp is offset-aware (assuming UTC if naive) before converting
            message_time_utc = latest_message.timestamp
            if message_time_utc.tzinfo is None:
                message_time_utc = message_time_utc.replace(tzinfo=datetime.timezone.utc)

            message_time_ist = message_time_utc.astimezone(ist_timezone)
            # Compare offset-aware times
            time_diff = now - message_time_ist
            if time_diff.total_seconds() < 2 * 60 * 60:  # Resume within 2 hours
                logger.info(f"Resuming recent session {latest_message.session_id} for user {user_id}")
                return latest_message.session_id
            else:
                logger.info(f"Last session {latest_message.session_id} for user {user_id} is too old ({time_diff}).")

        return None

    def get_session_history(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a specific session, formatted for LLM.
        Prioritizes in-memory history, falls back to database.

        Args:
            user_id: User identifier.
            session_id: Session identifier.

        Returns:
            List of LLM-formatted messages ({'role': 'user'/'assistant', 'content': ...}).
        """
        # 1. Check active memory first
        if session_id in self.active_sessions:
            logger.debug(f"Returning history for session {session_id} from active memory.")
            return self.active_sessions[session_id]

        # 2. If not in memory, load from database
        logger.debug(f"Loading history for session {session_id} from database.")
        messages_from_db = self.db.query(SessionMessage).filter(
            SessionMessage.user_id == user_id,
            SessionMessage.session_id == session_id
        ).order_by(SessionMessage.timestamp).all()

        # Format messages for the LLM
        # *** WARNING: Assumes alternating user/assistant roles based on order. ***
        # *** This is potentially incorrect if the first message isn't 'user' or order is broken. ***
        # *** A robust solution requires storing the role in the SessionMessage table. ***
        formatted_messages = []
        for i, msg in enumerate(messages_from_db):
            role = "user" if i % 2 == 0 else "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg.message
            })

        # Load into active memory for subsequent calls within the same service instance lifetime
        self.active_sessions[session_id] = formatted_messages
        logger.info(f"Loaded {len(formatted_messages)} messages from DB into active memory for session {session_id}.")
        return formatted_messages

    def get_user_sessions(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """ Retrieves a list of the user's most recent sessions. """
        # Subquery to find the last timestamp for each session
        subq = self.db.query(
            SessionMessage.session_id,
            func.max(SessionMessage.timestamp).label('last_timestamp')
        ).filter(SessionMessage.user_id == user_id).group_by(SessionMessage.session_id).subquery('t2')

        # Main query to get session_id, first timestamp, and first message content, ordered by last timestamp
        sessions_query = self.db.query(
            SessionMessage.session_id,
            func.min(SessionMessage.timestamp).label('first_timestamp'),
            # Correlated subquery or window function might be better for 'first message', but this works if ID increments with time
            func.min(SessionMessage.message).label('first_message_content')
        ).join(subq, SessionMessage.session_id == subq.c.session_id)\
        .filter(SessionMessage.user_id == user_id)\
        .group_by(SessionMessage.session_id)\
        .order_by(desc(subq.c.last_timestamp))\
        .limit(limit)

        sessions_data = sessions_query.all()

        # Format the output
        return [{
            "session_id": sid,
            "timestamp": ft.isoformat(), # Use ISO format for consistency
            "first_message": (fmc[:50] + "..." if len(fmc or "") > 50 else (fmc or ""))
            } for sid, ft, fmc in sessions_data
        ]

    def _get_recent_session_summaries(self, user_id: str) -> str:
        """Fetches the cumulative session summary block from the user's profile."""
        user_profile = self._get_or_create_user_profile(user_id)

        if user_profile and user_profile.cumulative_summary:
            return user_profile.cumulative_summary
        else:
            # Return a specific string indicating no summaries, rather than None or empty string
            return "No previous session summaries available."

    def _build_system_prompt(self, user_id: str) -> str:
        """Constructs the detailed system prompt using user profile and cumulative summary."""
        user_profile = self._get_or_create_user_profile(user_id)
        # Fetches the cumulative summary string
        recent_sessions_block = self._get_recent_session_summaries(user_id)

        # Get current IST time
        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        current_ist_time_str = datetime.datetime.now(ist_timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

        profile_data = {
            "student_name": user_profile.username or "Student",
            "student_class": user_profile.student_class or "N/A",
            "student_board": user_profile.student_board or "N/A",
            "student_goals": user_profile.student_goals or "Not specified",
            "student_strengths": user_profile.student_strengths or "Not specified",
            "student_weaknesses": user_profile.student_weaknesses or "Not specified",
            "student_learning_style": user_profile.student_learning_style or "Adaptive",
            "recent_sessions_block": recent_sessions_block,
            "current_ist_time": current_ist_time_str
        }

        # Keep placeholder for inferred topic; LLM is expected to infer based on context
        profile_data["inferred_topic"] = "the previous topic"

        return EDU_TUTOR_SYSTEM_PROMPT_TEMPLATE.format(**profile_data)

    def generate_response(self, user_id: str, user_input: str, session_id: Optional[str] = None, stream: bool = False) -> Tuple[Any, str]:
        """
        Generates AI response, managing session history in memory.

        Args:
            user_id: User identifier.
            user_input: The user's message.
            session_id: Optional session ID. If None, tries to resume recent or creates new.
            stream: Whether to stream the response.

        Returns:
            Tuple containing:
            - If stream=False: response_text (str)
            - If stream=True: response_generator (generator)
            - response_id (str)
        """
        if not session_id:
            session_id = self.get_active_session(user_id)
            if not session_id:
                 session_id = self.create_session(user_id)
                 logger.info(f"No active session found or resumable for {user_id}. Started new session: {session_id}")
            else:
                # Ensure history is loaded if we are resuming a session not already active in memory
                if session_id not in self.active_sessions:
                    self.get_session_history(user_id, session_id) # Loads history into active_sessions

        # Now, session_id is guaranteed to exist and its history (even if empty) is in active_sessions
        conversation_history = self.active_sessions[session_id]
        system_prompt = self._build_system_prompt(user_id)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history) # Add past messages from this session (already in memory)
        messages.append({"role": "user", "content": user_input})

        # Limit history length sent to LLM (excluding system prompt)
        if len(messages) > MAX_HISTORY_LENGTH + 1: # +1 for system prompt
             messages = [messages[0]] + messages[-(MAX_HISTORY_LENGTH):]

        logger.debug(f"Sending {len(messages)} messages (history limited to {MAX_HISTORY_LENGTH}) to LLM for user {user_id} in session {session_id}")

        response_id = f"resp_{uuid.uuid4().hex[:8]}"

        # Update in-memory session with user message *before* LLM call
        self.active_sessions[session_id].append({"role": "user", "content": user_input})
        # Prune in-memory history if it exceeds max length (keep it consistent with LLM view)
        # We keep more than MAX_HISTORY_LENGTH in memory potentially, but only send the tail to LLM
        # Let's adjust this: prune active_sessions as well to avoid unbounded growth
        if len(self.active_sessions[session_id]) > MAX_HISTORY_LENGTH:
             self.active_sessions[session_id] = self.active_sessions[session_id][-MAX_HISTORY_LENGTH:]
             logger.debug(f"In-memory history for {session_id} pruned to last {MAX_HISTORY_LENGTH} messages.")


        try:
            if stream:
                def response_generator() -> Generator[str, None, None]:
                    full_response = ""
                    current_sentence = ""
                    
                    if not polly_client:
                        logger.error("Polly client not available. Cannot generate audio.")
                        yield json.dumps({"error": "Text-to-speech service is unavailable."}) + "\n"
                        return

                    try:
                        stream_response = client.chat.completions.create(
                            model=LLM_MODEL,
                            messages=messages,
                            max_tokens=1000,
                            temperature=0.7,
                            stream=True
                        )
                        
                        # For sentence detection
                        sentence_end_patterns = re.compile(r'[.!?]+')
                        
                        for chunk in stream_response:
                            if chunk.choices and chunk.choices[0].delta.content:
                                text_content = chunk.choices[0].delta.content
                                full_response += text_content
                                
                                # Process content at word level
                                words = text_content.split()
                                for word in words:
                                    # Send each word individually
                                    yield json.dumps({"word": word}) + "\n"
                                    
                                    # Append to current sentence buffer
                                    current_sentence += " " + word if current_sentence else word
                                    
                                    # Check if we have a complete sentence
                                    if sentence_end_patterns.search(word):
                                        # Found sentence end, generate audio for the complete sentence
                                        try:
                                            polly_response = polly_client.synthesize_speech(
                                                Text=current_sentence,
                                                OutputFormat='mp3',
                                                VoiceId='Joanna',
                                                Engine='neural'
                                            )
                                            
                                            audio_stream = polly_response.get('AudioStream')
                                            if audio_stream:
                                                audio_data = audio_stream.read()
                                                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                                                # Send the audio for the completed sentence
                                                yield json.dumps({"audio": audio_base64}) + "\n"
                                            else:
                                                logger.warning(f"No AudioStream received from Polly for sentence: {current_sentence[:30]}...")
                                        
                                        except (BotoCoreError, ClientError) as polly_err:
                                            logger.error(f"Polly synthesis error: {polly_err}")
                                        
                                        # Send sentence end marker
                                        yield json.dumps({"sentence_end": True}) + "\n"
                                        
                                        # Reset current sentence
                                        current_sentence = ""
                        
                        # Handle any remaining text as a final sentence if needed
                        if current_sentence:
                            try:
                                polly_response = polly_client.synthesize_speech(
                                    Text=current_sentence,
                                    OutputFormat='mp3',
                                    VoiceId='Joanna',
                                    Engine='neural'
                                )
                                
                                audio_stream = polly_response.get('AudioStream')
                                if audio_stream:
                                    audio_data = audio_stream.read()
                                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                                    yield json.dumps({"audio": audio_base64}) + "\n"
                            except (BotoCoreError, ClientError) as polly_err:
                                logger.error(f"Polly synthesis error for final sentence: {polly_err}")
                            
                            # Final sentence end marker
                            yield json.dumps({"sentence_end": True}) + "\n"

                        # After successful streaming, update history with the full text
                        self.active_sessions[session_id].append({"role": "assistant", "content": full_response})
                        logger.info(f"Completed streaming response with TTS for session {session_id}")
                        
                        # Prune again after adding assistant response
                        if len(self.active_sessions[session_id]) > MAX_HISTORY_LENGTH:
                            self.active_sessions[session_id] = self.active_sessions[session_id][-MAX_HISTORY_LENGTH:]

                    except Exception as stream_exc:
                        logger.error(f"Error during LLM stream for {session_id}: {stream_exc}", exc_info=True)
                        yield json.dumps({"error": "I'm sorry, an error occurred while generating the response."}) + "\n"

                return response_generator(), response_id
            else:
                # Non-streaming response
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages, # Uses potentially truncated message list
                    max_tokens=1000,
                    temperature=0.7
                )
                ai_response = response.choices[0].message.content.strip()
                logger.info(f"Generated non-streaming response for session {session_id}")

                # Update in-memory session history
                self.active_sessions[session_id].append({"role": "assistant", "content": ai_response})
                # Prune after adding assistant response
                if len(self.active_sessions[session_id]) > MAX_HISTORY_LENGTH:
                    self.active_sessions[session_id] = self.active_sessions[session_id][-MAX_HISTORY_LENGTH:]

                return ai_response, response_id

        except Exception as e:
            logger.error(f"Error calling LLM API for {session_id}: {e}", exc_info=True)
            error_message = "I'm sorry, I encountered an error trying to process your request. Please try again."
            # Add error message to history *instead* of AI response?
            # Or maybe don't add anything to history on failure? Let's not add it.
            # self.active_sessions[session_id].append({"role": "assistant", "content": error_message}) # Decide if this is desired

            if stream:
                # Return a generator that just yields the error
                def error_generator():
                    yield error_message + "\n"
                return error_generator(), response_id
            else:
                return error_message, response_id

    def _save_message(self, user_id: str, session_id: str, message_content: str, role: str) -> SessionMessage:
        """ Internal helper to save a single message to DB. """
        # Note: This assumes SessionMessage table has columns for user_id, session_id, message, timestamp
        # It currently *doesn't* save the 'role', which causes issues elsewhere.
        # To fix the role issue, the SessionMessage model and this function need updating.
        session_message = SessionMessage(
            user_id=user_id,
            session_id=session_id,
            message=message_content
            # timestamp is likely handled by DB default or SQLAlchemy DefaultClause
        )
        self.db.add(session_message)
        # Commit is handled by calling functions (end_session, save_session)
        return session_message

    def _save_session_messages_from_memory(self, user_id: str, session_id: str) -> Tuple[bool, int]:
        """ Internal helper to save messages from memory to DB, avoiding duplicates. """
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found in active memory for saving.")
            return False, 0

        messages_in_memory = self.active_sessions[session_id]
        if not messages_in_memory:
            logger.info(f"No messages in memory for session {session_id} to save.")
            return True, 0 # Nothing to save, operation considered successful

        logger.info(f"Attempting to save {len(messages_in_memory)} messages from memory for session {session_id}.")

        try:
            # Find the timestamp of the last saved message for this session, if any
            last_saved_message = self.db.query(SessionMessage).filter(
                SessionMessage.user_id == user_id,
                SessionMessage.session_id == session_id
            ).order_by(desc(SessionMessage.timestamp)).first()

            # Determine which messages in memory are new
            # This assumes memory messages are ordered chronologically and roles are correct.
            # A more robust way might involve unique message IDs if available.
            # For now, we assume we just need to save *all* messages present in memory,
            # relying on the application logic to call save/end only once needed.
            # Let's refine the previous logic: only save messages *not already* in DB.
            # This requires fetching all DB messages, which is inefficient.
            # The original logic comparing counts is simpler but assumes memory only contains *new* messages
            # or that memory exactly mirrors DB + new messages. Let's stick to the count logic for now.

            existing_db_messages_count = self.db.query(func.count(SessionMessage.id)).filter(
                 SessionMessage.user_id == user_id,
                 SessionMessage.session_id == session_id
            ).scalar() or 0

            messages_saved_count = 0
            if len(messages_in_memory) > existing_db_messages_count:
                new_messages = messages_in_memory[existing_db_messages_count:]
                logger.info(f"Found {len(new_messages)} new messages in memory for session {session_id} to save.")
                for msg_dict in new_messages:
                    self._save_message(user_id, session_id, msg_dict["content"], msg_dict["role"])
                    messages_saved_count += 1

                if messages_saved_count > 0:
                    self.db.commit()
                    logger.info(f"Committed {messages_saved_count} new messages for session {session_id}.")
                else:
                     logger.info(f"No new messages needed saving for session {session_id} based on count comparison.")
                return True, messages_saved_count
            else:
                 logger.info(f"Memory message count ({len(messages_in_memory)}) not greater than DB count ({existing_db_messages_count}). No messages saved for session {session_id}.")
                 return True, 0 # Successful operation, nothing needed saving

        except Exception as e:
            logger.error(f"Error saving messages from memory for {session_id}: {e}", exc_info=True)
            self.db.rollback()
            return False, 0 # Indicate failure

    def end_session(self, user_id: str, session_id: str) -> bool:
        """Ends an active session, saves messages from memory to DB, and clears from memory."""
        logger.info(f"Attempting to end session {session_id} for user {user_id}.")

        success, _ = self._save_session_messages_from_memory(user_id, session_id)

        if success:
            # Clear from memory only if save was successful (or not needed)
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"Cleared session {session_id} from active memory.")
            # Attempt summarization after saving and before clearing fully? Or is summarization separate?
            # Let's assume summarization is called separately when needed.
            return True
        else:
            logger.error(f"Failed to save messages for session {session_id}. Session not cleared from memory.")
            return False # Indicate failure

    def save_session(self, user_id: str, session_id: str) -> bool:
        """Saves messages from memory to DB without ending the session."""
        logger.info(f"Attempting to save session {session_id} (keep active) for user {user_id}.")
        success, _ = self._save_session_messages_from_memory(user_id, session_id)
        return success

    def _get_or_create_user_profile(self, user_id: str) -> UserProfile:
        """Gets user profile from DB or creates a default one."""
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

        if not profile:
            logger.info(f"Creating new user profile for user_id: {user_id}")
            profile = UserProfile(
                user_id=user_id,
                username="New Student", # Default values
                student_class="N/A",
                student_board="N/A",
                student_goals="Explore topics",
                student_strengths="Eager to learn",
                student_weaknesses="To be identified",
                student_learning_style="Adaptive",
                cumulative_summary="", # Initialize as empty string
                total_sessions=0
            )
            self.db.add(profile)
            try:
                self.db.commit()
                self.db.refresh(profile) # Refresh to get DB-assigned defaults/IDs
                logger.info(f"Successfully created and committed profile for {user_id}.")
            except Exception as e:
                logger.error(f"Error committing new user profile for {user_id}: {e}", exc_info=True)
                self.db.rollback()
                # Re-raise allows calling function to know profile creation failed
                raise # Or handle more gracefully depending on requirements

        return profile

    def summarize_session(self, user_id: str, session_id: str) -> bool:
        """
        Uses an LLM to generate a summary for a given session AND update
        the cumulative summary block in the user's profile.

        Returns:
            bool: True if the LLM call, validation, and DB update were successful, False otherwise.
        """
        logger.info(f"Starting summary update process for session {session_id}, user {user_id}")

        # 1. Get messages for the specified session from the database
        messages = self.db.query(SessionMessage).filter(
            SessionMessage.user_id == user_id,
            SessionMessage.session_id == session_id
        ).order_by(SessionMessage.timestamp).all()

        if not messages:
            logger.warning(f"No messages found in DB for session {session_id}. Cannot generate summary.")
            return False

        # Determine session timestamp (use first message's timestamp)
        # Ensure timestamp is timezone-aware (assume UTC if naive)
        session_timestamp_utc = messages[0].timestamp
        if session_timestamp_utc.tzinfo is None:
            session_timestamp_utc = session_timestamp_utc.replace(tzinfo=datetime.timezone.utc)

        # Prepare conversation text for the prompt
        conversation_details = []
        # *** WARNING: Using index-based role assignment. See warning in get_session_history. ***
        for i, msg in enumerate(messages):
             role = "User" if i % 2 == 0 else "AI"
             conversation_details.append(f"{role}: {msg.message}")
        conversation_text = "\n".join(conversation_details)

        # 2. Get existing cumulative summary and user profile
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            existing_summary = user_profile.cumulative_summary or "" # Ensure it's a string
        except Exception as e:
             logger.error(f"Failed to retrieve/create user profile for {user_id} during summarization: {e}", exc_info=True)
             return False # Cannot proceed without profile

        # 3. Construct the LLM prompt
        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        ist_session_timestamp = session_timestamp_utc.astimezone(ist_timezone)
        session_datetime_str = ist_session_timestamp.strftime("%Y-%m-%d %H:%M") # Format for prompt

        prompt = f"""You are an expert assistant maintaining a student's chronological session summary log.
Each entry must be on a new line, possibly separated by one blank line, and strictly follow the format:
– *[YYYY-MM-DD HH:MM]:* [Summary Text]

Where:
- [YYYY-MM-DD HH:MM] is the date and time the session occurred (e.g., 2024-07-21 15:30). Use the provided session time.
- [Summary Text] is a concise 1-2 sentence summary starting with a verb (e.g., Learned, Practiced, Reviewed, Explored).

EXISTING SUMMARY LOG (if any):
{existing_summary.strip()}

TRANSCRIPT OF THE NEW SESSION (occurred at {session_datetime_str}):
--- START TRANSCRIPT ---
{conversation_text}
--- END TRANSCRIPT ---

YOUR TASK:
1. Generate a concise summary (1-2 sentences, starting with a verb) for the NEW session transcript.
2. Format the new summary entry as: – *{session_datetime_str}:* [Your generated summary text]
3. Append this new entry to the end of the EXISTING SUMMARY LOG. If the existing log is empty, the new entry will be the only content. Maintain chronological order implicitly by appending. Ensure a blank line separates entries if the existing log was not empty.
4. Ensure the final output contains ONLY the complete summary log (previous entries + new entry). Each entry MUST start with '– *' and be followed by the date, time, and summary. Do NOT include any other text, preamble, explanations, or markers like '--- START LOG ---' or '--- END LOG ---'.

Updated Summary Log:"""

        logger.debug("------ LLM SUMMARY PROMPT ------\n" + prompt + "\n-----------------------------")

        # 4. Call the LLM
        try:
            logger.debug(f"Sending summary update prompt to {SUMMARY_MODEL} for session {session_id}")
            response = client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert log keeper. Follow the user's instructions precisely to update the summary log. Output only the log entries as requested, ensuring the new entry is appended correctly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=max(1000, len(existing_summary.split()) * 2 + 400) # Dynamic token allocation
            )
            updated_summary_block = response.choices[0].message.content.strip()

            # 5. Validation of LLM Output
            # Basic check: Is it non-empty? Does it contain the new session timestamp?
            # A stricter check might involve regex or parsing, but let's keep it simple.
            if not updated_summary_block or session_datetime_str not in updated_summary_block:
                logger.error(f"LLM summary output validation FAILED for session {session_id}. Output missing timestamp or is empty. Output (first 200 chars): '{updated_summary_block[:200]}...'")
                return False # Indicate summarization failure
            # Check if it starts roughly correctly (might have newline issues)
            if not updated_summary_block.lstrip().startswith("–"):
                 logger.warning(f"LLM summary output for session {session_id} does not start with '–'. Check formatting. Output (first 200 chars): '{updated_summary_block[:200]}...'")
                 # Decide if this is a failure or just a warning. Let's treat it as success for now but log warning.

            logger.info(f"LLM generated updated summary block for user {user_id}, session {session_id}.")

            # 6. Save the validated/updated summary block to the profile
            try:
                user_profile.cumulative_summary = updated_summary_block
                # Increment total sessions count? Or is that handled elsewhere? Let's add it here.
                # This assumes summarize is called once per completed session.
                user_profile.total_sessions = (user_profile.total_sessions or 0) + 1
                self.db.commit()
                logger.info(f"Successfully saved LLM-updated cumulative summary and incremented session count for user {user_id}")
                return True # Indicate success

            except Exception as db_exc:
                logger.error(f"Database error saving LLM-updated summary for {user_id}: {db_exc}", exc_info=True)
                self.db.rollback()
                return False # DB save failed

        except Exception as llm_exc:
            logger.error(f"LLM API error during summary update for {session_id}: {llm_exc}", exc_info=True)
            return False # LLM call failed

        # Removed the duplicate save block that was here previously
