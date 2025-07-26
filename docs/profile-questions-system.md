# Profile Questions System Architecture

This document outlines the complete architecture and flow of the business profile questionnaire system in the mental-model application.

## Overview

The profile questions system is a chat-integrated questionnaire that collects business context from users to personalize AI responses. It supports both modal and inline presentation modes with seamless integration into the chat experience.

## High-Level Architecture

```
User Interface → API Endpoints → Questionnaire Service → Supabase + Zep Integration
     ↓              ↓                   ↓                      ↓
Frontend         Backend          Business Logic         Data Storage
Components       FastAPI          Commands               & Memory
```

## Core Components

### Frontend Components

#### 1. BusinessProfileQuestionnaire.js
**Location**: `frontend/src/components/BusinessProfileQuestionnaire.js`

**Purpose**: Main orchestrator component that manages the questionnaire flow

**Key Features**:
- Supports both modal and inline presentation modes
- Manages question progression and user answers
- Handles loading states and error management
- Integrates with backend APIs for persistence

**Props**:
- `user` - Current authenticated user
- `onComplete` - Callback when questionnaire is finished
- `onProgress` - Callback for progress updates
- `onClose` - Callback for closing/pausing questionnaire
- `initialQuestion` - Starting question number (default: 1)
- `mode` - Display mode ('inline' or 'modal')

**State Management**:
- `questions` - Array of question objects
- `currentQuestionIndex` - Current position in questionnaire
- `answers` - User responses mapped by question ID
- `progress` - Progress tracking object
- `isLoading` / `isSaving` - Loading states

#### 2. ProfileQuestionCard.js
**Location**: `frontend/src/components/ProfileQuestionCard.js`

**Purpose**: Renders individual questions with appropriate input types

**Supported Question Types**:
- `text` - Multi-line textarea input
- `select` - Radio button options from JSON array
- `scale` - Numeric scale with optional labels
- `default` - Single-line text input

**Features**:
- Real-time answer validation
- Loading states during submission
- Accessibility support with ARIA labels
- First question welcome notice

#### 3. ProfileProgressIndicator.js
**Location**: `frontend/src/components/ProfileProgressIndicator.js`

**Purpose**: Visual progress bar showing completion status

#### 4. Integration Points

**ChatPanel.js** (`frontend/src/components/ChatPanel.js:1165-1173`):
- Shows questionnaire in modal overlay when `showQuestionnaire` is true
- Handles completion and progress callbacks
- Manages questionnaire state alongside chat functionality

**UserProfile.js** (`frontend/src/components/UserProfile.js:507-517`):
- Provides access to questionnaire from user profile modal
- Displays in modal mode with close-on-complete behavior

### Backend Components

#### 1. QuestionnaireService
**Location**: `backend/questionnaire_service.py`

**Purpose**: Core business logic for questionnaire management

**Key Methods**:

**`start_questionnaire(user_id)`**:
- Ensures Zep user exists before starting
- Creates progress record in database
- Returns first question and initial progress

**`submit_answer(user_id, question_id, answer_text)`**:
- Validates and saves answer to Supabase
- Syncs answer to Zep for context building
- Manages progression to next question or completion
- Returns next question or completion status

**`handle_command(user_id, command)`**:
- Processes navigation commands: "skip", "pause", "previous", "resume"
- Updates progress and question position
- Returns appropriate response based on command

**`get_current_question(user_id)` / `get_questionnaire_status(user_id)`**:
- Retrieves current state for resume functionality
- Provides progress information for UI updates

#### 2. API Endpoints
**Location**: `backend/main.py`

**Core Endpoints**:

- `POST /api/questionnaire/start` - Initialize questionnaire session
- `GET /api/questionnaire/current/{user_id}` - Get current question
- `GET /api/questionnaire/status/{user_id}` - Get progress status
- `POST /api/questionnaire/answer` - Submit answer to question
- `POST /api/questionnaire/command` - Handle navigation commands
- `GET /api/questionnaire/responses/{user_id}` - Get all user responses

**Request/Response Models**:
- `QuestionnaireAnswerRequest` - Answer submission data
- `QuestionnaireCommandRequest` - Command execution data

### Data Storage

#### 1. Supabase Tables

**`questionnaire_questions`**:
- Stores the 11 business profile questions
- Fields: `id`, `question_number`, `question_text`, `answer_type`, `options`, `question_category`

**`user_questionnaire_responses`**:
- User answers with metadata
- Fields: `user_id`, `question_id`, `response_text`, `skipped`, `created_at`, `updated_at`

**`user_questionnaire_progress`**:
- Progress tracking per user
- Fields: `user_id`, `status`, `current_question`, `started_at`, `completed_at`, `last_updated`

#### 2. Zep Integration

**User Context Building**:
- Each answer is synced to Zep as a business profile entity
- Entity ID format: `business_profile_q{question_number}`
- Enables personalized AI responses based on business context
- Progressive context building as questionnaire progresses

## Data Flow

### 1. Questionnaire Initialization
```
User triggers questionnaire
    ↓
Frontend calls /api/questionnaire/start
    ↓
Backend ensures Zep user exists
    ↓
Creates progress record (status: in_progress, current_question: 1)
    ↓
Returns first question to frontend
    ↓
UI renders ProfileQuestionCard
```

### 2. Answer Submission
```
User submits answer
    ↓
Frontend calls /api/questionnaire/answer
    ↓
Backend validates and saves to Supabase
    ↓
Syncs answer to Zep for context building
    ↓
Checks if questionnaire complete (11 questions answered)
    ↓
If complete: marks status as 'completed'
If incomplete: returns next question
    ↓
Frontend updates UI with next question or completion state
```

### 3. Command Handling (Navigation)
```
User issues command (skip/pause/previous/resume)
    ↓
Frontend calls /api/questionnaire/command
    ↓
Backend processes command:
  - skip: marks current as skipped, moves to next
  - pause: sets status to 'paused'
  - previous: moves back one question
  - resume: sets status to 'in_progress'
    ↓
Returns updated state to frontend
    ↓
UI updates accordingly
```

## Current Navigation Commands

### Exit/Pause Commands
- `"pause"` - Pauses questionnaire, allows resume later

### Navigation Commands  
- `"skip"` - Skip current question
- `"previous"` - Go to previous question
- `"resume"` - Resume paused questionnaire

### Backend Command Processing
**Location**: `questionnaire_service.py:174-286`

Commands are processed with case-insensitive string matching:
```python
if command.lower() == "skip":
    # Skip logic
elif command.lower() == "pause":
    # Pause logic
elif command.lower() == "previous":
    # Previous logic
elif command.lower() == "resume":
    # Resume logic
```

## UI/UX Features

### Modal Mode
- Full overlay with close button in header
- "Pause & Continue Later" navigation button
- Completion celebration screen

### Inline Mode  
- Seamless integration within chat interface
- Progress indicator always visible
- Navigation controls contextual to current state

### Accessibility
- ARIA labels on all interactive elements
- Keyboard navigation support
- Screen reader friendly progress indicators
- Error states with clear messaging

### Error Handling
- Network error recovery with retry options
- Validation errors with clear feedback
- Graceful degradation when services unavailable

## Integration with Chat System

### Profile Nudge Banner
- Appears in chat when questionnaire incomplete
- Provides one-click access to start/resume questionnaire
- Dismissible but persistent until completion

### Context Enhancement
- Completed profile data automatically enhances chat responses
- Zep memory integration provides personalized business context
- No additional user action required after completion

## Performance Considerations

- Questions loaded one at a time to reduce initial load
- Answers saved immediately to prevent data loss
- Progress persisted across sessions
- Zep sync happens in background with retry logic
- Graceful handling of slow network conditions

## Future Enhancement Opportunities

1. **Command Expansion**: Support for more natural language commands
2. **Question Branching**: Conditional questions based on previous answers
3. **Progress Resume**: Deep linking to specific questions
4. **Analytics**: Completion rate and abandonment tracking
5. **Customization**: Admin interface for question management