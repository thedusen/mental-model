# Supabase Production Setup Documentation

## Overview

This document outlines the complete setup and management process for the Supabase production cloud instance. The system provides authentication, user management, chat persistence, and business profile functionality through Supabase's managed PostgreSQL and authentication services.

## System Architecture

### Components

1. **Supabase Cloud** - Production PostgreSQL database with authentication
2. **Python Supabase Client** - Backend integration via `supabase-py`
3. **React Supabase Client** - Frontend authentication and data access
4. **Supabase CLI** - Development and deployment tools
5. **Environment Configuration** - Multi-environment variable management

### Key Features

- **Scalable**: Cloud-hosted PostgreSQL with automatic scaling
- **Secure**: Built-in Row Level Security (RLS) and authentication
- **Real-time**: WebSocket connections for live updates
- **Flexible**: Supports both local development and production deployment
- **Integrated**: Seamless auth, database, and storage in one platform

## Quick Start

### Prerequisites

1. **Supabase Account**: Create account at [supabase.com](https://supabase.com)
2. **Project Setup**: Production project created with credentials
3. **Environment Variables**: Configured in all relevant `.env` files
4. **Dependencies**: Python and Node.js packages installed

### Production Configuration

#### Environment Variables

**Root `.env` file:**
```bash
# Supabase Production Configuration
SUPABASE_URL=https://ehqssdhhekqyzqkvormf.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:UPD_qnj.fda!npe3ghy@db.ehqssdhhekqyzqkvormf.supabase.co:5432/postgres

# Frontend Supabase Config
REACT_APP_SUPABASE_URL=https://ehqssdhhekqyzqkvormf.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Backend `.env` file:**
```bash
# Supabase Production Configuration
SUPABASE_URL=https://ehqssdhhekqyzqkvormf.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:UPD_qnj.fda!npe3ghy@db.ehqssdhhekqyzqkvormf.supabase.co:5432/postgres
```

**Frontend `.env.local` file:**
```bash
REACT_APP_SUPABASE_URL=https://ehqssdhhekqyzqkvormf.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Detailed Setup

### 1. Supabase CLI Installation and Configuration

```bash
# Install via Homebrew (recommended)
brew install supabase/tap/supabase

# Verify installation
supabase --version

# Login to Supabase
supabase login

# Link to project (optional, for schema migrations)
supabase link --project-ref ehqssdhhekqyzqkvormf
```

### 2. Backend Python Integration

#### Supabase Client Configuration

The backend uses the official `supabase-py` library (already installed in `requirements.txt`):

```python
# backend/supabase_client.py
import os
from supabase import create_client, Client

# Environment-based configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", 
                                os.getenv("SUPABASE_ANON_KEY"))

# Initialize client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
```

#### Service Layer Integration

```python
# Example usage in FastAPI endpoints
from backend.supabase_client import supabase_service

@app.post("/api/chat/sessions")
async def create_chat_session(user_id: str, title: str = None):
    session = await supabase_service.create_chat_session(user_id, title)
    return session

@app.get("/api/chat/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    sessions = await supabase_service.get_user_sessions(user_id)
    return sessions
```

### 3. Frontend React Integration

#### Supabase Client Setup

```javascript
// frontend/src/utils/supabase.js
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
});
```

#### Authentication Integration

```javascript
// Example authentication usage
import { auth } from '../utils/supabase';

// Sign up
const { data, error } = await auth.signUp(email, password, {
  full_name: fullName
});

// Sign in
const { data, error } = await auth.signIn(email, password);

// Get current user
const user = await auth.getUser();
```

## Database Schema Management

### Core Tables

#### User Authentication
- **Users**: Managed automatically by Supabase Auth
- **User Profiles**: Extended user information

```sql
-- User profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Chat System
- **Chat Sessions**: User conversation containers
- **Chat Messages**: Individual messages within sessions

```sql
-- Chat sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id),
    role TEXT NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

#### Business Profile System
- **Business Profile Questions**: Dynamic questionnaire system
- **User Business Profiles**: User responses to questions
- **User Questionnaire Progress**: Tracking completion status

```sql
-- Business profile questions
CREATE TABLE business_profile_questions (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    question_type TEXT DEFAULT 'text',
    order_index INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User business profiles (answers)
CREATE TABLE user_business_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    question_id INTEGER REFERENCES business_profile_questions(id),
    answer TEXT,
    answered_at TIMESTAMPTZ,
    session_id UUID,
    is_complete BOOLEAN DEFAULT FALSE,
    synced_to_zep BOOLEAN DEFAULT FALSE,
    zep_sync_at TIMESTAMPTZ,
    UNIQUE(user_id, question_id)
);

-- User questionnaire progress
CREATE TABLE user_questionnaire_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    nudge_dismissed_count INTEGER DEFAULT 0,
    last_nudged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Row Level Security (RLS)

```sql
-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_questionnaire_progress ENABLE ROW LEVEL SECURITY;

-- Users can only access their own data
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users can access own sessions" ON chat_sessions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own messages" ON chat_messages
    FOR ALL USING (auth.uid() IN (
        SELECT user_id FROM chat_sessions WHERE id = session_id
    ));

CREATE POLICY "Users can access own business profile" ON user_business_profiles
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own progress" ON user_questionnaire_progress
    FOR ALL USING (auth.uid() = user_id);
```

## Development Workflow

### Local vs Production Setup

#### Local Development (Optional)
```bash
# Start local Supabase
docker compose up

# Use local environment variables
SUPABASE_URL=http://localhost:54321
REACT_APP_SUPABASE_URL=http://localhost:54321
```

#### Production Development (Current)
```bash
# Use production environment variables (already configured)
SUPABASE_URL=https://ehqssdhhekqyzqkvormf.supabase.co
REACT_APP_SUPABASE_URL=https://ehqssdhhekqyzqkvormf.supabase.co
```

### Schema Migrations

#### Using Supabase CLI
```bash
# Create new migration
supabase migration new add_new_feature

# Apply migrations to production
supabase db push

# Pull production schema to local
supabase db pull
```

#### Direct SQL Execution
```bash
# Connect to production database
psql "postgresql://postgres:UPD_qnj.fda!npe3ghy@db.ehqssdhhekqyzqkvormf.supabase.co:5432/postgres"

# Or use Supabase SQL Editor in dashboard
```

## API Integration Patterns

### Backend Service Layer

#### Chat Operations
```python
# Create chat session
session = await supabase_service.create_chat_session(
    user_id="123e4567-e89b-12d3-a456-426614174000",
    title="New conversation"
)

# Add message
message = await supabase_service.add_message(
    session_id=session["id"],
    role="user",
    content="Hello, I need help with...",
    metadata={"source": "web"}
)

# Get session history
messages = await supabase_service.get_session_messages(session["id"])
```

#### Business Profile Operations
```python
# Get questionnaire progress
progress = await supabase_service.get_business_profile_progress(user_id)

# Save answer
answer = await supabase_service.save_business_profile_answer(
    user_id=user_id,
    question_id=1,
    answer="I run a SaaS business",
    session_id=session_id
)

# Mark as synced to Zep
await supabase_service.mark_answers_synced_to_zep(user_id)
```

### Frontend Integration

#### Authentication Flow
```javascript
// Sign up new user
const handleSignUp = async (email, password, fullName) => {
    try {
        const result = await auth.signUp(email, password, { full_name: fullName });
        if (result.error) throw result.error;
        
        if (result.data?.user && !result.data.user.email_confirmed_at) {
            setError('Please check your email and click the confirmation link.');
        } else {
            onAuthSuccess(result.data.user);
        }
    } catch (err) {
        setError(err.message);
    }
};
```

#### Data Operations
```javascript
// Create chat session
const createSession = async (title) => {
    const user = await auth.getUser();
    if (!user) throw new Error('User not authenticated');

    const { data, error } = await supabase
        .from('chat_sessions')
        .insert({ user_id: user.id, title })
        .select()
        .single();

    return { data, error };
};
```

## Security Configuration

### Authentication Settings

#### Email Authentication
- **Email confirmation**: Required for new accounts
- **Password requirements**: Minimum 6 characters
- **Session management**: Automatic refresh tokens

#### OAuth Providers (Optional)
```javascript
// Google OAuth
const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
        redirectTo: `${window.location.origin}/auth/callback`
    }
});
```

### Database Security

#### Row Level Security (RLS)
- **Enabled**: All user data tables have RLS policies
- **User isolation**: Users can only access their own data
- **Admin access**: Service role can bypass RLS for admin operations

#### API Key Security
- **Anonymous key**: Safe for frontend use (RLS protection)
- **Service role key**: Backend only, bypasses RLS
- **Environment variables**: All keys stored securely

## Monitoring and Maintenance

### Dashboard Access
- **Supabase Dashboard**: [https://supabase.com/dashboard](https://supabase.com/dashboard)
- **Project URL**: https://supabase.com/dashboard/project/ehqssdhhekqyzqkvormf

### Key Metrics to Monitor
1. **Database Usage**: Connection count, query performance
2. **Authentication**: Sign-up rates, active users
3. **Storage**: Database size, backup status
4. **API Usage**: Request volume, error rates

### Backup and Recovery
- **Automatic Backups**: Daily backups included with Supabase Pro
- **Point-in-time Recovery**: Available through dashboard
- **Export Options**: SQL dump, CSV export available

## Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Test backend connection
python -c "
from backend.supabase_client import get_supabase_client
client = get_supabase_client()
print('✅ Backend connection successful')
"

# Test frontend connection
# Check browser console for Supabase connection errors
```

#### Authentication Issues
```javascript
// Debug authentication state
console.log('Supabase URL:', process.env.REACT_APP_SUPABASE_URL);
console.log('Current user:', await supabase.auth.getUser());
console.log('Session:', await supabase.auth.getSession());
```

#### Environment Variable Issues
```bash
# Verify environment variables are loaded
node -e "console.log({
    url: process.env.REACT_APP_SUPABASE_URL,
    key: process.env.REACT_APP_SUPABASE_ANON_KEY?.substring(0, 20) + '...'
})"
```

### Error Recovery

#### Database Connection Issues
1. **Verify credentials**: Check environment variables
2. **Network connectivity**: Test from different network
3. **Supabase status**: Check [status.supabase.com](https://status.supabase.com)

#### Authentication Failures
1. **Email confirmation**: Check if email verification required
2. **Password policy**: Ensure meets minimum requirements
3. **RLS policies**: Verify policies allow user access

## Performance Optimization

### Database Optimization
- **Indexes**: Created automatically for foreign keys
- **Connection pooling**: Built into Supabase
- **Query optimization**: Use `.select()` to limit returned columns

### Frontend Optimization
- **Session persistence**: Enabled for better UX
- **Token refresh**: Automatic token refresh configured
- **Error handling**: Graceful degradation for offline scenarios

## Integration with Existing Systems

### Neo4j Integration
- **Separate concerns**: Supabase for users/auth, Neo4j for knowledge graph
- **Data flow**: User context from Supabase feeds into Neo4j queries
- **Relationship**: User ID links data between systems

### Zep Memory Integration
- **User linking**: Supabase user ID used as Zep user identifier
- **Data sync**: Business profile answers synced to Zep
- **Memory context**: Retrieved and combined with expert knowledge

## Best Practices

### Development
1. **Environment separation**: Use different projects for dev/staging/prod
2. **Schema versioning**: Use migrations for schema changes
3. **RLS testing**: Test policies thoroughly before production
4. **Error handling**: Implement comprehensive error handling

### Security
1. **Key management**: Never commit keys to version control
2. **RLS policies**: Always enable and test RLS policies
3. **Input validation**: Validate all user inputs
4. **CORS settings**: Configure appropriate CORS origins

### Performance
1. **Query optimization**: Use indexes and limit result sets
2. **Connection management**: Reuse connections where possible
3. **Caching**: Implement appropriate caching strategies
4. **Monitoring**: Monitor query performance and optimize as needed

## Support Resources

### Documentation
- **Supabase Docs**: [https://supabase.com/docs](https://supabase.com/docs)
- **Python Client**: [https://supabase.com/docs/reference/python](https://supabase.com/docs/reference/python)
- **JavaScript Client**: [https://supabase.com/docs/reference/javascript](https://supabase.com/docs/reference/javascript)

### Community
- **Discord**: [https://discord.supabase.com](https://discord.supabase.com)
- **GitHub**: [https://github.com/supabase/supabase](https://github.com/supabase/supabase)
- **Community Forum**: [https://github.com/supabase/supabase/discussions](https://github.com/supabase/supabase/discussions)

### Project Specific
1. **Environment files**: Check `.env`, `backend/.env`, `frontend/.env.local`
2. **Supabase client**: Review `backend/supabase_client.py`
3. **Frontend auth**: Check `frontend/src/utils/supabase.js`
4. **Database schema**: Use Supabase SQL Editor for schema management

---

*Last updated: July 23, 2025*
*Supabase setup version: 1.0*
*Project reference: ehqssdhhekqyzqkvormf*