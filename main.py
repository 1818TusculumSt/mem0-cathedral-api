from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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

# Quality thresholds (configurable) - Used for legacy content-based mode
MIN_MEMORY_LENGTH = 20  # Minimum characters for a memory
MIN_WORD_COUNT = 4      # Minimum words in a memory
SIMILARITY_THRESHOLD = 0.85  # Deduplication threshold (0.0-1.0)

# Default memory categories (Mem0 native feature)
DEFAULT_CATEGORIES = {
    "personal_information": "User's name, location, age, family, background",
    "preferences": "Likes, dislikes, favorites, personal tastes",
    "work": "Career, projects, professional information, job details",
    "food_preferences": "Food likes, dislikes, dietary restrictions",
    "technical": "Technology stack, tools, programming languages, frameworks",
    "goals": "Objectives, plans, aspirations, future intentions",
    "health": "Health conditions, fitness routines, wellness",
    "hobbies": "Interests, activities, pastimes",
    "relationships": "Friends, family, colleagues, connections",
    "location": "Places lived, traveled, or frequently visited",
    "schedule": "Routines, availability, time preferences",
    "communication": "Preferred communication styles and channels"
}

# Custom extraction instructions (Mem0 native feature)
EXTRACTION_INSTRUCTIONS = """
Extract memories with these priorities:
- Be generous with preference detection (both explicit and implicit)
- Include temporal context when relevant
- Extract behavioral patterns, habits, and routines
- Catch goals, aspirations, and future plans
- Focus on long-term user characteristics
- Include relationships and social context
- Avoid temporary states or simple acknowledgments
- Prefer specific facts over general statements
"""

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
    (Legacy mode only - AI extraction mode uses structured metadata)
    """
    # Add timestamp context
    timestamp = datetime.now(timezone.utc).isoformat()

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
    # NEW: Support conversation-based extraction (Mem0 native)
    messages: Optional[list[dict]] = Field(
        default=None,
        description="Conversation messages for automatic extraction. Format: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]. When provided, Mem0's AI extracts memories automatically."
    )
    # Legacy: Pre-extracted content (backward compatible)
    content: Optional[str] = Field(
        default=None,
        description="Pre-extracted memory content (legacy mode). Use 'messages' for better AI extraction."
    )

    # Core identifiers
    user_id: str = Field(default="el-jefe-principal", description="User ID to associate this memory with.")
    agent_id: Optional[str] = Field(default=None, description="AI agent identifier for multi-agent systems.")
    run_id: Optional[str] = Field(default=None, description="Conversation session ID for tracking specific interactions.")

    # Mem0 native extraction features
    infer: bool = Field(default=True, description="Let Mem0's AI extract memories automatically from messages. Set false to store messages as-is.")
    custom_categories: Optional[dict] = Field(default=None, description="Custom memory categories with descriptions. Uses DEFAULT_CATEGORIES if not provided.")
    custom_instructions: Optional[str] = Field(default=None, description="Custom extraction instructions to guide Mem0's AI.")
    metadata: Optional[dict] = Field(default=None, description="Structured metadata (location, timestamp, tags, etc.).")

    # Advanced features
    enable_graph: bool = Field(default=False, description="Build entity relationships for contextual retrieval.")
    includes: Optional[str] = Field(default=None, description="Focus extraction on specific topics (e.g., 'preferences, goals, skills').")
    excludes: Optional[str] = Field(default=None, description="Exclude specific patterns (e.g., 'acknowledgments, temporary states').")
    async_mode: bool = Field(default=True, description="Process memory in background for faster response.")

    # Legacy compatibility
    force: bool = Field(default=False, description="Bypass quality checks in legacy content mode.")

class SearchMemoryInput(BaseModel):
    query: str = Field(..., description="Search query to find relevant memories - can be keywords, questions, or topics.")
    user_id: str = Field(default="el-jefe-principal", description="User ID to search memories for.")
    agent_id: Optional[str] = Field(default=None, description="Filter by specific AI agent.")
    run_id: Optional[str] = Field(default=None, description="Filter by specific conversation session.")
    limit: int = Field(default=100, description="Maximum number of memories to return (up to 100).")
    categories: Optional[list[str]] = Field(default=None, description="Filter by memory categories (e.g., ['preferences', 'work']).")
    enable_graph: bool = Field(default=False, description="Include entity relationships in search results.")

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
    version="12.0.0 (The AI-Powered One)",
    description=(
        "🚀 AI-powered Mem0 wrapper with native extraction, categories, and graph memory. "
        "Uses Mem0's built-in AI for intelligent memory extraction from conversations. "
        "✅ AI Extraction | ✅ Custom Categories | ✅ Graph Relationships | ✅ Multi-Agent Support | ✅ Metadata & Filtering"
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
    description=(
        "🚀 NEW: AI-powered memory extraction! "
        "Pass conversation 'messages' for automatic extraction, or use legacy 'content' mode. "
        "Mem0's AI extracts facts, preferences, goals, and context automatically. "
        "Supports categories, metadata, graph relationships, and multi-agent tracking."
    ),
)
async def add_memory(data: AddMemoryInput):
    """
    Add memory with two modes:
    1. AI Extraction Mode (recommended): Pass 'messages' array, Mem0 extracts automatically
    2. Legacy Mode: Pass 'content' string with manual quality checks
    """
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}

    # Validate input
    if not data.messages and not data.content:
        raise HTTPException(status_code=400, detail="Either 'messages' or 'content' must be provided")

    # ============================================================
    # MODE 1: AI EXTRACTION (Mem0 native - RECOMMENDED)
    # ============================================================
    if data.messages:
        # Build enriched metadata
        enriched_metadata = data.metadata or {}
        enriched_metadata.update({
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "cathedral_api",
            "api_version": "12.0.0",
            "extraction_mode": "ai_powered"
        })

        # Build Mem0 API payload (only include supported parameters)
        payload = {
            "messages": data.messages,
            "user_id": data.user_id,
            "infer": data.infer,  # Mem0's AI extraction
            "metadata": enriched_metadata,
            "async_mode": data.async_mode,
        }

        # Add optional fields only if provided
        if data.agent_id:
            payload["agent_id"] = data.agent_id
        if data.run_id:
            payload["run_id"] = data.run_id
        if data.enable_graph:
            payload["enable_graph"] = data.enable_graph
        if data.includes:
            payload["includes"] = data.includes
        if data.excludes:
            payload["excludes"] = data.excludes

        # Add custom categories and instructions only if provided by user
        # (Don't send defaults - let Mem0 use its own defaults)
        if data.custom_categories:
            payload["custom_categories"] = data.custom_categories
        if data.custom_instructions:
            payload["custom_instructions"] = data.custom_instructions

        # Send to Mem0
        try:
            response = await http_client.post(f"{MEM0_API_URL}/memories/", headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Mem0 API error: {e.response.status_code} - {e.response.text}")
            logger.error(f"Payload sent: {payload}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Mem0 API error: {e.response.text}"
            )

        if response_data:
            first_memory = response_data[0] if isinstance(response_data, list) else response_data
            return {
                "ok": True,
                "mode": "ai_extraction",
                "memory_id": first_memory.get("id"),
                "extracted_count": len(response_data) if isinstance(response_data, list) else 1,
                "categories": first_memory.get("categories", []),
                "graph_enabled": data.enable_graph,
                "async_processing": data.async_mode,
                "message": "Memory extracted and saved by Mem0's AI"
            }
        else:
            return {"ok": False, "error": "Mem0 API returned empty response"}

    # ============================================================
    # MODE 2: LEGACY CONTENT MODE (Backward Compatible)
    # ============================================================
    else:
        # Assess quality (legacy)
        quality = assess_memory_quality(data.content)

        if not data.force and not quality["should_save"]:
            return {
                "ok": False,
                "rejected": True,
                "mode": "legacy_content",
                "reason": "Quality threshold not met",
                "issues": quality["issues"],
                "suggestion": "Provide more context, use 'force: true', or switch to 'messages' mode for AI extraction",
            }

        # Check for duplicates (legacy)
        search_payload = {
            "query": data.content[:100],
            "version": "v2",
            "filters": {"user_id": data.user_id},
            "top_k": 5
        }

        try:
            search_response = await http_client.post(
                f"{MEM0_API_V2_URL}/memories/search/",
                headers=headers,
                json=search_payload
            )
            if search_response.status_code == 200:
                search_data = search_response.json()
                similar_memories = search_data.get("results", []) if isinstance(search_data, dict) else search_data

                for mem in similar_memories:
                    similarity = calculate_similarity(data.content, mem.get("memory", ""))
                    if similarity > SIMILARITY_THRESHOLD:
                        return {
                            "ok": False,
                            "duplicate": True,
                            "mode": "legacy_content",
                            "existing_memory_id": mem.get("id"),
                            "existing_content": mem.get("memory"),
                            "similarity": round(similarity, 2),
                            "suggestion": "Use update_memory to modify existing memory instead",
                        }
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")

        # Enrich content (legacy)
        enriched_content = enrich_memory_context(data.content)

        # Build metadata
        enriched_metadata = data.metadata or {}
        enriched_metadata.update({
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "cathedral_api",
            "api_version": "12.0.0",
            "extraction_mode": "legacy_content",
            "quality_score": quality["score"]
        })

        # Save to Mem0 (legacy mode)
        payload = {
            "messages": [{"role": "user", "content": enriched_content}],
            "user_id": data.user_id,
            "version": "v2",
            "infer": False,  # Don't extract in legacy mode
            "metadata": enriched_metadata
        }

        if data.agent_id:
            payload["agent_id"] = data.agent_id
        if data.run_id:
            payload["run_id"] = data.run_id

        response = await http_client.post(f"{MEM0_API_URL}/memories/", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()

        if response_data:
            return {
                "ok": True,
                "mode": "legacy_content",
                "memory_id": response_data[0].get("id"),
                "quality_score": quality["score"],
                "message": "Memory saved successfully (legacy mode)"
            }
        else:
            return {"ok": False, "error": "API returned an empty response, memory not created."}

# --- The Sacrament of Recollection (SEARCH) ---
@app.post(
    "/search_memories",
    summary="Search stored memories",
    description=(
        "🔍 Enhanced search with categories, graph relationships, and multi-agent filtering. "
        "Retrieves relevant memories with semantic search plus entity relationship context. "
        "Filter by user, agent, session, or memory categories for precise results."
    ),
)
async def search_memories(data: SearchMemoryInput):
    """
    Search memories with advanced filtering:
    - Category filtering (e.g., only 'preferences' or 'work')
    - Graph relationships (contextually related entities)
    - Agent/Session filtering
    - Up to 100 results
    """
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}

    # Build filters
    filters = {"user_id": data.user_id}
    if data.agent_id:
        filters["agent_id"] = data.agent_id
    if data.run_id:
        filters["run_id"] = data.run_id

    # Build payload with all features
    payload = {
        "query": data.query,
        "version": "v2",
        "filters": filters,
        "top_k": data.limit
    }

    # Add category filtering if specified
    if data.categories:
        payload["categories"] = data.categories

    # Add graph memory if enabled
    if data.enable_graph:
        payload["enable_graph"] = True

    response = await http_client.post(f"{MEM0_API_V2_URL}/memories/search/", headers=headers, json=payload)
    response.raise_for_status()
    results_data = response.json()

    # Handle response format
    memories = []
    if isinstance(results_data, dict) and "results" in results_data:
        memories = results_data["results"]
    elif isinstance(results_data, list):
        memories = results_data

    return {
        "memories": memories,
        "count": len(memories),
        "filters_applied": {
            "user_id": data.user_id,
            "agent_id": data.agent_id,
            "run_id": data.run_id,
            "categories": data.categories,
            "graph_enabled": data.enable_graph
        }
    }

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
    description="Retrieves all stored memories for a specific user. Optionally filter by agent or session. Use this at conversation start to load full context.",
)
async def get_all_memories(
    user_id: str = "el-jefe-principal",
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None
):
    """Get all memories with optional agent/session filtering"""
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    params = {"user_id": user_id}

    if agent_id:
        params["agent_id"] = agent_id
    if run_id:
        params["run_id"] = run_id

    response = await http_client.get(f"{MEM0_API_URL}/memories/", headers=headers, params=params)
    response.raise_for_status()
    memories = response.json()

    return {
        "memories": memories,
        "total": len(memories),
        "filters": {
            "user_id": user_id,
            "agent_id": agent_id,
            "run_id": run_id
        }
    }

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
        "version": "12.0.0",
        "mode": "ai_powered",
        "features": {
            "ai_extraction": True,
            "custom_categories": True,
            "graph_memory": True,
            "metadata_support": True,
            "multi_agent": True,
            "session_tracking": True,
            "async_processing": True,
            "legacy_mode": True,  # Backward compatible
            "quality_filtering": True,  # Legacy mode only
            "deduplication": True,  # Legacy mode only
            "context_enrichment": True,
            "consolidation": True
        },
        "extraction_modes": {
            "ai_powered": "Use 'messages' field for automatic extraction",
            "legacy_content": "Use 'content' field for manual quality checks"
        },
        "default_categories": list(DEFAULT_CATEGORIES.keys())
    }
