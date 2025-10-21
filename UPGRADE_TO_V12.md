# 🚀 Upgrade Guide: Cathedral API v12.0.0

## What's New in v12.0.0

Version 12.0.0 brings **AI-powered memory extraction** using Mem0's native features. No external LLM required!

### Major Features

✅ **AI Extraction Mode** - Let Mem0's AI extract memories from conversations automatically
✅ **Custom Categories** - Organize memories into 12 predefined categories
✅ **Graph Memory** - Build entity relationships for contextual retrieval
✅ **Metadata Support** - Rich structured data with every memory
✅ **Multi-Agent Support** - Track memories by agent_id and run_id
✅ **Async Processing** - Faster API responses with background processing
✅ **Backward Compatible** - Legacy `content` mode still works

---

## Quick Start: AI Extraction Mode (NEW)

### Before (v11.x - Manual Extraction)
```python
# You had to extract the memory yourself
{
  "content": "User prefers dark mode",
  "user_id": "alice"
}
```

### After (v12.x - AI Extraction)
```python
# Just pass the conversation, Mem0 extracts automatically
{
  "messages": [
    {"role": "user", "content": "I always use dark mode, light themes hurt my eyes"},
    {"role": "assistant", "content": "Got it! I'll remember your preference for dark mode."}
  ],
  "user_id": "alice",
  "infer": true  // Mem0's AI extracts memories
}
```

**Result:** Mem0 automatically extracts:
- "User prefers dark mode"
- "User finds light themes uncomfortable"
- Categories: `["preferences", "technical"]`

---

## API Changes

### `/add_memory` Endpoint

#### NEW: AI Extraction Mode (Recommended)

```json
POST /add_memory
{
  "messages": [
    {"role": "user", "content": "I'm a Python developer working on ML projects"},
    {"role": "assistant", "content": "Interesting! How long have you been doing ML?"},
    {"role": "user", "content": "About 3 years now, mostly with PyTorch"}
  ],
  "user_id": "bob",
  "infer": true,
  "custom_categories": {
    "work": "Career and technical skills",
    "technical": "Technology preferences"
  },
  "enable_graph": true,
  "metadata": {
    "conversation_type": "onboarding",
    "importance": "high"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "mode": "ai_extraction",
  "memory_id": "mem_abc123",
  "extracted_count": 3,
  "categories": ["work", "technical"],
  "graph_enabled": true,
  "message": "Memory extracted and saved by Mem0's AI"
}
```

#### Legacy: Content Mode (Still Works)

```json
POST /add_memory
{
  "content": "User prefers TypeScript over JavaScript",
  "user_id": "bob"
}
```

---

### `/search_memories` Endpoint

#### NEW: Enhanced Search with Categories & Graph

```json
POST /search_memories
{
  "query": "What programming languages does the user know?",
  "user_id": "bob",
  "categories": ["technical", "work"],  // NEW: Filter by category
  "enable_graph": true,  // NEW: Include related entities
  "limit": 20
}
```

**Response:**
```json
{
  "memories": [
    {
      "id": "mem_abc123",
      "memory": "User is a Python developer with 3 years of ML experience",
      "categories": ["work", "technical"],
      "metadata": {...}
    }
  ],
  "count": 1,
  "filters_applied": {
    "user_id": "bob",
    "categories": ["technical", "work"],
    "graph_enabled": true
  }
}
```

---

### `/get_all_memories/{user_id}` Endpoint

#### NEW: Filter by Agent/Session

```http
GET /get_all_memories/alice?agent_id=support-bot&run_id=session-001
```

**Response:**
```json
{
  "memories": [...],
  "total": 5,
  "filters": {
    "user_id": "alice",
    "agent_id": "support-bot",
    "run_id": "session-001"
  }
}
```

---

## New Parameters Reference

### AddMemoryInput

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `messages` | array | - | **NEW**: Conversation for AI extraction |
| `content` | string | - | Legacy: Pre-extracted content |
| `user_id` | string | "el-jefe-principal" | User identifier |
| `agent_id` | string | null | **NEW**: AI agent identifier |
| `run_id` | string | null | **NEW**: Session/conversation ID |
| `infer` | boolean | true | **NEW**: Enable Mem0's AI extraction |
| `custom_categories` | dict | DEFAULT_CATEGORIES | **NEW**: Memory categories |
| `custom_instructions` | string | EXTRACTION_INSTRUCTIONS | **NEW**: Guide extraction |
| `metadata` | dict | {} | **NEW**: Structured metadata |
| `enable_graph` | boolean | false | **NEW**: Build entity relationships |
| `includes` | string | null | **NEW**: Focus on specific topics |
| `excludes` | string | null | **NEW**: Exclude patterns |
| `async_mode` | boolean | true | **NEW**: Background processing |

### SearchMemoryInput

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | - | Search query |
| `user_id` | string | "el-jefe-principal" | User identifier |
| `agent_id` | string | null | **NEW**: Filter by agent |
| `run_id` | string | null | **NEW**: Filter by session |
| `categories` | array | null | **NEW**: Filter by categories |
| `enable_graph` | boolean | false | **NEW**: Include graph relationships |
| `limit` | int | 100 | Max results |

---

## Default Categories

v12.0.0 includes 12 predefined categories:

1. **personal_information** - Name, location, age, family
2. **preferences** - Likes, dislikes, favorites
3. **work** - Career, projects, professional info
4. **food_preferences** - Food likes/dislikes, dietary restrictions
5. **technical** - Technology stack, tools, languages
6. **goals** - Objectives, plans, aspirations
7. **health** - Health conditions, fitness routines
8. **hobbies** - Interests, activities, pastimes
9. **relationships** - Friends, family, colleagues
10. **location** - Places lived, traveled, visited
11. **schedule** - Routines, availability, time preferences
12. **communication** - Preferred communication styles

---

## Migration Guide

### If You're Using Open WebUI

**Option 1: Use AI Extraction (Recommended)**

Update your function call to pass `messages` instead of extracting manually:

```javascript
// Before (v11.x)
const memory = extractMemory(conversation);  // Manual extraction
await addMemory({ content: memory });

// After (v12.x)
await addMemory({
  messages: conversation,  // Let Mem0 extract
  infer: true
});
```

**Option 2: Keep Using Legacy Mode**

Your existing code still works! Just using `content` field automatically uses legacy mode.

---

## Advanced Examples

### Multi-Agent Conversation Tracking

```json
{
  "messages": [
    {"role": "user", "content": "I need help with my diet plan"},
    {"role": "assistant", "content": "I can help! Any dietary restrictions?"}
  ],
  "user_id": "alice",
  "agent_id": "nutrition-bot",
  "run_id": "consultation-2025-01-15",
  "enable_graph": true,
  "metadata": {
    "session_type": "initial_consultation",
    "priority": "high"
  }
}
```

### Custom Extraction Instructions

```json
{
  "messages": [...],
  "user_id": "bob",
  "custom_instructions": "Focus on extracting technical skills, project experience, and career goals. Ignore casual conversation.",
  "includes": "skills, projects, goals, experience",
  "excludes": "greetings, acknowledgments, small talk"
}
```

### Category-Specific Search

```json
// Find only food-related memories
{
  "query": "What does the user like to eat?",
  "user_id": "alice",
  "categories": ["food_preferences"]
}
```

---

## Performance Notes

### Async Mode (Default: ON)
- Memories process in background
- API responds immediately
- Better UX for real-time chat

### Graph Memory
- Builds entity relationships
- Slight processing overhead
- Best for long-running assistants

### AI Extraction
- Uses Mem0's backend LLM (included in API costs)
- No external LLM setup required
- More accurate than manual quality rules

---

## Backward Compatibility

✅ All v11.x code continues to work
✅ Legacy `content` field still supported
✅ Quality filtering still active in legacy mode
✅ Deduplication still works

---

## Questions?

Check `/health` endpoint to see all available features:

```bash
curl http://localhost:8000/health
```

Or visit `/docs` for interactive API documentation.
