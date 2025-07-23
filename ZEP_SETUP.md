# Zep Integration Setup Guide

This guide walks through setting up Zep for automatic knowledge extraction and GraphRAG integration in the Mental Model application.

## Overview

Zep is now integrated to automatically extract business knowledge from user conversations, creating personalized knowledge graphs that enhance AI responses with relevant user context.

## Environment Setup

### 1. Zep Cloud Setup (Recommended)

1. **Sign up for Zep Cloud**
   - Go to [https://www.getzep.com](https://www.getzep.com)
   - Create an account and get your API key

2. **Add Environment Variables**
   Add these to your `.env` file in the backend directory:
   ```bash
   # Zep Configuration
   ZEP_API_KEY=your_zep_api_key_here
   ZEP_API_URL=https://api.getzep.com
   ```

### 2. Self-Hosted Zep (Alternative)

If you prefer self-hosting:

1. **Docker Setup**
   ```bash
   # Clone Zep repository
   git clone https://github.com/getzep/zep.git
   cd zep
   
   # Start Zep services
   docker-compose up -d
   ```

2. **Environment Variables**
   ```bash
   # Zep Configuration (Self-hosted)
   ZEP_API_KEY=your_self_hosted_api_key
   ZEP_API_URL=http://localhost:8000
   ```

## Backend Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

The `zep-python==2.0.0` package is already included in requirements.txt.

### 2. Verify Installation

Start the backend server:
```bash
cd backend
python main.py
```

Check logs for Zep initialization:
```
INFO: Zep client initialized successfully
INFO: Mental Model API starting up...
```

## How It Works

### Automatic Knowledge Extraction

1. **Conversation Storage**: Every chat message is automatically sent to Zep for knowledge extraction
2. **Business Context**: Zep extracts facts, entities, and relationships from conversations
3. **Temporal Memory**: Facts are tracked with validity date ranges
4. **GraphRAG Integration**: Relevant user context is retrieved for AI responses

### Data Flow

```
User Message → Supabase (persistence) → Zep (knowledge extraction)
     ↓                                          ↓
AI Response ← GraphRAG Context ← User Knowledge Graph
```

## API Endpoints

### New Zep-Enabled Endpoints

1. **Enhanced Chat with User Context**
   ```
   POST /api/chat
   {
     "question": "How can I improve my business?",
     "user_id": "user-123",
     "session_id": "session-456",
     "conversation_history": [...]
   }
   ```

2. **Add Business Data**
   ```
   POST /api/user/business-data
   {
     "user_id": "user-123",
     "data": {
       "company": "Tech Startup",
       "industry": "SaaS",
       "challenge": "User acquisition"
     }
   }
   ```

3. **Get User Knowledge Graph**
   ```
   GET /api/user/{user_id}/knowledge-graph
   ```

4. **Get Session Memory Context**
   ```
   GET /api/user/{user_id}/memory/{session_id}?query=optional_search
   ```

## Frontend Integration

### Updated Chat Component

The chat interface now automatically:
- Sends user_id and session_id with chat requests
- Receives enhanced responses with user context
- Displays both expert and personal knowledge context

### Required Changes

Update your chat request to include user information:

```javascript
const chatRequest = {
  question: userInput,
  user_id: user.id,
  session_id: currentSession.id,
  conversation_history: messages,
  chat_context_node: selectedNode
};
```

## Data Privacy

### User Data Control

Users can delete their Zep data:
```
DELETE /api/user/{user_id}/data
```

### Data Retention

- Conversations are stored in both Supabase (for UI) and Zep (for knowledge extraction)
- Zep automatically manages fact validity and temporal relationships
- Business data can be updated/deleted as needed

## Testing

### 1. Basic Functionality Test

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test chat with user context
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are my business challenges?",
    "user_id": "test-user",
    "session_id": "test-session"
  }'
```

### 2. Business Data Test

```bash
# Add business context
curl -X POST http://localhost:8000/api/user/business-data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "data": {
      "company": "My Startup",
      "challenge": "Finding product-market fit"
    }
  }'
```

## Troubleshooting

### Common Issues

1. **Zep API Key Error**
   ```
   ValueError: ZEP_API_KEY environment variable not set
   ```
   Solution: Ensure ZEP_API_KEY is set in your .env file

2. **Connection Error**
   ```
   Failed to retrieve user memory from Zep: Connection timeout
   ```
   Solution: Check ZEP_API_URL and network connectivity

3. **Missing User Context**
   - Ensure user_id and session_id are passed in chat requests
   - Check that messages are being stored in Zep (check logs)

### Debug Mode

Enable detailed Zep logging:
```python
import logging
logging.getLogger('zep_python').setLevel(logging.DEBUG)
```

## Production Considerations

### Performance
- Zep operations are asynchronous and won't block chat responses
- Failed Zep operations are logged but don't break the chat flow
- Consider implementing retry logic for critical Zep operations

### Scaling
- Zep Cloud automatically scales with your usage
- Self-hosted Zep may need resource planning for large user bases
- Monitor Zep API rate limits and usage

### Security
- Zep API keys should be stored securely
- Consider implementing user consent for knowledge extraction
- Regular data audits and cleanup policies

## Next Steps

1. **Phase 2**: Enhanced knowledge extraction configuration
2. **Phase 3**: Knowledge graph visualization in frontend
3. **Phase 4**: Business intelligence and insights features

## Support

- **Zep Documentation**: [https://docs.getzep.com](https://docs.getzep.com)
- **Python SDK**: [https://github.com/getzep/zep-python](https://github.com/getzep/zep-python)
- **Community**: [Zep Discord](https://discord.gg/zep)