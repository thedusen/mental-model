# Chat-Integrated Business Profile Questionnaire Implementation Plan

## Overview
Transform the business profile questionnaire from a modal popup into a seamless chat-based experience where users answer questions through the main chat interface while maintaining clean data separation.

## Core Architecture

### Key Design Decisions
1. **Separate Q&A from Chat History**: Questionnaire uses chat UI for display only, Q&A don't persist to chat history
2. **Dedicated Questionnaire Endpoints**: Clean separation from regular chat flow via `/api/questionnaire/*`
3. **Progressive Saving**: Answers saved to both Supabase and Zep after each individual question (not bulk at end)
4. **Zep Upsert Strategy**: Question data overwritten (not duplicated) when answers change using consistent entity IDs

## Database Schema

```sql
-- Store the 11 predefined questions
CREATE TABLE questionnaire_questions (
  id SERIAL PRIMARY KEY,
  question_number INTEGER UNIQUE NOT NULL,
  question_text TEXT NOT NULL,
  question_category VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Store user responses
CREATE TABLE user_questionnaire_responses (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  question_id INTEGER REFERENCES questionnaire_questions(id),
  response_text TEXT,
  skipped BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, question_id)
);

-- Track questionnaire progress
CREATE TABLE user_questionnaire_progress (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  current_question INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'not_started', -- not_started, in_progress, paused, completed
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  last_updated TIMESTAMP DEFAULT NOW()
);
```

### Seed Data (11 Business Profile Questions)
```sql
INSERT INTO questionnaire_questions (question_number, question_text, question_category) VALUES
(1, 'What industry is your business in?', 'business_context'),
(2, 'What is the size of your company (number of employees)?', 'business_context'),
(3, 'What is your role in the company?', 'personal_context'),
(4, 'What are your primary business goals for the next 12 months?', 'goals'),
(5, 'What are the biggest challenges your business currently faces?', 'challenges'),
(6, 'Who is your target customer or market?', 'market'),
(7, 'What products or services does your business offer?', 'offerings'),
(8, 'What is your current revenue model?', 'financial'),
(9, 'What key metrics do you track to measure success?', 'metrics'),
(10, 'What is your competitive advantage?', 'strategy'),
(11, 'What additional context would help me better understand your business?', 'context');
```

## Implementation Phases

### Phase 1: Backend Foundation

#### Files to Create/Modify
- **NEW**: `backend/questionnaire_service.py` - Core questionnaire logic
- **MODIFY**: `backend/main.py` - Add questionnaire endpoints
- **MODIFY**: `backend/supabase_client.py` - Add questionnaire database methods
- **NEW**: Database migration for questionnaire tables

#### API Endpoints
```python
# Questionnaire Management
POST /api/questionnaire/start
  - Initialize questionnaire session for user
  - Create progress record with status 'in_progress'
  - Return first question

GET /api/questionnaire/current
  - Get current question and progress for user
  - Return question details and progress info

POST /api/questionnaire/answer
  - Accept: {"user_id", "question_id", "answer_text"}
  - Save to Supabase user_questionnaire_responses
  - Immediately update/create Zep entity for this question
  - Update progress to next question
  - Return next question or completion status

POST /api/questionnaire/command
  - Handle special commands: "skip", "pause", "previous"
  - Update progress and return appropriate response

GET /api/questionnaire/all-responses
  - Return all user responses for edit form
  - Include question text and current answers

PUT /api/questionnaire/edit
  - Update specific question responses
  - Immediately sync changes to Zep (overwrite existing entity)
```

#### Zep Integration Strategy
**Progressive Saving Flow**:
1. User answers question → Save to Supabase
2. Immediately create/update Zep entity with consistent ID format: `business_profile_q{number}`
3. Use structured entity format for consistent AI context

**Zep Entity Structure**:
```json
{
  "entity_id": "business_profile_q1",
  "entity_type": "business_profile_question", 
  "question": "What industry is your business in?",
  "answer": "Software development",
  "question_number": 1,
  "answered_at": "2025-01-15T10:30:00Z",
  "category": "business_context"
}
```

**Upsert Logic**: When answer changes, overwrite existing Zep entity (prevent duplicates)

### Phase 2: Frontend Integration

#### Files to Remove (Existing Modal System)
- `frontend/src/components/ChatQuestionnaire.js`
- `frontend/src/components/QuestionnaireControls.js` 
- `frontend/src/components/QuestionnaireProgressBar.js`
- `frontend/src/components/QuestionnaireControls.css`
- `frontend/src/components/QuestionnaireProgressBar.css`
- Related CSS in `ChatPanel.css` for questionnaire focus mode

#### Files to Modify
- **`frontend/src/components/ChatPanel.js`**:
  - Add questionnaire state management
  - Route messages to questionnaire endpoints when in questionnaire mode
  - Display Q&A temporarily in chat UI (not persisted to history)  
  - Command detection for "skip", "pause", "previous"
  - Visual indicators (border highlight, progress bar)

#### New State Management
```javascript
// Add to ChatPanel state
const [questionnaireActive, setQuestionnaireActive] = useState(false);
const [currentQuestion, setCurrentQuestion] = useState(null);
const [questionnaireProgress, setQuestionnaireProgress] = useState({ current: 0, total: 11 });
const [tempQuestionnaireMessages, setTempQuestionnaireMessages] = useState([]);
```

#### Message Routing Logic
```javascript
// In message send handler
if (questionnaireActive) {
  // Handle questionnaire commands
  if (currentInput.toLowerCase() === 'skip') {
    await handleQuestionnaireCommand('skip');
    return;
  }
  // Submit answer to questionnaire
  await submitQuestionnaireAnswer(currentInput);
  return;
} else {
  // Regular chat flow
  await sendMessageToChat(message);
}
```

### Phase 3: Edit & Resume Features

#### New Components to Create
- **`frontend/src/components/QuestionnaireEditForm.js`**:
  - Traditional form showing all 11 questions
  - Prefilled with user's current answers
  - Save functionality that syncs to both Supabase and Zep

- **`frontend/src/components/QuestionnaireResumeNudge.js`**:
  - Banner component for incomplete questionnaires
  - Similar to existing ProfileNudgeBanner

#### Integration Points  
- **`frontend/src/components/LeftSidebar.js`**: Add questionnaire reminder box above profile
- **`frontend/src/components/ChatPanel.js`**: Show resume nudge when appropriate

## User Experience Flows

### Starting Questionnaire
1. User clicks "Start Business Profile" button or banner
2. Frontend calls `POST /api/questionnaire/start`
3. Chat UI enters questionnaire mode:
   - Border color changes to indicate mode
   - Progress bar appears: "Question 1 of 11"
   - AI presents first question as chat bubble (temporary display only)

### During Questionnaire  
1. User types answer in regular chat input
2. Answer sent to `POST /api/questionnaire/answer`
3. Backend saves to Supabase + immediately updates Zep
4. Next question returned and displayed as AI message
5. Progress bar updates: "Question 2 of 11"
6. **Commands**: "skip", "pause", "previous" intercepted and handled

### Pause/Resume Flow
1. User types "pause" → Backend saves progress with status 'paused'
2. Chat returns to normal mode, questionnaire UI elements disappear
3. Resume nudge appears in chat banner and sidebar
4. User clicks resume → Continue from last question

### Edit Flow
1. User clicks "Edit Answers" or types "edit answers"
2. Traditional form opens with all questions and prefilled answers
3. User modifies any answers and clicks save
4. Changes saved to Supabase and immediately synced to Zep (overwriting existing entities)

### Completion
1. After question 11, questionnaire mode ends automatically
2. Progress marked as 'completed' in database
3. All 11 answers now available as structured context in user's Zep knowledge graph
4. Chat returns to normal mode

## Error Handling & Edge Cases

### Network Resilience
- Each answer immediately saved to both Supabase and Zep
- Progress tracked in database survives browser refreshes
- Partial completions preserved and resumable

### Command Disambiguation  
- Commands only active during questionnaire mode
- "skip" during regular chat ignored or clarified
- Clear mode indicators prevent user confusion

### Data Consistency
- Zep entity IDs ensure no duplicates when answers change
- Database constraints prevent duplicate responses
- Failed Zep updates logged but don't block questionnaire flow

## Technical Implementation Notes

### Backend Service Structure
```python
# backend/questionnaire_service.py
class QuestionnaireService:
    def start_questionnaire(user_id)
    def get_current_question(user_id) 
    def submit_answer(user_id, question_id, answer_text)
    def handle_command(user_id, command)
    def get_all_responses(user_id)
    def update_response(user_id, question_id, new_answer)
    def _sync_to_zep(user_id, question_data)  # Private method for Zep updates
```

### Frontend State Management
- Questionnaire state isolated to ChatPanel
- Temporary message display without persistence
- Clear mode transitions and visual feedback

### Database Considerations
- Use transactions for atomic progress updates
- Index on user_id for performance
- Soft delete for data retention requirements

## Success Metrics
- Users can complete all 11 questions through chat interface
- Seamless mode transitions without UI confusion  
- Progressive saving prevents data loss
- All answers immediately available as AI context
- Clean edit functionality for answer updates
- Robust pause/resume across sessions

## Future Enhancements
- Question branching based on previous answers
- Analytics on completion rates and drop-off points
- Integration with user onboarding flows
- Export functionality for user data portability

## Code Review Findings & Fixes

### Critical Issues Fixed
1. **Skip Command Database Bug**: Fixed skip command to use actual database question ID instead of question number, preventing foreign key constraint violations
2. **State Variable Consistency**: Updated documentation to reflect actual implementation using `questionnaireActive` instead of `questionnaireMode`
3. **CSS Class Application**: Verified questionnaire-active CSS class is properly applied when questionnaire is active

### Data Migration Considerations
- Migration drops existing business profile tables with CASCADE 
- **IMPORTANT**: Will delete all existing user business profile data in production
- Consider data preservation strategy if migrating existing production system

### Input Validation
- API endpoints should validate user_id format (UUID) and question_id ranges (1-11)
- Consider adding rate limiting for questionnaire endpoints

### Database Schema Notes
- Uses TIMESTAMPTZ for proper timezone handling
- Includes proper foreign key constraints and cascading deletes
- Unique constraints prevent duplicate responses per user/question
- Automatic triggers update progress tracking

---

**Last Updated**: 2025-01-24
**Status**: Implementation complete, code review fixes applied
**Critical Issues**: All resolved
**Next Steps**: Testing and remaining feature development (edit form, resume nudges)