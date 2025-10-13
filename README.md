<div align="center">
  <img src="logo.png" alt="Mem0 Cathedral API Logo"/>
</div>

# Mem0 Cathedral API - Intelligent Edition

FastAPI wrapper for Mem0 API with **MCP-inspired intelligence**: quality filtering, smart deduplication, and context enrichment for Open WebUI.

## 🎯 What's New in v11.0

Your existing FastAPI REST API now has **ALL the intelligence features** from [mem0-cathedral-mcp](https://github.com/1818TusculumSt/mem0-cathedral-mcp):

- ✅ **Quality Filtering** - Rejects trivial acknowledgments and low-value content
- ✅ **Smart Deduplication** - Prevents saving similar/duplicate memories
- ✅ **Context Enrichment** - Automatically adds timestamps and clarifying context
- ✅ **Memory Consolidation** - New endpoint to find and merge redundant memories

**Same REST API for Open WebUI. Now with intelligent memory management.**

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
3. Intelligent memory operations now available in chats!

---

## 🎨 Intelligence Features

### 1. Quality Filtering

Every memory is scored before saving:

**Scoring Criteria:**
- ✅ **Length**: Minimum 20 characters
- ✅ **Word Count**: Minimum 4 words
- ✅ **Content Value**: Rejects "ok", "thanks", simple acknowledgments
- ✅ **Context Indicators**: Bonus for preferences, goals, technical details

**Example:**
```json
// ❌ REJECTED
POST /add_memory
{"content": "ok", "user_id": "el-jefe-principal"}

Response:
{
  "ok": false,
  "rejected": true,
  "reason": "Quality threshold not met",
  "issues": [
    "Too short (min 20 chars)",
    "Too few words (min 4 words)",
    "Low-value acknowledgment"
  ],
  "suggestion": "Provide more context or use 'force: true' to override"
}

// ✅ SAVED
POST /add_memory
{"content": "User prefers TypeScript over JavaScript for type safety", "user_id": "el-jefe-principal"}

Response:
{
  "ok": true,
  "memory_id": "mem_abc123",
  "quality_score": 120,
  "message": "Memory saved successfully"
}
```

### 2. Smart Deduplication

Automatically checks for similar memories before saving (threshold: 0.85):

**Example:**
```json
// Attempt to save duplicate
POST /add_memory
{"content": "User likes Python for data science", "user_id": "el-jefe-principal"}

// If similar memory exists...
Response:
{
  "ok": false,
  "duplicate": true,
  "existing_memory_id": "mem_xyz789",
  "existing_content": "User prefers Python for ML work",
  "similarity": 0.87,
  "suggestion": "Use update_memory to modify existing memory instead"
}
```

### 3. Context Enrichment

Memories are automatically enhanced with:
- Timestamp metadata
- Clarifying prefixes (e.g., "User preference: ...")
- Self-contained structure

**Example:**
```
Input:  "prefers dark mode"
Stored: "User preference: prefers dark mode
         [Captured: 2024-01-15T10:30:00Z]"
```

### 4. Memory Consolidation (NEW!)

Identifies redundant memories for cleanup:

**Example:**
```bash
POST /consolidate_memories?user_id=el-jefe-principal&dry_run=true
```

**Response:**
```json
{
  "ok": true,
  "dry_run": true,
  "candidates": [
    {
      "memory1_id": "mem_123",
      "memory1_content": "User prefers Python",
      "memory2_id": "mem_456",
      "memory2_content": "User likes Python for data science",
      "similarity": 0.82
    }
  ],
  "count": 1,
  "message": "Review these candidates. Use update_memory and delete_memory to consolidate manually."
}
```

---

## 📚 API Endpoints

### Core Memory Operations

#### Add Memory (with Intelligence)
```http
POST /add_memory
{
  "content": "User prefers Python over JavaScript",
  "user_id": "el-jefe-principal",
  "force": false  // Optional: bypass quality checks
}
```

**Responses:**
- ✅ Success: `{ok: true, memory_id: "...", quality_score: 120}`
- ❌ Rejected: `{ok: false, rejected: true, issues: [...]}`
- ❌ Duplicate: `{ok: false, duplicate: true, existing_memory_id: "..."}`

#### Search Memories
```http
POST /search_memories
{
  "query": "programming preferences",
  "user_id": "el-jefe-principal",
  "limit": 100
}
```

#### Get All Memories (NEW!)
```http
GET /get_all_memories/el-jefe-principal
```

#### Consolidate Memories (NEW!)
```http
POST /consolidate_memories?user_id=el-jefe-principal&dry_run=true
```

#### Other Endpoints
- `GET /get_memory/{memory_id}` - Get specific memory
- `PUT /update_memory/{memory_id}` - Update memory
- `DELETE /delete_memory/{memory_id}` - Delete memory
- `GET /get_history/{memory_id}` - View modification history
- `GET /health` - Health check with feature flags

### API Documentation
- **Swagger UI**: `http://localhost:8007/docs`
- **ReDoc**: `http://localhost:8007/redoc`
- **OpenAPI spec**: `http://localhost:8007/openapi.json`

---

## ⚙️ Configuration

### Quality Thresholds

Customize in [main.py:22-24](main.py#L22-L24):

```python
MIN_MEMORY_LENGTH = 20      # Minimum characters (default: 20)
MIN_WORD_COUNT = 4          # Minimum words (default: 4)
SIMILARITY_THRESHOLD = 0.85 # Deduplication threshold (default: 0.85)
```

### Environment Variables

- `MEM0_API_KEY` (required) - Your Mem0 API key from https://app.mem0.ai/
- Default user ID: `el-jefe-principal`

### Quality Indicators

**Good indicators** (bonus points):
- Preferences: "prefer", "like", "love", "hate"
- Technical: "project", "tool", "language"
- Personal: "name is", "location", "timezone"
- Goals: "goal", "objective", "plan"

**Low-value patterns** (rejected):
- "ok", "okay", "got it", "understood"
- "sure", "thanks", "thank you"
- "yes", "no", "maybe", "alright"

---

## 🧪 Usage Examples

### Example 1: Quality Filtering

**Good Memory:**
```bash
curl -X POST http://localhost:8007/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers PostgreSQL over MySQL for complex queries and ACID compliance",
    "user_id": "el-jefe-principal"
  }'
```

**Response:**
```json
{
  "ok": true,
  "memory_id": "mem_abc123",
  "quality_score": 120,
  "message": "Memory saved successfully"
}
```

**Low-Quality Memory:**
```bash
curl -X POST http://localhost:8007/add_memory \
  -H "Content-Type: application/json" \
  -d '{"content": "ok", "user_id": "el-jefe-principal"}'
```

**Response:**
```json
{
  "ok": false,
  "rejected": true,
  "reason": "Quality threshold not met",
  "issues": [
    "Too short (min 20 chars)",
    "Too few words (min 4 words)",
    "Low-value acknowledgment"
  ],
  "suggestion": "Provide more context or use 'force: true' to override"
}
```

### Example 2: Force Save Override

```bash
curl -X POST http://localhost:8007/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ok",
    "user_id": "el-jefe-principal",
    "force": true
  }'
```

### Example 3: Deduplication

**Attempt to save duplicate:**
```bash
curl -X POST http://localhost:8007/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User likes Python for data science",
    "user_id": "el-jefe-principal"
  }'
```

**Response (if similar memory exists):**
```json
{
  "ok": false,
  "duplicate": true,
  "existing_memory_id": "mem_xyz789",
  "existing_content": "User prefers Python for ML work",
  "similarity": 0.87,
  "suggestion": "Use update_memory to modify existing memory instead"
}
```

### Example 4: Consolidation

```bash
curl -X POST "http://localhost:8007/consolidate_memories?user_id=el-jefe-principal&dry_run=true"
```

**Response:**
```json
{
  "ok": true,
  "dry_run": true,
  "candidates": [
    {
      "memory1_id": "mem_123",
      "memory1_content": "User prefers Python",
      "memory2_id": "mem_456",
      "memory2_content": "User likes Python for data science",
      "similarity": 0.82
    }
  ],
  "count": 1,
  "message": "Review these candidates. Use update_memory and delete_memory to consolidate manually."
}
```

---

## 🏗️ Architecture

- **Base**: Python 3.11 slim
- **Framework**: FastAPI 0.115.4
- **Server**: Uvicorn with 2 workers (production)
- **HTTP Client**: httpx with HTTP/2 support
- **Validation**: Pydantic v2
- **Features**: Quality filtering, deduplication, enrichment, consolidation

### Intelligence Features (NEW in v11.0)
- Quality assessment before saving
- Semantic similarity detection
- Automatic context enrichment
- Memory consolidation endpoint

---

## 🔄 Version Comparison

| Feature | v10.0 (Before) | v11.0 (After) |
|---------|----------------|---------------|
| Quality Filtering | ❌ | ✅ |
| Deduplication | ❌ | ✅ |
| Context Enrichment | ❌ | ✅ |
| Memory Consolidation | ❌ | ✅ |
| v2 Search API | ✅ | ✅ |
| 100+ Search Results | ✅ | ✅ |
| Docker Support | ✅ | ✅ |
| Open WebUI Integration | ✅ | ✅ |

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

### Too many memories rejected

Lower quality thresholds in [main.py:22-24](main.py#L22-L24):
```python
MIN_MEMORY_LENGTH = 10   # Was 20
MIN_WORD_COUNT = 2       # Was 4
```

### Duplicate detection too sensitive

Increase similarity threshold in [main.py:24](main.py#L24):
```python
SIMILARITY_THRESHOLD = 0.90  # Was 0.85 (higher = more strict)
```

---

## 📊 Performance

- **Workers**: 2 (for production throughput)
- **Request timeout**: 60s (connect: 10s)
- **HTTP/2**: Enabled for Mem0 API calls
- **Connection pooling**: Via httpx AsyncClient
- **Health check**: Every 30s with 40s startup grace

---

## 🔐 Security Notes

- Never commit `MEM0_API_KEY` to version control
- Use environment variables for secrets
- CORS enabled for Open WebUI (adjust for production if needed)
- Quality filtering prevents spam/junk memories

---

## 📦 Stack Details

### Dependencies
- `fastapi==0.115.4`
- `uvicorn[standard]`
- `httpx[http2]`
- `pydantic>=2.0`

### Environment
- Python 3.11+
- Docker with multi-stage build
- Slim base image for smaller footprint

---

## 🎯 Version History

### 11.0.0 (The Intelligent One) - **Current**
- ✅ Quality filtering with configurable thresholds
- ✅ Smart deduplication before saving
- ✅ Automatic context enrichment with timestamps
- ✅ Memory consolidation endpoint
- ✅ Force save override option
- ✅ Enhanced health check with feature flags

### 10.0.0 (The Enlightened One)
- Upgraded to Mem0 v2 API for search
- 100+ search results support (was limited to 10)
- Multi-worker production setup

### 9.0.0 and earlier
- Basic Mem0 v1 API wrapper
- Simple CRUD operations

---

## 🤝 Credits

- **Original API**: Built for Open WebUI integration
- **Intelligence Features**: Inspired by [mem0-cathedral-mcp](https://github.com/1818TusculumSt/mem0-cathedral-mcp)
- **Maintained by**: El Jefe Principal 🧠

---

## 📝 License

Built for the network. Use wisely. 🏗️

---

## 🚀 Deployment

### Production Workflow

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Rebuild container:**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

3. **Verify health:**
   ```bash
   curl http://localhost:8007/health
   ```

### Expected Health Response
```json
{
  "status": "at_peace",
  "version": "11.0.0",
  "features": {
    "quality_filtering": true,
    "deduplication": true,
    "context_enrichment": true,
    "consolidation": true
  }
}
```

---

## 💡 Tips for Open WebUI

### Best Practices

1. **Let quality filtering work** - It prevents memory bloat
2. **Use force sparingly** - Only when truly needed
3. **Run consolidation periodically** - Clean up duplicates
4. **Check duplicate suggestions** - Update instead of creating new

### Adjusting for Your Needs

**More permissive filtering:**
```python
MIN_MEMORY_LENGTH = 10
MIN_WORD_COUNT = 2
```

**More strict deduplication:**
```python
SIMILARITY_THRESHOLD = 0.90
```

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Mem0 Docs**: https://docs.mem0.ai
- **Open WebUI**: https://github.com/open-webui/open-webui

---

Happy memory management! 🧠✨