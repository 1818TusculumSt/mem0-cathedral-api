<div align="center">
  <img src="logo.png" alt="Mem0 Cathedral API Logo"/>
</div>

# Mem0 Cathedral API - The Silent Oracle

FastAPI wrapper for Mem0 Platform API with **AI-powered memory extraction**, **intelligent auto-recall**, and **silent operations** for Open WebUI.

## 🎯 What's New in v12.1.0 (The Silent Oracle)

Your FastAPI REST API is now a **production-ready memory powerhouse**:

- 🧠 **AI-Powered Extraction** - Mem0's native LLM extracts memories automatically from conversations
- 🔍 **Intelligent Auto-Recall** - Hybrid search with keyword reranking for perfect context injection
- 🤫 **Silent Operations** - Clean UX with minimal responses (no verbose clutter)
- 📊 **Graph Memory** - Entity relationship tracking for contextual recall
- 🏷️ **Custom Categories** - 12 predefined categories + custom support
- 🤖 **Multi-Agent Support** - Track memories per agent with session IDs
- ⚡ **Ultra-Simple Recall** - `GET /recall/{user_id}?q=message` for one-liner context retrieval
- 🔄 **Backward Compatible** - Legacy v11.x content-based mode still works

**FREE Mem0 API tier included. Zero LLM configuration required.**

---

## 🚀 Quick Start

### With Docker Compose (Recommended)
```bash
docker compose up -d
```

### Standalone Docker
```bash
docker build -t mem0-cathedral-api .
docker run -d \
  -p 8007:8000 \
  -e MEM0_API_KEY=your_mem0_api_key_here \
  --name mem0-proxy \
  mem0-cathedral-api
```

### Open WebUI Integration
1. Navigate to **Settings → Functions**
2. Add function: `http://your-server:8007/openapi.json`
3. AI-powered memory extraction + auto-recall now active!

---

## 🧠 Core Features

### 1. AI-Powered Memory Extraction

Send conversation messages, Mem0's AI extracts memories automatically.

**Before (Manual Extraction - Old Way):**
```json
POST /add_memory
{
  "content": "User prefers Python for data science",
  "user_id": "el-jefe-principal"
}
```

**After (AI Extraction - New Way):**
```json
POST /add_memory
{
  "messages": [
    {"role": "user", "content": "I love using Python for all my data science work"},
    {"role": "assistant", "content": "That's great! Python has excellent ML libraries."}
  ],
  "user_id": "el-jefe-principal",
  "infer": true
}
```

**What happens:** Mem0's LLM automatically extracts:
- `"User prefers Python for data science work"`
- Auto-categorizes as `technical` and `preferences`
- Stores with metadata, timestamps, and context

**Response (Silent Mode):**
```json
{
  "success": true
}
```

### 2. Intelligent Auto-Recall

Automatically inject relevant memories into conversation context.

**Option 1: Ultra-Simple (Recommended)**
```bash
GET /recall/el-jefe-principal?q=What should I eat for dinner?&limit=10
```

**Response:**
```json
{
  "context": "## User Context\n\n### Food Preferences\n- User loves Italian food, especially pizza\n- User is vegetarian\n- User avoids spicy food\n\n### Health\n- User has lactose intolerance\n",
  "count": 4
}
```

**Option 2: Full-Featured**
```json
POST /get_context
{
  "current_message": "What should I eat for dinner?",
  "recent_messages": [
    {"role": "user", "content": "I'm feeling hungry"},
    {"role": "assistant", "content": "What sounds good?"}
  ],
  "user_id": "el-jefe-principal",
  "max_memories": 10,
  "enable_graph": true
}
```

**How it works:**
1. Semantic search retrieves 3x candidates (30 for top 10)
2. Keyword reranking boosts by 15% per match
3. Returns top N formatted by category
4. Ready for LLM prompt injection

### 3. Silent Operations

All memory saves return minimal responses - no clutter in chat.

**Success:**
```json
{"success": true}
```

**Failure (quality/duplicate rejection):**
```json
{"success": false}
```

Quality issues and duplicates are **logged server-side only** - users never see rejection details.

### 4. Graph Memory & Relationships

Track entities and relationships automatically.

```json
POST /add_memory
{
  "messages": [
    {"role": "user", "content": "My colleague Sarah introduced me to React"}
  ],
  "enable_graph": true,
  "user_id": "el-jefe-principal"
}
```

**Extracted:**
- Memory: "User's colleague Sarah introduced them to React"
- Entities: Sarah (person), React (technology)
- Relationships: colleague_of, introduced_to

### 5. Custom Categories & Instructions

Use defaults or customize extraction behavior.

**Default Categories (12 built-in):**
- `personal_information` - Name, location, age, family
- `preferences` - Likes, dislikes, favorites
- `work` - Career, projects, professional info
- `food_preferences` - Dietary restrictions, favorites
- `technical` - Tech stack, tools, languages
- `goals` - Objectives, plans, aspirations
- `health` - Health conditions, fitness
- `hobbies` - Interests, activities
- `relationships` - Friends, family, colleagues
- `location` - Places lived/visited
- `schedule` - Routines, availability
- `communication` - Preferred styles

**Custom Example:**
```json
POST /add_memory
{
  "messages": [...],
  "custom_categories": {
    "gaming": "Video games, platforms, preferences",
    "music": "Music genres, artists, instruments"
  },
  "custom_instructions": "Focus on extracting gaming preferences and musical tastes",
  "user_id": "el-jefe-principal"
}
```

### 6. Multi-Agent & Session Tracking

Track memories per agent and conversation session.

```json
POST /add_memory
{
  "messages": [...],
  "user_id": "el-jefe-principal",
  "agent_id": "coding_assistant",
  "run_id": "session_2024_01_15_001"
}
```

**Search by agent:**
```json
POST /search_memories
{
  "query": "Python preferences",
  "user_id": "el-jefe-principal",
  "agent_id": "coding_assistant"
}
```

---

## 📚 Complete API Reference

### Memory Operations

#### Add Memory (AI Mode - Recommended)
```http
POST /add_memory
{
  "messages": [{"role": "user", "content": "..."}],
  "user_id": "el-jefe-principal",
  "agent_id": "optional",
  "run_id": "optional",
  "infer": true,
  "enable_graph": false,
  "metadata": {"key": "value"},
  "async_mode": true
}
```

**Response:** `{"success": true/false}`

#### Add Memory (Legacy Mode)
```http
POST /add_memory
{
  "content": "Pre-extracted memory text",
  "user_id": "el-jefe-principal",
  "force": false
}
```

#### Get Context (Auto-Recall - Full)
```http
POST /get_context
{
  "current_message": "What should I do?",
  "recent_messages": [...],
  "user_id": "el-jefe-principal",
  "max_memories": 10,
  "enable_graph": true
}
```

**Response:**
```json
{
  "context": "## User Context\n\n### Category\n- Memory 1\n- Memory 2\n",
  "memories": [...],
  "count": 10,
  "total_searched": 30
}
```

#### Recall (Ultra-Simple)
```http
GET /recall/{user_id}?q=current_message&limit=10&agent_id=optional
```

**Response:**
```json
{
  "context": "formatted context string",
  "count": 10
}
```

#### Search Memories
```http
POST /search_memories
{
  "query": "search text",
  "user_id": "el-jefe-principal",
  "agent_id": "optional",
  "run_id": "optional",
  "limit": 100,
  "categories": ["technical", "preferences"],
  "enable_graph": false
}
```

#### Get All Memories
```http
GET /get_all_memories/{user_id}
```

#### Get Specific Memory
```http
GET /get_memory/{memory_id}
```

#### Update Memory
```http
PUT /update_memory/{memory_id}
{
  "data": "new content"
}
```

#### Delete Memory
```http
DELETE /delete_memory/{memory_id}
```

#### Get Memory History
```http
GET /get_history/{memory_id}
```

#### Consolidate Memories (Legacy Feature)
```http
POST /consolidate_memories?user_id=el-jefe-principal&dry_run=true
```

### System Endpoints

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "at_peace",
  "version": "12.1.0",
  "mode": "silent_oracle",
  "features": {
    "auto_recall": true,
    "keyword_reranking": true,
    "silent_operations": true,
    "ai_extraction": true,
    "graph_memory": true,
    "multi_agent": true,
    "session_tracking": true,
    "async_processing": true,
    "legacy_mode": true,
    "quality_filtering": true,
    "deduplication": true,
    "consolidation": true
  },
  "new_endpoints": {
    "get_context": "POST /get_context",
    "recall": "GET /recall/{user_id}?q=message"
  },
  "response_format": {
    "add_memory": "Silent: {success: true/false}",
    "get_context": "Returns formatted context string + memories"
  }
}
```

### API Documentation
- **Swagger UI**: `http://localhost:8007/docs`
- **ReDoc**: `http://localhost:8007/redoc`
- **OpenAPI spec**: `http://localhost:8007/openapi.json`

---

## 🧪 Usage Examples

See [EXAMPLES.md](EXAMPLES.md) for 12 detailed examples including:
- Basic AI extraction
- Multi-category extraction
- Custom categories & instructions
- Graph memory relationships
- Multi-agent tracking
- Metadata filtering
- Legacy mode compatibility
- Python SDK usage

---

## ⚙️ Configuration

### Environment Variables

```bash
MEM0_API_KEY=your_mem0_api_key_here  # Required - get from https://app.mem0.ai/
```

### Quality Thresholds (Legacy Mode)

Customize in [main.py:21-24](main.py#L21-L24):

```python
MIN_MEMORY_LENGTH = 20      # Minimum characters (default: 20)
MIN_WORD_COUNT = 4          # Minimum words (default: 4)
SIMILARITY_THRESHOLD = 0.85 # Deduplication threshold (default: 0.85)
```

### Keyword Reranking

Adjust boost factor in `_rerank_by_keywords()`:

```python
def _rerank_by_keywords(memories: list, query: str, boost: float = 0.15):
    # Default: 15% boost per keyword match
    # Increase for stronger keyword influence: 0.20 or 0.25
    # Decrease for more semantic focus: 0.10 or 0.05
```

---

## 🏗️ Architecture

- **Base**: Python 3.11 slim
- **Framework**: FastAPI 0.115.4
- **Server**: Uvicorn with 2 workers (production)
- **HTTP Client**: httpx with HTTP/2 support
- **Validation**: Pydantic v2
- **Memory Provider**: Mem0 Platform API (cloud-based)

### Intelligence Pipeline

**AI Extraction Mode:**
```
User Messages → Mem0 LLM → Extracted Memories → Categories → Graph (optional) → Storage
```

**Auto-Recall Mode:**
```
User Query → Semantic Search (3x candidates) → Keyword Reranking (15% boost/match) → Top N → Format by Category → LLM Context
```

**Legacy Mode:**
```
Content → Quality Check → Deduplication → Enrichment → Storage
```

---

## 🔄 Version Comparison

| Feature | v11.0 | v12.0 | v12.1 |
|---------|-------|-------|-------|
| AI Extraction (Mem0 native) | ❌ | ✅ | ✅ |
| Auto-Recall Context | ❌ | ❌ | ✅ |
| Keyword Reranking | ❌ | ❌ | ✅ |
| Silent Operations | ❌ | ❌ | ✅ |
| Graph Memory | ❌ | ✅ | ✅ |
| Custom Categories | ❌ | ✅ | ✅ |
| Multi-Agent Tracking | ❌ | ✅ | ✅ |
| Session IDs | ❌ | ✅ | ✅ |
| Ultra-Simple Recall | ❌ | ❌ | ✅ |
| Quality Filtering (legacy) | ✅ | ✅ | ✅ |
| Deduplication (legacy) | ✅ | ✅ | ✅ |
| v2 Search API | ✅ | ✅ | ✅ |
| 100+ Search Results | ✅ | ✅ | ✅ |

---

## 🚀 Production Deployment

### Standard Workflow

```bash
# 1. Pull latest changes
git pull origin main

# 2. Rebuild container (no cache)
docker compose build --no-cache

# 3. Deploy
docker compose up -d

# 4. Verify health
curl http://localhost:8007/health
```

### Expected Health Response

```json
{
  "status": "at_peace",
  "version": "12.1.0",
  "mode": "silent_oracle",
  "features": {
    "auto_recall": true,
    "keyword_reranking": true,
    "silent_operations": true,
    "ai_extraction": true,
    "graph_memory": true
  }
}
```

---

## 🐛 Troubleshooting

### Server not starting
```bash
# Check if port 8007 is in use
docker ps

# View logs
docker logs mem0-proxy

# Restart
docker compose restart
```

### Dependencies not found
```bash
# Rebuild container
docker compose build --no-cache
docker compose up -d
```

### Mem0 API Errors

**400 Bad Request:**
- Usually means invalid payload
- Check logs: `docker logs mem0-proxy`
- Verify `MEM0_API_KEY` is set correctly

**401 Unauthorized:**
- Invalid API key
- Get fresh key from https://app.mem0.ai/

**429 Rate Limited:**
- Exceeded free tier limits
- Wait or upgrade Mem0 plan

### Auto-Recall Not Finding Memories

**Increase candidate pool:**
```python
# In get_context endpoint
retrieve_limit = min(data.max_memories * 5, 100)  # Was 3x, now 5x
```

**Adjust reranking boost:**
```python
memories = _rerank_by_keywords(memories, data.current_message, boost=0.20)  # Was 0.15
```

### LLM Showing Function Call Citations

**Fixed in v12.1.0** - If you still see citations:
1. Verify you're running v12.1.0: `curl http://localhost:8007/health`
2. Check Open WebUI function settings
3. Ensure OpenAPI spec is up-to-date

---

## 📊 Performance

- **Workers**: 2 (for production throughput)
- **Request timeout**: 60s (connect: 10s)
- **HTTP/2**: Enabled for Mem0 API calls
- **Connection pooling**: Via httpx AsyncClient
- **Health check**: Every 30s with 40s startup grace
- **Async Processing**: Background memory extraction (default on)

---

## 🔐 Security Notes

- Never commit `MEM0_API_KEY` to version control
- Use environment variables for secrets
- CORS enabled for Open WebUI (adjust for production if needed)
- Quality filtering prevents spam/junk memories (legacy mode)
- Silent operations prevent information leakage in chat

---

## 💡 Tips for Open WebUI

### Recommended Configuration

**Use AI extraction mode:**
```json
{
  "messages": [...],
  "infer": true,
  "enable_graph": true,
  "async_mode": true
}
```

**Enable auto-recall at conversation start:**
```
GET /recall/el-jefe-principal?q={current_user_message}&limit=10
```

**Let silent operations work:**
- Don't expect verbose confirmation messages
- Check server logs for quality/duplicate rejections
- Use `{"success": true}` as signal for UI updates

### Best Practices

1. **AI extraction > Manual extraction** - Better quality, less work
2. **Enable graph memory** - Richer context for relationships
3. **Use auto-recall** - Inject context automatically
4. **Trust silent operations** - Clean UX is worth it
5. **Monitor server logs** - See what's being filtered

---

## 📧 Support & Resources

- **Issues**: [GitHub Issues](https://github.com/1818TusculumSt/mem0-cathedral-api/issues)
- **Mem0 Docs**: https://docs.mem0.ai
- **Open WebUI**: https://github.com/open-webui/open-webui
- **MCP Version**: [mem0-cathedral-mcp](https://github.com/1818TusculumSt/mem0-cathedral-mcp)

---

## 🎯 Version History

### 12.1.0 (The Silent Oracle) - **Current**
- ✅ Intelligent auto-recall with keyword reranking
- ✅ Ultra-simple `/recall` endpoint
- ✅ Silent operations (`{success: true/false}`)
- ✅ No function call citations in LLM responses
- ✅ Hybrid search (semantic + lexical)
- ✅ Context formatting by category

### 12.0.0 (The AI-Powered One)
- ✅ AI-powered extraction via Mem0 native API
- ✅ Custom categories (12 defaults)
- ✅ Custom extraction instructions
- ✅ Graph memory support
- ✅ Multi-agent tracking
- ✅ Session IDs (run_id)
- ✅ Structured metadata
- ✅ Category filtering in search
- ✅ Async processing mode

### 11.0.0 (The Intelligent One)
- ✅ Quality filtering with configurable thresholds
- ✅ Smart deduplication before saving
- ✅ Automatic context enrichment
- ✅ Memory consolidation endpoint

### 10.0.0 (The Enlightened One)
- ✅ Upgraded to Mem0 v2 API
- ✅ 100+ search results support

### 9.0.0 and earlier
- Basic Mem0 v1 API wrapper

---

## 🤝 Credits

- **Built by**: El Jefe Principal 🧠
- **Powered by**: [Mem0 Platform API](https://mem0.ai)
- **Designed for**: [Open WebUI](https://github.com/open-webui/open-webui)
- **Sister Project**: [mem0-cathedral-mcp](https://github.com/1818TusculumSt/mem0-cathedral-mcp)

---

## 📝 License

Built for the network. Use wisely. 🏗️

---

## 🌟 Why Cathedral API?

**vs SmartMemory API:**
- ✅ **FREE** - Mem0 API is free for minimal usage
- ✅ **Lightweight** - 100MB vs 4GB Docker image
- ✅ **Zero Config** - No LLM setup required
- ✅ **Cloud-Based** - No local inference overhead
- ✅ **Production Ready** - Silent, fast, reliable

**vs Manual Memory Management:**
- ✅ **AI Extraction** - No manual memory writing
- ✅ **Auto-Recall** - Automatic context injection
- ✅ **Graph Memory** - Relationship tracking
- ✅ **Silent Operations** - Clean UX

**Perfect For:**
- Open WebUI deployments
- Personal AI assistants
- Multi-agent systems
- Session-based conversations
- Relationship-aware context

---

Happy memory management! 🧠✨
