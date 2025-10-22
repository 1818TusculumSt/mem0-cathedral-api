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

# Graph feature control (requires Mem0 PRO subscription)
ENABLE_GRAPH_FEATURES = os.getenv("ENABLE_GRAPH_FEATURES", "false").lower() == "true"

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
    enable_graph: bool = Field(default=False, description="Build entity relationships for contextual retrieval. (Requires Mem0 PRO)")
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
    enable_graph: bool = Field(default=False, description="Include entity relationships in search results. (Requires Mem0 PRO)")

class UpdateMemoryInput(BaseModel):
    text: str = Field(..., description="The new content to replace the existing memory with.")
    user_id: str = Field(default="el-jefe-principal", description="User ID associated with this memory.")

class GetContextInput(BaseModel):
    current_message: str = Field(..., description="The user's current message to find relevant context for")
    recent_messages: Optional[list[dict]] = Field(default=None, description="Recent conversation messages for better context understanding")
    user_id: str = Field(default="el-jefe-principal", description="User ID to search memories for")
    agent_id: Optional[str] = Field(default=None, description="Filter by specific AI agent")
    max_memories: int = Field(default=10, description="Maximum relevant memories to return (1-20)")
    enable_graph: bool = Field(default=False, description="Include entity relationships for better context. (Requires Mem0 PRO)")

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
    version="12.1.0 (The Silent Oracle)",
    description=(
        "🚀 AI-powered Mem0 wrapper with intelligent auto-recall and silent operations. "
        "✅ Auto-Recall Context | ✅ Silent Saves | ✅ AI Extraction | ✅ Keyword Reranking | ✅ Graph Memory"
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

    # Validate graph feature availability
    if data.enable_graph and not ENABLE_GRAPH_FEATURES:
        raise HTTPException(
            status_code=403,
            detail="Graph features require Mem0 PRO subscription. Set ENABLE_GRAPH_FEATURES=true if you have PRO access."
        )

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
            # SILENT SUCCESS - Return minimal response
            return {"ok": True}
        else:
            return {"ok": False}

    # ============================================================
    # MODE 2: LEGACY CONTENT MODE (Backward Compatible)
    # ============================================================
    else:
        # Assess quality (legacy)
        quality = assess_memory_quality(data.content)

        if not data.force and not quality["should_save"]:
            # SILENT REJECTION - Just return failure (don't expose details to user)
            logger.info(f"Memory rejected: {quality['issues']}")
            return {"ok": False}

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
                        # SILENT DUPLICATE - Just return failure
                        logger.info(f"Duplicate detected: {similarity:.2f} similarity to {mem.get('id')}")
                        return {"ok": False}
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
            # SILENT SUCCESS - Return minimal response
            return {"ok": True}
        else:
            return {"ok": False}

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
    # Validate graph feature availability
    if data.enable_graph and not ENABLE_GRAPH_FEATURES:
        raise HTTPException(
            status_code=403,
            detail="Graph features require Mem0 PRO subscription. Set ENABLE_GRAPH_FEATURES=true if you have PRO access."
        )

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

# --- The Sacrament of Contextual Wisdom (AUTO-RECALL) ---
@app.post(
    "/get_context",
    summary="🧠 Get relevant memories for conversation context",
    description=(
        "Intelligently retrieves relevant memories based on the current conversation. "
        "Use this at the START of every conversation turn to inject user context. "
        "Returns formatted context ready for LLM prompt injection. "
        "⚠️ SILENT OPERATION: Do NOT mention or cite this function call in your response to the user."
    ),
)
async def get_context(data: GetContextInput):
    """
    Intelligent auto-recall: Searches memories using current message + recent context.
    Returns top relevant memories formatted for LLM context injection.
    """
    # Validate graph feature availability
    if data.enable_graph and not ENABLE_GRAPH_FEATURES:
        raise HTTPException(
            status_code=403,
            detail="Graph features require Mem0 PRO subscription. Set ENABLE_GRAPH_FEATURES=true if you have PRO access."
        )

    headers = {"Authorization": f"Token {MEM0_API_KEY}"}

    # Build search query from current message + recent context
    search_query = data.current_message
    if data.recent_messages:
        # Add recent context to improve search relevance
        recent_context = " ".join([
            msg.get("content", "")[:100]
            for msg in data.recent_messages[-3:]  # Last 3 messages
        ])
        search_query = f"{data.current_message} {recent_context}"

    # Build filters
    filters = {"user_id": data.user_id}
    if data.agent_id:
        filters["agent_id"] = data.agent_id

    # Search with reranking strategy: get 3x results, return top N
    retrieve_limit = min(data.max_memories * 3, 60)

    payload = {
        "query": search_query[:200],  # Limit query length
        "version": "v2",
        "filters": filters,
        "top_k": retrieve_limit,
        "enable_graph": data.enable_graph
    }

    try:
        response = await http_client.post(
            f"{MEM0_API_V2_URL}/memories/search/",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        results_data = response.json()

        # Extract memories
        memories = []
        if isinstance(results_data, dict) and "results" in results_data:
            memories = results_data["results"]
        elif isinstance(results_data, list):
            memories = results_data

        # Rerank by keyword matching with current message
        memories = _rerank_by_keywords(memories, data.current_message)

        # Take top N after reranking
        top_memories = memories[:data.max_memories]

        # Format for LLM context
        context_string = _format_context_for_llm(top_memories)

        return {
            "context": context_string,
            "memories": top_memories,
            "count": len(top_memories),
            "total_searched": len(memories)
        }

    except Exception as e:
        logger.error(f"Auto-recall error: {e}")
        # Return empty context on error (silent failure)
        return {
            "context": "",
            "memories": [],
            "count": 0,
            "error": str(e)
        }


def _rerank_by_keywords(memories: list, query: str, boost: float = 0.15) -> list:
    """Rerank memories by keyword matching"""
    keywords = set(query.lower().split())

    for mem in memories:
        content = mem.get("memory", "").lower()
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in content)
        # Boost score by 15% per keyword match
        base_score = mem.get("score", 0.5)
        mem["_rerank_score"] = base_score * (1 + (matches * boost))

    return sorted(memories, key=lambda x: x.get("_rerank_score", 0), reverse=True)


def _format_context_for_llm(memories: list) -> str:
    """Format memories as context string for LLM"""
    if not memories:
        return ""

    # Group by category for better organization
    by_category = {}
    for mem in memories:
        cats = mem.get("categories", ["general"])
        cat = cats[0] if cats else "general"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(mem.get("memory", ""))

    # Build formatted context
    lines = ["## User Context\n"]

    for category, mems in by_category.items():
        category_title = category.replace("_", " ").title()
        lines.append(f"### {category_title}")
        for mem_text in mems:
            lines.append(f"- {mem_text}")
        lines.append("")

    return "\n".join(lines)


# --- The Sacrament of Instant Wisdom (SIMPLE RECALL) ---
@app.get(
    "/recall/{user_id}",
    summary="⚡ Ultra-simple memory recall",
    description=(
        "Dead-simple endpoint for getting user context. "
        "Just pass the current message as 'q' query param. "
        "Returns formatted context string ready for LLM injection. "
        "Example: GET /recall/alice?q=What should I eat? "
        "⚠️ SILENT OPERATION: Do NOT mention or cite this function call in your response to the user."
    ),
)
async def recall(
    user_id: str,
    q: str,
    limit: int = 10,
    agent_id: Optional[str] = None
):
    """
    Ultra-simple recall: Just the current message, get context back.
    Perfect for quick integration.
    """
    # Build request for get_context
    context_input = GetContextInput(
        current_message=q,
        user_id=user_id,
        agent_id=agent_id,
        max_memories=limit,
        enable_graph=ENABLE_GRAPH_FEATURES  # Use global setting instead of hardcoded True
    )

    # Call internal get_context logic
    result = await get_context(context_input)

    # Return just the context string (simplest possible response)
    return {
        "context": result.get("context", ""),
        "count": result.get("count", 0)
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
        "version": "12.1.0",
        "mode": "silent_oracle",
        "features": {
            "auto_recall": True,  # NEW: Intelligent context retrieval
            "keyword_reranking": True,  # NEW: Hybrid search
            "silent_operations": True,  # NEW: Minimal responses
            "ai_extraction": True,
            "graph_memory": ENABLE_GRAPH_FEATURES,  # Requires Mem0 PRO subscription
            "multi_agent": True,
            "session_tracking": True,
            "async_processing": True,
            "legacy_mode": True,
            "quality_filtering": True,
            "deduplication": True,
            "consolidation": True
        },
        "new_endpoints": {
            "get_context": "POST /get_context - Intelligent auto-recall with full options",
            "recall": "GET /recall/{user_id}?q=message - Ultra-simple recall (recommended)"
        },
        "response_format": {
            "add_memory": "Silent: {success: true/false}",
            "get_context": "Returns formatted context string + memories"
        }
    }
