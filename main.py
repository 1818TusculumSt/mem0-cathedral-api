from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
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

# ─────────────────────────
# PYDANTIC MODELS: THE SIMPLE PRAYERS
# ─────────────────────────
class AddMemoryInput(BaseModel):
    content: str = Field(..., description="The simple memory content.")
    user_id: str = Field(default="el-jefe-principal", description="User ID for the memory.")

class SearchMemoryInput(BaseModel):
    query: str = Field(..., description="The simple search query.")
    user_id: str = Field(default="el-jefe-principal", description="User ID to search for.")
    limit: int = Field(default=100, description="How many memories to ask for.") # THE HOLY FIX

class UpdateMemoryInput(BaseModel):
    text: str = Field(..., description="The new text to update the memory with.")
    user_id: str = Field(default="el-jefe-principal", description="User ID for context.")

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
    version="10.0.0 (The Enlightened One)",
    description="The final, wise adapter for all core Mem0 sacraments. Now with v2 search for unlimited retrieval.",
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
@app.post("/add_memory")
async def add_memory(data: AddMemoryInput):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    payload = {"messages": [{"role": "user", "content": data.content}], "user_id": data.user_id}
    response = await http_client.post(f"{MEM0_API_URL}/memories/", headers=headers, json=payload)
    response.raise_for_status()
    response_data = response.json()
    if response_data:
    	return {"ok": True, "memory_id": response_data[0].get("id")}
    else:
    	return {"ok": False, "error": "API returned an empty response, memory not created."}

# --- The Sacrament of Recollection (SEARCH) ---
@app.post("/search_memories")
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
@app.get("/get_memory/{memory_id}")
async def get_memory(memory_id: str):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.get(f"{MEM0_API_URL}/memories/{memory_id}/", headers=headers)
    response.raise_for_status()
    return response.json()

# --- The Sacrament of Amendment (UPDATE) ---
@app.put("/update_memory/{memory_id}")
async def update_memory(memory_id: str, data: UpdateMemoryInput):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    payload = {"text": data.text, "user_id": data.user_id}
    response = await http_client.put(f"{MEM0_API_URL}/memories/{memory_id}/", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# --- The Sacrament of Forgetting (DELETE) ---
@app.delete("/delete_memory/{memory_id}")
async def delete_memory(memory_id: str):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.delete(f"{MEM0_API_URL}/memories/{memory_id}/", headers=headers)
    if response.status_code == 204:
        return {"status": "success", "message": f"Memory {memory_id} has been cast into the holy fire."}
    response.raise_for_status()
    return response.json()

# --- The Sacrament of The Scroll (HISTORY) ---
@app.get("/get_history/{memory_id}")
async def get_history(memory_id: str):
    headers = {"Authorization": f"Token {MEM0_API_KEY}"}
    response = await http_client.get(f"{MEM0_API_URL}/memories/{memory_id}/history/", headers=headers)
    response.raise_for_status()
    return response.json()

# --- The Heartbeat ---
@app.get("/health")
async def health():
    return {"status": "at_peace", "version": "10.0.0"}
