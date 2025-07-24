# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

### Backend (Python/FastAPI)
```bash
# Start local development server
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run the FastAPI server with proper environment
cd backend && python main.py

# Code formatting and linting
cd backend && black .
cd backend && flake8 .

# Install dependencies
cd backend && pip install -r requirements.txt
```

### Frontend (React)
```bash
# Start development server
cd frontend && npm start

# Build for production
cd frontend && npm run build

# Install dependencies
cd frontend && npm install
```

### Database (Neo4j)
```bash
# Start local Neo4j instance
docker compose up

# Access Neo4j Browser: http://localhost:7474
# Default credentials: neo4j/password123

# Import data to local database
cd backend && python import_data.py

# Import data to production (Neo4j Aura)
# Set environment variables first, then run import_data.py
```

### Full Development Setup
1. `./setup-hooks.sh` (install Git hooks for CI validation)
2. `docker compose up` (start Neo4j)
3. `cd backend && python main.py` (start API server)
4. `cd frontend && npm start` (start React app)
5. Access at http://localhost:3000

### Git Hooks
```bash
# Install development hooks (run once after cloning)
./setup-hooks.sh

# The pre-push hook will automatically check if CI workflow needs updating
# To bypass the hook if needed: git push --no-verify
```

## High-Level Architecture

### Core System
This is a **Neo4j-based knowledge graph system** that translates expert mental models into interactive, queryable networks. The system enables users to visualize and chat with an expert's knowledge using graph relationships and AI-powered conversations.

### Technology Stack
- **Database**: Neo4j (Community Edition locally, AuraDB in production)
- **Backend**: Python with FastAPI, serving as API gateway between frontend and database/LLM
- **Frontend**: React with Neo4j NVL visualization library for graph rendering
- **AI Services**: 
  - Anthropic Claude Sonnet 4 for conversational AI
  - Cohere embed-english-v3.0 for vector embeddings
- **User Memory**: Zep for automatic knowledge extraction and GraphRAG

### Data Flow Architecture
```
Expert Knowledge: Expert Interview → JSON Chunks → Themed Batches → Neo4j Graph → Vector Search
User Knowledge: User Conversations → Zep Memory → Knowledge Extraction → User Knowledge Graph
Combined Context: Expert Graph + User Graph → GraphRAG → Enhanced AI Response
```

**Expert Knowledge Pipeline**:
1. **Data Preparation**: Raw interview data is chunked into JSON files
2. **Thematic Enrichment**: Manual LLM collaboration assigns themes to data batches
3. **Graph Import**: `import_data.py` creates Entity/Theme nodes with vector embeddings
4. **Semantic Search**: User queries trigger vector similarity search in Neo4j

**User Knowledge Pipeline** (NEW):
1. **Conversation Capture**: User messages automatically sent to Zep
2. **Knowledge Extraction**: Zep extracts facts, entities, and business context
3. **Memory Storage**: User-specific knowledge graph built over time
4. **Context Retrieval**: Relevant user context retrieved for personalized responses

**GraphRAG Integration**:
5. **Dual Context**: Claude receives both expert knowledge and user-specific context
6. **Personalized Response**: AI generates responses using combined expert + personal knowledge

### Graph Schema
**Node Types**:
- `:Entity` (with specific labels: `:Principle`, `:Pattern`, `:Example`)
- `:Theme` (high-level categorizations)

**Key Properties**:
- `id`: Unique identifier for entities
- `description`/`content`: Text content used for embeddings
- `theme`: Categorical grouping
- `embedding`: 1024-dim vector from Cohere

**Relationships**:
- `(Entity)-[:BELONGS_TO]->(Theme)`
- `(Entity)-[:INFLUENCES|SUPPORTS|CONTRADICTS|DEMONSTRATES|PART_OF|USES|LEADS_TO]->(Entity)`

### Key Architecture Decisions
1. **Vector-First Search**: Uses semantic embeddings rather than keyword matching
2. **Streaming Chat**: Supports both sync and async chat responses via SSE
3. **Context Management**: Separates graph-wide search from explicit node-focused chat
4. **Cloud-Ready Design**: Includes keep-warm services for Neo4j Aura hibernation prevention
5. **Modular Backend**: Clear separation between config, data processing, AI, and API layers

## Development Workflow Patterns

### Adding New Data
1. Place JSON files in `data/themed_json/`
2. Run `cd backend && python import_data.py`
3. The import is idempotent - skips existing nodes with embeddings

### Modifying AI Behavior
- Edit `backend/prompts.py` to change the AI persona/system prompt
- Restart backend server to apply changes
- No database changes needed

### Frontend Component Structure
```
App.js (main orchestrator)
├── GraphView.js (Neo4j NVL visualization)
├── ChatPanel.js (AI conversation interface) 
├── NodeDetailsPanel.js (selected node info)
└── NodeTypesPanel.js (filtering controls)
```

### API Endpoints

**Core Endpoints**:
- `GET /health` - Database connectivity check
- `GET /api/graph` - Returns entire expert graph structure (nodes + edges)
- `POST /api/chat` - Enhanced chat with expert + user context (now includes user_id, session_id)
- `POST /api/chat/stream` - Server-sent events for streaming responses

**Chat Persistence** (existing):
- `POST /api/chat/sessions` - Create new chat session
- `GET /api/chat/sessions/{user_id}` - Get user's chat sessions
- `POST /api/chat/messages` - Add message (now auto-stores in Zep)
- `GET /api/chat/search` - Search across user's messages

**Zep Knowledge Graph** (NEW):
- `POST /api/user/business-data` - Add structured business data to user's knowledge graph
- `GET /api/user/{user_id}/knowledge-graph` - Get user's personal knowledge graph
- `GET /api/user/{user_id}/memory/{session_id}` - Get relevant memory context for session
- `DELETE /api/user/{user_id}/data` - Delete user's Zep data (privacy compliance)

## Environment Configuration

### Required Environment Variables
```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687  # or neo4j+s://... for Aura
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# AI Services
ANTHROPIC_API_KEY=sk-ant-api03-...
COHERE_API_KEY=...

# Zep Memory & Knowledge Graph
ZEP_API_KEY=your-zep-api-key
ZEP_API_URL=https://api.getzep.com  # or http://localhost:8000 for self-hosted
```

### Production Deployment Notes
- **Backend**: Deploy to Railway with nixpacks.toml configuration
- **Frontend**: Deploy to Vercel with REACT_APP_API_URL pointing to backend
- **Database**: Use Neo4j AuraDB with automated keep-warm service
- **CORS**: Configure proper origins in production (currently allows all)

## Testing Strategy
- **Manual Testing**: Use `/health` endpoint to verify database connectivity
- **Graph Queries**: Test in Neo4j Browser at http://localhost:7474
- **API Testing**: Use the frontend chat interface or tools like Postman
- **Vector Search**: Verify similarity search returns relevant nodes

## Performance Considerations
- Vector index enables sub-200ms semantic search on large graphs
- Conversation history limited to 15 messages to manage token usage
- Prompt caching reduces Claude API costs for repeated system prompts
- Keep-warm service prevents cold starts in cloud environments