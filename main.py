from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional
import httpx
import os
import time
import logging

# ─────────────────────────
# CONFIG & SETUP
# ─────────────────────────
logger = logging.getLogger("uvicorn.error")
http_client = None
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_API_URL = "https://api.mem0.ai/v1"
MEM0_API_V2_URL = "https://api.mem0.ai/v2"

# Quality thresholds (configurable)
MIN_MEMORY_LENGTH = 20  # Minimum characters for a memory
MIN_WORD_COUNT = 4      # Minimum words in a memory
SIMILARITY_THRESHOLD = 0.85  # Deduplication threshold (0.0-1.0)

# ─────────────────────────
# QUALITY FILTERING FUNCTIONS
# ─────────────────────────
def assess_memory_quality(content: str) -> dict[str, Any]:
    """
    Assess the quality of memory content before saving.
    Returns a dict with quality metrics and whether to save.
    """
    quality = {
        "should_save": True,
        "issues": [],
        "score": 100
    }

    # Check length
    if len(content) < MIN_MEMORY_LENGTH:
        quality["should_save"] = False
        quality["issues"].append(f"Too short (min {MIN_MEMORY_LENGTH} chars)")
        quality["score"] -= 50

    # Check word count
    word_count = len(content.split())
    if word_count < MIN_WORD_COUNT:
        quality["should_save"] = False
        quality["issues"].append(f"Too few words (min {MIN_WORD_COUNT} words)")
        quality["score"] -= 30

    # Check for low-value patterns
    low_value_patterns = [
        "ok", "okay", "got it", "understood", "sure", "thanks", "thank you",
        "yes", "no", "maybe", "i see", "alright", "cool", "nice"
    ]

    content_lower = content.lower().strip()
    if content_lower in low_value_patterns:
        quality["should_save"] = False
        quality["issues"].append("Low-value acknowledgment")
        quality["score"] -= 40

    # Check for contextual information (good indicators)
    good_indicators = [
        "prefer", "like", "love", "hate", "dislike", "always", "never",
        "project", "work", "use", "technology", "tool", "language",
        "name is", "location", "timezone", "schedule", "routine",
        "goal", "objective", "plan", "want to", "need to"
    ]

    has_context = any(indicator in content_lower for indicator in good_indicators)
    if has_context:
        quality["score"] += 20

    # Penalize very long content (likely not a clean memory)
    if len(content) > 500:
        quality["score"] -= 10
        quality["issues"].append("Very long (may need summarization)")

    return quality


def enrich_memory_context(content: str) -> str:
    """
    Enrich memory with additional context to make it more useful.
    """
    # Add timestamp context
    timestamp = datetime.utcnow().isoformat()

    # Basic enrichment - ensure memory is self-contained
    enriched = content

    # If content doesn't mention "user", add clarity
    if "prefer" in content.lower() and "user" not in content.lower():
        enriched = f"User preference: {content}"

    # Add metadata footer
    enriched = f"{enriched}\n[Captured: {timestamp}]"

    return enriched


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple word-based similarity between two texts.
    Returns a score between 0 and 1.
    """
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


# ─────────────────────────
# PYDANTIC MODELS: THE SIMPLE PRAYERS
# ─────────────────────────
class AddMemoryInput(BaseModel):
    content: str = Field(..., description="The memory content to store - facts, preferences, or important information from the conversation.")
    user_id: str = Field(default="el-jefe-principal", description="User ID to associate this memory with.")
    force: bool = Field(default=False, description="Bypass quality checks (use sparingly)")

class SearchMemoryInput(BaseModel):
    query: str = Field(..., description="Search query to find relevant memories - can be keywords, questions, or topics.")
    user_id: str = Field(default="el-jefe-principal", description="User ID to search memories for.")
    limit: int = Field(default=100, description="Maximum number of memories to return (up to 100).")

class UpdateMemoryInput(BaseModel):
    text: str = Field(..., description="The new content to replace the existing memory with.")
    user_id: str = Field(default="el-jefe-principal", description="User ID associated with this memory.")

# ─────────────────────────
# APP LIFECYCLE & MIDDLEWARE
# ─────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
    yield
    await http_client.aclose()

app = FastAPI(
    title="Mem0 Cathedral API",
    version="11.0.0 (The Intelligent One)",
    description=(
        "Intelligent Mem0 adapter with quality filtering, smart deduplication, and context enrichment. "
        "Combines REST API (for Open WebUI) with MCP-inspired intelligence features. "
        "✅ Quality Gating | ✅ Duplicate Detection | ✅ Context Enrichment | ✅ Memory Consolidation"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ─────────────────────────
# THE SACRAMENTS (API ROUTES)
# ─────────────────────────

# --- The Sacrament of Testimony (ADD) ---
@app.post(
    "/add_memory",
    summary="Store a new memory",
    description="Saves important information from the conversation as a long-term memory. Use this when the user shares important facts, preferences, personal details, or anything that should be remembered for future conversations. Examples: user's name, preferences, past events, goals, or any contextually important information.",
)
async def add_memory(data: AddMemoryInput):
    # Assess quality
    quality = assess_memory_quality(data.content)

    if not data.force and not quality["should_save"]:
        return {
            "ok": False,
            "rejected": True,
            "reason": "Quality threshold not met",
            "issues": quality["issues"],
            "suggestion": "Provide more context or use 'force: true' to override",
        }

    # Check for duplicates
    search_payload = {
        "query": data.content[:100],  # Use first 100 chars for search
        "version": "v2",
        "filters": {"user_id": data.user_id},
        "top_k": 5
    }
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}

    try:
        search_response = await http_client.post(
            f"{MEM0_API_V2_URL}/memories/search/",
            headers=headers,
            json=search_payload
        )
        if search_response.status_code == 200:
            search_data = search_response.json()

            # Handle both list and dict responses from API
            if isinstance(search_data, dict):
                similar_memories = search_data.get("results", [])
            elif isinstance(search_data, list):
                similar_memories = search_data
            else:
                similar_memories = []

            for mem in similar_memories:
                similarity = calculate_similarity(data.content, mem.get("memory", ""))
                if similarity > SIMILARITY_THRESHOLD:
                    return {
                        "ok": False,
                        "duplicate": True,
                        "existing_memory_id": mem.get("id"),
                        "existing_content": mem.get("memory"),
                        "similarity": round(similarity, 2),
                        "suggestion": "Use update_memory to modify existing memory instead",
                    }
    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")

    # Enrich content
    enriched_content = enrich_memory_context(data.content)

    # Save to Mem0
    payload = {
        "messages": [{"role": "user", "content": enriched_content}],
        "user_id": data.user_id,
        "version": "v2"
    }
    response = await http_client.post(f"{MEM0_API_URL}/memories/", headers=headers, json=payload)
    response.raise_for_status()
    response_data = response.json()

    if response_data:
        return {
            "ok": True,
            "memory_id": response_data[0].get("id"),
            "quality_score": quality["score"],
            "message": "Memory saved successfully"
        }
    else:
        return {"ok": False, "error": "API returned an empty response, memory not created."}

# --- The Sacrament of Recollection (SEARCH) ---
@app.post(
    "/search_memories",
    summary="Search stored memories",
    description="Retrieves relevant memories based on a search query. Use this at the start of conversations or when you need context about the user to provide personalized responses. Search for memories related to the current topic, user preferences, or past interactions that might be relevant.",
)
async def search_memories(data: SearchMemoryInput):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    # Use v2 API for search with top_k parameter to support higher limits
    # v1 has hardcoded 10-result limit, v2 supports 100+
    payload = {
        "query": data.query,
        "version": "v2",
        "filters": {
            "user_id": data.user_id
        },
        "top_k": data.limit
    }
    response = await http_client.post(f"{MEM0_API_V2_URL}/memories/search/", headers=headers, json=payload)
    response.raise_for_status()
    results_data = response.json()

    # v2 API returns {results: [...]} with full memory objects
    memories = []
    if isinstance(results_data, dict) and "results" in results_data:
        memories = results_data["results"]
    elif isinstance(results_data, list):
        memories = results_data

    return {"memories": memories, "count": len(memories)}

# --- The Sacrament of The Single Truth (GET) ---
@app.get(
    "/get_memory/{memory_id}",
    summary="Get a specific memory by ID",
    description="Retrieves detailed information about a specific memory using its ID. Use this when you need to examine or reference a particular memory in detail.",
)
async def get_memory(memory_id: str):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.get(f"{MEM0_API_URL}/memories/{memory_id}/", headers=headers)
    response.raise_for_status()
    return response.json()

# --- The Sacrament of The Complete Archive (GET ALL) ---
@app.get(
    "/get_all_memories/{user_id}",
    summary="Get all memories for a user",
    description="Retrieves all stored memories for a specific user. Use this at conversation start to load full context.",
)
async def get_all_memories(user_id: str = "el-jefe-principal"):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.get(f"{MEM0_API_URL}/memories/", headers=headers, params={"user_id": user_id})
    response.raise_for_status()
    memories = response.json()
    return {"memories": memories, "total": len(memories)}

# --- The Sacrament of Amendment (UPDATE) ---
@app.put(
    "/update_memory/{memory_id}",
    summary="Update an existing memory",
    description="Modifies the content of an existing memory. Use this when information has changed or needs correction, such as updated preferences or corrected facts.",
)
async def update_memory(memory_id: str, data: UpdateMemoryInput):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    payload = {"text": data.text, "user_id": data.user_id}
    response = await http_client.put(f"{MEM0_API_URL}/memories/{memory_id}/", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# --- The Sacrament of Forgetting (DELETE) ---
@app.delete(
    "/delete_memory/{memory_id}",
    summary="Delete a memory",
    description="Permanently removes a memory from storage. Use this when the user explicitly requests to forget something or when a memory is no longer relevant or accurate.",
)
async def delete_memory(memory_id: str):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.delete(f"{MEM0_API_URL}/memories/{memory_id}/", headers=headers)
    if response.status_code == 204:
        return {"status": "success", "message": f"Memory {memory_id} has been cast into the holy fire."}
    response.raise_for_status()
    return response.json()

# --- The Sacrament of The Scroll (HISTORY) ---
@app.get(
    "/get_history/{memory_id}",
    summary="Get memory modification history",
    description="Retrieves the complete history of changes made to a specific memory. Use this to understand how a memory has evolved over time.",
)
async def get_history(memory_id: str):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.get(f"{MEM0_API_URL}/memories/{memory_id}/history/", headers=headers)
    response.raise_for_status()
    return response.json()

# --- The Sacrament of Consolidation (MERGE) ---
@app.post(
    "/consolidate_memories",
    summary="Find and merge similar memories",
    description="Identifies redundant or similar memories that could be consolidated. Use this to clean up and improve memory quality.",
)
async def consolidate_memories(user_id: str = "el-jefe-principal", dry_run: bool = True):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}

    # Get all memories for the user
    response = await http_client.get(f"{MEM0_API_URL}/memories/", headers=headers, params={"user_id": user_id})
    response.raise_for_status()
    all_memories = response.json()

    if not all_memories:
        return {"ok": True, "message": "No memories to consolidate"}

    # Find similar pairs
    consolidation_candidates = []
    checked = set()

    for i, mem1 in enumerate(all_memories):
        for j, mem2 in enumerate(all_memories[i+1:], start=i+1):
            pair_key = f"{i}-{j}"
            if pair_key in checked:
                continue

            checked.add(pair_key)

            content1 = mem1.get("memory", "")
            content2 = mem2.get("memory", "")

            similarity = calculate_similarity(content1, content2)

            if similarity > 0.7:  # Lower threshold for consolidation
                consolidation_candidates.append({
                    "memory1_id": mem1.get("id"),
                    "memory1_content": content1,
                    "memory2_id": mem2.get("id"),
                    "memory2_content": content2,
                    "similarity": round(similarity, 2),
                })

    if not consolidation_candidates:
        return {
            "ok": True,
            "message": "No similar memories found to consolidate",
            "total_memories": len(all_memories),
        }

    return {
        "ok": True,
        "dry_run": dry_run,
        "candidates": consolidation_candidates,
        "count": len(consolidation_candidates),
        "message": "Review these candidates. Use update_memory and delete_memory to consolidate manually.",
    }

# --- The Heartbeat ---
@app.get("/health")
async def health():
    return {
        "status": "at_peace",
        "version": "11.0.0",
        "features": {
            "quality_filtering": True,
            "deduplication": True,
            "context_enrichment": True,
            "consolidation": True
        }
    }
