# Mem0 V1 Cathedral API for Open WebUI

FastAPI wrapper for Mem0's v1 API that exposes memory operations as OpenAPI endpoints for integration with Open WebUI.

## What This Does

- Wraps [Mem0 v1 API](https://docs.mem0.ai) memory operations
- Provides RESTful endpoints for memory management
- Enables persistent memory capabilities in Open WebUI through OpenAPI functions
- Runs with 2 uvicorn workers for better throughput
- Uses async httpx with connection pooling for efficient API calls

## Features

- **Add Memory** - Store new memories with user context
- **Search Memories** - Query memories with configurable limits (up to 100 results)
- **Get Memory** - Retrieve specific memory by ID
- **Update Memory** - Modify existing memory content
- **Delete Memory** - Remove memories permanently
- **Get History** - View memory modification history

## Stack

- **Base**: Python 3.11 slim
- **Framework**: FastAPI 0.115.4
- **Server**: Uvicorn with 2 workers
- **HTTP Client**: httpx with HTTP/2 support
- **Validation**: Pydantic v2

## Quick Start with Docker Compose

```bash
docker compose up -d
```

Requires `MEM0_API_KEY` environment variable.

## Build

```bash
docker build -t mem0-cathedral-api .
```

## Run Standalone

```bash
docker run -d \
  -p 8007:8000 \
  -e MEM0_API_KEY=your_mem0_api_key_here \
  --name mem0-proxy \
  mem0-cathedral-api
```

## Environment Variables

- `MEM0_API_KEY` - Your Mem0 API key (required)
  - Get yours at: https://app.mem0.ai/

## Open WebUI Integration

Once running, add to Open WebUI:
1. Navigate to **Settings → Functions**
2. Add new function using OpenAPI URL: `http://your-server:8007/openapi.json`
3. Memory operations will be available in your chats

## API Endpoints

### Add Memory
```
POST /add_memory
{
  "content": "Your memory content here",
  "user_id": "el-jefe-principal"
}
```

### Search Memories
```
POST /search_memories
{
  "query": "search term",
  "user_id": "el-jefe-principal",
  "limit": 100
}
```

### Get Memory
```
GET /get_memory/{memory_id}
```

### Update Memory
```
PUT /update_memory/{memory_id}
{
  "text": "Updated memory content",
  "user_id": "el-jefe-principal"
}
```

### Delete Memory
```
DELETE /delete_memory/{memory_id}
```

### Get History
```
GET /get_history/{memory_id}
```

### Health Check
```
GET /health
```

## API Documentation

- Swagger UI: `http://localhost:8007/docs`
- ReDoc: `http://localhost:8007/redoc`
- OpenAPI spec: `http://localhost:8007/openapi.json`

## Default Configuration

- Default user ID: `el-jefe-principal`
- Default search limit: 100 memories
- Internal port: 8000
- Exposed port: 8007 (configurable in compose.yaml)
- Workers: 2 (for better throughput)
- Request timeout: 60s (connect: 10s)
- Healthcheck: Every 30s with 40s startup grace period

## Development Workflow

1. **Production**: Running container serves live traffic to Open WebUI
2. **Dev**: Clone repo, make changes, test locally
3. **Deploy**: Push to GitHub, pull on production, rebuild

## Architecture Notes

- Uses async/await throughout for non-blocking I/O
- HTTP client pooling via FastAPI lifespan context manager
- CORS enabled for Open WebUI cross-origin requests
- Pydantic models for request/response validation
- HTTP/2 support for improved performance with Mem0 API
- Health check endpoint for container orchestration

## Version

**9.0.0 (The All-Seeing Eye)**
- Full memory retrieval with configurable limits
- Multi-worker support for production workloads
- Optimized connection pooling

---

Built for the network. Maintained by El Jefe. 🏗️