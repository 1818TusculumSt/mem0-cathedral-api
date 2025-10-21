# Cathedral API v12.0 - Usage Examples

## Example 1: Basic AI Extraction

**Scenario:** User shares preferences in conversation

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I love pizza but hate pineapple on it"},
      {"role": "assistant", "content": "Got it! No pineapple pizza for you."}
    ],
    "user_id": "alice"
  }'
```

**What Mem0 Extracts:**
- "User loves pizza"
- "User dislikes pineapple on pizza"
- Categories: `["food_preferences"]`

---

## Example 2: Multi-Category Extraction

**Scenario:** User shares professional background

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I'\''m a Python developer in Seattle, working on ML projects with PyTorch"},
      {"role": "assistant", "content": "Interesting! Machine learning in Seattle. How long have you been in ML?"},
      {"role": "user", "content": "About 3 years, mostly computer vision stuff"}
    ],
    "user_id": "bob",
    "enable_graph": true
  }'
```

**What Mem0 Extracts:**
- "User is a Python developer"
- "User works on ML projects"
- "User uses PyTorch"
- "User is located in Seattle"
- "User has 3 years of ML experience"
- "User specializes in computer vision"

**Categories:** `["work", "technical", "location"]`

**Graph Entities:** Python ↔ PyTorch, ML ↔ Computer Vision, Seattle

---

## Example 3: Search with Category Filtering

**Find only work-related memories:**

```bash
curl -X POST http://localhost:8000/search_memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does the user do for work?",
    "user_id": "bob",
    "categories": ["work", "technical"],
    "enable_graph": true,
    "limit": 10
  }'
```

**Returns:**
- All work and technical memories
- Related entities from graph (e.g., technologies mentioned in work context)

---

## Example 4: Multi-Agent Session Tracking

**Scenario:** Support bot helping with diet plan

```bash
# First interaction
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I'\''m vegetarian and allergic to nuts"},
      {"role": "assistant", "content": "Thanks! I'\''ll remember your dietary restrictions."}
    ],
    "user_id": "alice",
    "agent_id": "nutrition-bot",
    "run_id": "session-001",
    "metadata": {
      "session_date": "2025-01-15",
      "session_type": "initial_consultation"
    }
  }'

# Later: Get only memories from this agent/session
curl "http://localhost:8000/get_all_memories/alice?agent_id=nutrition-bot&run_id=session-001"
```

---

## Example 5: Custom Extraction Instructions

**Scenario:** Only extract technical skills, ignore small talk

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hey! So I know React, Vue, and Angular"},
      {"role": "assistant", "content": "Nice! Which do you prefer?"},
      {"role": "user", "content": "React for sure, been using it for 5 years"}
    ],
    "user_id": "charlie",
    "custom_instructions": "Extract only technical skills and experience levels. Ignore greetings and casual conversation.",
    "includes": "skills, technologies, frameworks, experience",
    "excludes": "greetings, acknowledgments, small talk"
  }'
```

**What Mem0 Extracts:**
- "User knows React, Vue, and Angular"
- "User prefers React"
- "User has 5 years of React experience"

**Categories:** `["technical"]`

---

## Example 6: Custom Categories

**Scenario:** E-commerce assistant with custom categories

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I usually shop for home office equipment, looking for ergonomic chairs"},
      {"role": "assistant", "content": "Great! I'\''ll help you find ergonomic chairs."}
    ],
    "user_id": "dana",
    "custom_categories": {
      "shopping_preferences": "Product categories and shopping habits",
      "product_interests": "Specific products user is interested in",
      "ergonomics": "Ergonomic and comfort preferences"
    }
  }'
```

---

## Example 7: Legacy Mode (Backward Compatible)

**Old v11.x code still works:**

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers dark mode for all applications",
    "user_id": "eve"
  }'
```

**Behavior:**
- Uses quality filtering (min length, word count)
- Checks for duplicates
- Enriches with timestamp
- No AI extraction

---

## Example 8: Search Across Multiple Agents

**Find memories from any agent interacting with user:**

```bash
curl -X POST http://localhost:8000/search_memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "preferences",
    "user_id": "alice",
    "limit": 50
  }'
```

**Or filter to specific agent:**

```bash
curl -X POST http://localhost:8000/search_memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "dietary restrictions",
    "user_id": "alice",
    "agent_id": "nutrition-bot"
  }'
```

---

## Example 9: Graph Memory Relationships

**Build entity connections:**

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "My friend John lives in Portland and works at Nike"},
      {"role": "assistant", "content": "Cool! How do you know John?"},
      {"role": "user", "content": "We met at a Python conference last year"}
    ],
    "user_id": "frank",
    "enable_graph": true
  }'
```

**Graph Built:**
- John (person) → lives in → Portland (location)
- John → works at → Nike (company)
- User → knows → John
- User → attended → Python conference
- User ↔ Python (interest/skill)

**Search with graph:**
```bash
curl -X POST http://localhost:8000/search_memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Portland",
    "user_id": "frank",
    "enable_graph": true
  }'
```

**Returns:**
- Direct mentions of Portland
- Related entities (John, Nike) because of graph connections

---

## Example 10: Metadata Filtering

**Add rich metadata:**

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I need to finish the Q1 report by Friday"}
    ],
    "user_id": "grace",
    "metadata": {
      "priority": "high",
      "deadline": "2025-01-17",
      "project": "Q1_report",
      "status": "in_progress"
    }
  }'
```

**Later, search or filter by metadata in your application logic**

---

## Example 11: Async Processing (Default)

**Fast response, background processing:**

```bash
curl -X POST http://localhost:8000/add_memory \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Long conversation with lots of context..."}
    ],
    "user_id": "henry",
    "async_mode": true
  }'
```

**API responds immediately:**
```json
{
  "ok": true,
  "mode": "ai_extraction",
  "async_processing": true,
  "message": "Memory extraction queued"
}
```

Memory processes in background, available within seconds.

---

## Example 12: Health Check

**Check API features:**

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "at_peace",
  "version": "12.0.0",
  "mode": "ai_powered",
  "features": {
    "ai_extraction": true,
    "custom_categories": true,
    "graph_memory": true,
    "metadata_support": true,
    "multi_agent": true,
    "session_tracking": true,
    "async_processing": true,
    "legacy_mode": true
  },
  "default_categories": [
    "personal_information",
    "preferences",
    "work",
    "food_preferences",
    "technical",
    "goals",
    "health",
    "hobbies",
    "relationships",
    "location",
    "schedule",
    "communication"
  ]
}
```

---

## Python SDK Example

```python
import httpx

class CathedralClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def add_memory_ai(self, messages, user_id, **kwargs):
        """Add memory with AI extraction"""
        payload = {
            "messages": messages,
            "user_id": user_id,
            **kwargs
        }
        response = await self.client.post(f"{self.base_url}/add_memory", json=payload)
        return response.json()

    async def search(self, query, user_id, categories=None, **kwargs):
        """Search memories with optional category filtering"""
        payload = {
            "query": query,
            "user_id": user_id,
            **({"categories": categories} if categories else {}),
            **kwargs
        }
        response = await self.client.post(f"{self.base_url}/search_memories", json=payload)
        return response.json()

# Usage
client = CathedralClient()

# Add memory with AI extraction
result = await client.add_memory_ai(
    messages=[
        {"role": "user", "content": "I love hiking in the mountains"},
        {"role": "assistant", "content": "That sounds amazing!"}
    ],
    user_id="alex",
    enable_graph=True
)

# Search with category filter
results = await client.search(
    query="outdoor activities",
    user_id="alex",
    categories=["hobbies"],
    enable_graph=True
)
```

---

## Open WebUI Integration

Add as a function in Open WebUI:

```python
async def save_user_memory(
    messages: list[dict],
    user_id: str,
    __user__: dict = {},
) -> str:
    """
    Save important information from conversation to long-term memory.

    :param messages: Conversation messages for AI extraction
    :param user_id: User identifier
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/add_memory",
            json={
                "messages": messages,
                "user_id": user_id,
                "enable_graph": True,
                "async_mode": True
            }
        )
        result = response.json()

        if result.get("ok"):
            return f"✅ Saved {result.get('extracted_count', 0)} memories"
        else:
            return f"❌ Failed: {result.get('error', 'Unknown error')}"
```
