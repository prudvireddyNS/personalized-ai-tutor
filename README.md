# Personalized AI Tutor

A cutting-edge AI-powered tutoring platform that provides personalized learning experiences tailored to individual student needs. This application leverages advanced machine learning and natural language processing to deliver adaptive educational content and real-time feedback.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## 📖 Overview

Personalized AI Tutor is an intelligent tutoring system designed to adapt to each student's learning pace, style, and preferences. The platform analyzes student interactions, identifies knowledge gaps, and generates customized learning paths to maximize educational outcomes.

### Key Objectives

- Provide personalized learning experiences for students of all levels
- Offer real-time feedback and progress tracking
- Adapt content difficulty based on student performance
- Support multiple subjects and learning domains
- Enable instructors to monitor and manage student progress

## ✨ Features

### Core Features

- **Personalized Learning Paths**: Adaptive curriculum that adjusts based on student performance and learning style
- **AI-Powered Content Generation**: Dynamic creation of practice problems, explanations, and learning materials
- **Real-Time Feedback**: Instant feedback on student responses with detailed explanations
- **Progress Tracking**: Comprehensive analytics and progress monitoring for both students and instructors
- **Multi-Subject Support**: Support for various academic subjects and learning domains
- **Interactive Learning**: Engaging interactive tools including quizzes, practice problems, and simulations
- **Natural Language Processing**: Conversational tutoring interface for questions and discussions
- **Performance Analytics**: Detailed insights into student strengths, weaknesses, and learning patterns

### Advanced Features

- Spaced repetition algorithm for optimal knowledge retention
- Difficulty level adaptation based on mastery
- Multi-language support
- Export learning reports and certificates
- Integration with educational platforms
- Offline mode support

## 🛠 Tech Stack

- **Backend**: Python, FastAPI
- **AI/ML**: OpenAI API, TensorFlow, scikit-learn
- **Database**: PostgreSQL, Redis
- **Frontend**: React, TypeScript
- **Authentication**: JWT, OAuth 2.0
- **Deployment**: Docker, Kubernetes
- **Monitoring**: Prometheus, ELK Stack

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- Node.js 16+ (for frontend)
- PostgreSQL 12+
- Docker and Docker Compose (optional)
- Git

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/prudvireddyNS/personalized-ai-tutor.git
cd personalized-ai-tutor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Configure environment variables (see Configuration section)
nano .env
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment configuration
cp .env.example .env

# Configure environment variables
nano .env
```

### Docker Setup

```bash
# Build and run using Docker Compose
docker-compose up -d

# Access the application
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Backend Configuration
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/ai_tutor
REDIS_URL=redis://localhost:6379/0

# AI/ML Services
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7

# Authentication
JWT_SECRET_KEY=your-jwt-secret-key
JWT_EXPIRATION_HOURS=24
REFRESH_TOKEN_EXPIRATION_DAYS=30

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=True

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_ENV=development

# AWS/Cloud Services (if applicable)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=ai-tutor-bucket
AWS_REGION=us-east-1
```

## 🚀 Usage

### Starting the Application

#### Local Development

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm start
```

#### Docker

```bash
docker-compose up
```

### Accessing the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **API Schema**: http://localhost:8000/redoc (ReDoc)

### User Registration

1. Navigate to the registration page
2. Enter email and create a password
3. Verify email address
4. Select role (Student/Instructor)
5. Complete profile setup

### For Students

1. **Select a Course**: Browse available courses or join through an invitation code
2. **Start Learning**: Follow the personalized learning path
3. **Practice**: Complete interactive exercises and quizzes
4. **Track Progress**: Monitor your learning analytics and achievements

### For Instructors

1. **Create Courses**: Set up new courses with learning objectives
2. **Manage Classes**: Add students and organize them into groups
3. **Monitor Progress**: View detailed analytics for each student
4. **Generate Reports**: Create comprehensive progress reports

## 📡 API Endpoints

### Authentication Endpoints

```
POST   /api/v1/auth/register          - User registration
POST   /api/v1/auth/login             - User login
POST   /api/v1/auth/refresh-token     - Refresh access token
POST   /api/v1/auth/logout            - User logout
POST   /api/v1/auth/forgot-password   - Request password reset
POST   /api/v1/auth/reset-password    - Reset password
```

### User Endpoints

```
GET    /api/v1/users/profile          - Get user profile
PUT    /api/v1/users/profile          - Update user profile
GET    /api/v1/users/{id}             - Get user by ID
DELETE /api/v1/users/{id}             - Delete user account
```

### Course Endpoints

```
GET    /api/v1/courses                - List all courses
POST   /api/v1/courses                - Create new course (Instructor)
GET    /api/v1/courses/{id}           - Get course details
PUT    /api/v1/courses/{id}           - Update course (Instructor)
DELETE /api/v1/courses/{id}           - Delete course (Instructor)
GET    /api/v1/courses/{id}/lessons   - Get course lessons
POST   /api/v1/courses/{id}/enroll    - Enroll in course
```

### Learning Endpoints

```
GET    /api/v1/lessons/{id}           - Get lesson details
POST   /api/v1/lessons/{id}/complete  - Mark lesson as complete
GET    /api/v1/quiz/{id}              - Get quiz questions
POST   /api/v1/quiz/{id}/submit       - Submit quiz answers
GET    /api/v1/assignments/{id}       - Get assignment details
POST   /api/v1/assignments/{id}/submit - Submit assignment
```

### AI Tutoring Endpoints

```
POST   /api/v1/tutor/ask              - Ask AI tutor a question
POST   /api/v1/tutor/explain          - Get explanation for a concept
POST   /api/v1/tutor/practice         - Generate practice problems
POST   /api/v1/tutor/feedback         - Get AI feedback on work
```

### Analytics Endpoints

```
GET    /api/v1/analytics/progress     - Get learning progress
GET    /api/v1/analytics/performance  - Get performance metrics
GET    /api/v1/analytics/strengths    - Get strength/weakness analysis
GET    /api/v1/analytics/recommendations - Get learning recommendations
```

### Admin Endpoints

```
GET    /api/v1/admin/users            - List all users (Admin)
GET    /api/v1/admin/statistics       - Get system statistics (Admin)
GET    /api/v1/admin/reports          - Generate reports (Admin)
```

### Request/Response Examples

#### User Registration

```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "student@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student"
}

Response: 201 Created
{
  "id": "user-uuid",
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "created_at": "2026-01-14T10:57:13Z"
}
```

#### Ask AI Tutor

```bash
POST /api/v1/tutor/ask
Authorization: Bearer {token}
Content-Type: application/json

{
  "lesson_id": "lesson-uuid",
  "question": "Can you explain photosynthesis?",
  "context": "chapter_3"
}

Response: 200 OK
{
  "response": "Photosynthesis is the process by which plants...",
  "explanation_level": "intermediate",
  "related_topics": ["cellular_respiration", "chloroplasts"],
  "suggested_resources": ["video_link", "article_link"],
  "timestamp": "2026-01-14T10:57:13Z"
}
```

#### Get Learning Progress

```bash
GET /api/v1/analytics/progress
Authorization: Bearer {token}

Response: 200 OK
{
  "user_id": "user-uuid",
  "overall_progress": 65.5,
  "courses": [
    {
      "course_id": "course-uuid",
      "course_name": "Introduction to Python",
      "progress": 80.0,
      "lessons_completed": 12,
      "total_lessons": 15
    }
  ],
  "recent_achievements": ["first_lesson", "quiz_master"],
  "learning_streak": 7
}
```

## 🤝 Contributing

We welcome contributions from the community! Please follow these guidelines to contribute to the Personalized AI Tutor project.

### How to Contribute

1. **Fork the Repository**
   ```bash
   git clone https://github.com/prudvireddyNS/personalized-ai-tutor.git
   cd personalized-ai-tutor
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Write clean, well-documented code
   - Follow the project's coding standards
   - Add tests for new functionality
   - Update documentation as needed

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Provide a clear description of your changes
   - Reference any related issues
   - Ensure all tests pass
   - Wait for code review and feedback

### Coding Standards

- **Python**: Follow PEP 8 style guide
- **JavaScript/TypeScript**: Follow ESLint configuration
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)
- **Testing**: Maintain >80% code coverage
- **Documentation**: Document all public functions and classes

### Development Workflow

```bash
# Install development dependencies
pip install -r requirements-dev.txt
npm install

# Run tests
pytest                          # Backend tests
npm test                        # Frontend tests

# Run linting
flake8 .
black .
npm run lint

# Run type checking
mypy .
npm run type-check
```

