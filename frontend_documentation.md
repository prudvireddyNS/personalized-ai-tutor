# Documentation 

## Core Workflow

### 1. User Creation

**Endpoint:** `POST /users/`

**Purpose:** Create a new student profile in the system

**Request Body:**
```json
{
  "username": "Student Name",
  "student_class": "10",
  "student_board": "CBSE",
  "student_goals": "Improve math scores",
  "student_strengths": "Good at problem-solving",
  "student_weaknesses": "Struggles with algebra",
  "student_learning_style": "Visual"
}
```

**Response:**
```json
{
  "user_id": "generated-uuid",
  "username": "Student Name",
  "student_class": "10",
  "student_board": "CBSE",
  "student_goals": "Improve math scores",
  "student_strengths": "Good at problem-solving",
  "student_weaknesses": "Struggles with algebra",
  "student_learning_style": "Visual",
  "total_sessions": 0,
  "cumulative_summary": null
}
```

**Important Notes:**
- The system automatically generates a `user_id` - store this in your frontend for all future requests
- Only `username`, `student_class`, and `student_board` are required fields

### 2. Session Creation

**Endpoint:** `POST /sessions/create`

**Purpose:** Start a new tutoring session

**Request Body:**
```json
{
  "user_id": "user-uuid-from-step-1"
}
```

**Response:**
```json
{
  "session_id": "generated-session-id",
  "timestamp": "2023-06-15T10:30:00Z"
}
```

**Important Notes:**
- Store the `session_id` for all messages in this tutoring session
- A session represents one conversation between the student and tutor

### 3. Messaging

**Endpoint:** `POST /sessions/message`

**Purpose:** Send a student message and get the AI tutor's response

**Request Body:**
```json
{
  "user_id": "user-uuid",
  "message": "Can you help me understand quadratic equations?",
  "session_id": "session-id-from-step-2"
}
```

**Response:**
```json
{
  "user_id": "user-uuid",
  "session_id": "session-id",
  "response_text": "Hi [Student Name]! I'd be happy to help you understand quadratic equations...",
  "response_id": "unique-response-id"
}
```

**Important Notes:**
- The `session_id` is optional - if omitted, the system will use the most recent active session or create a new one
- The AI tutor customizes responses based on the student's profile and learning history
- Each message/response pair is stored in the session history

### 4. Session End

**Endpoint:** `POST /sessions/{session_id}/end`

**Purpose:** End the current tutoring session and generate a summary

**Request Body:**
```json
{
  "user_id": "user-uuid"
}
```

**Response:**
```json
{
  "message": "Session ended, messages saved. Cumulative summary updated by AI.",
  "user_id": "user-uuid",
  "session_id": "session-id",
  "summary_updated": true
}
```

**Important Notes:**
- Ending a session triggers the AI to update the student's learning profile
- The system maintains a cumulative summary of all sessions for personalized learning
- Frontend should provide a clear way for users to end sessions

## Additional Helpful Endpoints

### View User Profile

**Endpoint:** `GET /users/{user_id}`

**Purpose:** Retrieve a student's profile information

### View Session History

**Endpoint:** `GET /sessions/history/{user_id}/{session_id}`

**Purpose:** Get the complete conversation history for a specific session

### List User Sessions

**Endpoint:** `GET /sessions/list/{user_id}`

**Purpose:** Get a list of previous sessions for a user

## Implementation Tips

1. **User Flow:** Create user → Start session → Exchange messages → End session
2. **Error Handling:** All endpoints return appropriate HTTP status codes with error details
3. **State Management:** Store user_id and active session_id in your frontend state
4. **UI Considerations:**
   - Provide a welcome screen for new users to create their profile
   - Consider a dashboard to view past sessions and learning progress
