# Debug: Zep User Creation Issues

## Problem Statement

Users are not being created in Zep when they chat directly after registration (bypassing the business profile questionnaire). This prevents the chat-only user flow from working properly.

## Expected Behavior

When a user registers and immediately starts chatting without completing the business profile questionnaire, they should:
1. Be able to create chat sessions successfully
2. Have their messages sent to the backend
3. Be automatically created in Zep during the first chat interaction
4. Receive AI responses with their context being tracked

## Current Behavior

1. User registers successfully
2. User tries to chat directly after registration
3. Session creation fails with 500 errors or timeouts
4. No Zep user is created
5. Chat functionality is broken

## Error Patterns Observed

### Registration Phase
```
https://mental-model-backend.up.railway.app/api/business-profile/progress/1dd10bdd-dd3a-472f-b657-16a3aad61e58 500 (Internal Server Error)
```

### Chat Attempt Phase
```
ChatHistory.js:96 ❌ Error loading sessions: Error: Request timeout
ChatPanel.js:1001 ❌ No current session available for chat request
ChatPanel.js:1083 Error with streaming, attempting fallback: Error: Session not available. Please try again.
```

## Root Cause Analysis

The issue appears to be a cascading failure:
1. **Missing User Profiles**: Users registered through Supabase Auth don't automatically get `user_profiles` records
2. **Database Trigger Issues**: The expected `on_auth_user_created` trigger may not be firing consistently
3. **RLS Policy Violations**: Backend operations fail when user profiles don't exist due to Row Level Security
4. **Zep Integration Dependency**: Zep user creation depends on user profile metadata extraction

## Attempted Fixes (All Failed)

### Attempt 1: Backend Session Creation Fix (Commit: f50ff515)
**Date**: Initial conversation
**Approach**: Added fallback session creation logic in ChatPanel.js
**Changes**:
- Added temporary session creation when backend fails
- Added exponential backoff retry logic
- Added comprehensive error handling

**Result**: ❌ Failed - Still getting 500 errors and timeouts

### Attempt 2: User Profile Creation in Session Creation (Commit: d2679de7)
**Date**: Follow-up fix
**Approach**: Ensure user profiles exist before creating chat sessions
**Changes**:
- Modified `create_chat_session()` in `supabase_client.py` to create user profiles
- Added debug endpoint `/api/debug/supabase-connection`
- Added proper error handling

**Result**: ❌ Failed - UUID validation errors, still no Zep users created

### Attempt 3: Zep Metadata Extraction Fix (Commit: 0988853b)
**Date**: Latest attempt
**Approach**: Fix user profile creation in Zep integration layer
**Changes**:
- Modified `_extract_user_metadata_from_supabase()` in `zep_memory.py`
- Added automatic user profile creation when missing
- Removed duplicate profile creation logic from session creation
- Added UUID validation in debug endpoint

**Result**: ❌ Failed - User reports no Zep user creation still occurring

## Technical Issues Identified

### 1. UUID Format Validation
```python
# Error from production
{'message': 'invalid input syntax for type uuid: "test_user_debug_1753567742"', 'code': '22P02'}
```
The `user_profiles` table expects proper UUID format, but test strings were being used.

### 2. Database Trigger Dependencies
The system relies on database triggers that may not be working:
- `on_auth_user_created` trigger should create user profiles automatically
- This trigger appears to be missing or not firing consistently

### 3. RLS Policy Conflicts
Supabase Row Level Security policies prevent backend operations when user context is missing.

### 4. Session Creation Timeouts
Production backend experiencing timeouts during session creation, preventing the entire flow.

## Working State Reference

**User's Note**: "At a certain point, somewhere in the main repository, was a version of this code that worked. After signing up, [...] Only clicking 'Let's chat!' creates the user."

This suggests:
- There was a working implementation in git history
- The issue arose when trying to add name/email to Zep records
- The "Let's chat!" button flow works, but direct typing doesn't

## Current Status

### What Works
- User registration through Supabase Auth
- "Let's chat!" button flow (creates Zep users)
- Business profile questionnaire flow

### What Doesn't Work
- Direct chat after registration (chat-only flow)
- Automatic user profile creation
- Session creation without existing profiles

## Next Steps Needed

1. **Investigate Git History**
   - Find the last working commit before name/email changes
   - Identify what specific changes broke the working flow
   - Compare working "Let's chat!" flow vs. broken direct typing flow

2. **Database Investigation**
   - Check if `on_auth_user_created` trigger exists and is active
   - Verify RLS policies for `user_profiles` and `chat_sessions` tables
   - Test database operations with service key vs. user context

3. **Flow Comparison**
   - Analyze difference between working "Let's chat!" and broken direct chat
   - Identify why one creates Zep users and the other doesn't
   - Check if both flows hit the same backend endpoints

4. **Production Deployment Issues**
   - Investigate why Railway deployments seem to have stale code
   - Verify environment variables are correctly set
   - Check for any deployment pipeline issues

## Debug Commands for Investigation

```bash
# Test backend connectivity
curl https://mental-model-backend.up.railway.app/health

# Test debug endpoint
curl https://mental-model-backend.up.railway.app/api/debug/supabase-connection

# Check recent commits
git log --oneline -10

# Search for name/email changes in Zep
git log --grep="email" --grep="name" --oneline
```

## Files Involved

### Backend Files
- `/backend/main.py` - Main API endpoints
- `/backend/supabase_client.py` - Database operations
- `/backend/zep_memory.py` - Zep integration and user creation
- `/backend/config.py` - Configuration and client setup

### Frontend Files
- `/frontend/src/components/ChatPanel.js` - Chat interface and session management
- `/frontend/src/components/ChatHistory.js` - Session loading
- `/frontend/src/utils/supabase.js` - Frontend Supabase operations

### Key Endpoints
- `POST /api/chat/sessions` - Session creation
- `POST /api/chat` - Chat with Zep user creation
- `GET /api/business-profile/progress/{user_id}` - Profile progress (failing)
- `GET /api/debug/supabase-connection` - Debug connectivity

## Conclusion

Multiple surgical fixes have been attempted, but the core issue persists. The problem likely requires:
1. Understanding what changed when name/email was added to Zep
2. Restoring the working flow from git history
3. Ensuring proper database trigger setup
4. Fixing the discrepancy between "Let's chat!" and direct typing flows

The issue is not simply a code problem but appears to be a combination of database configuration, deployment timing, and flow logic that needs systematic investigation.