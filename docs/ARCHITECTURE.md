# Architecture

TabletopGPT is a Compose-based local application. The first scaffold favors clear boundaries over completeness.

## Services

- `game-api`: FastAPI app, static frontend, WebSocket endpoint, campaign APIs.
- `game-worker`: background worker that claims campaign jobs and calls Ollama when needed.
- `postgres`: durable campaign state.
- `redis`: future lightweight coordination, presence expiration, rate limiting, and queue helpers.
- `qdrant`: vector store for campaign knowledge chunks.
- `ollama`: local LLM and embedding service with NVIDIA GPU support.

Only `game-api` and Ollama are exposed for local development. PostgreSQL, Redis, and Qdrant stay on the internal Compose network.

## Backend Modules

- `main.py`: API routes, startup schema install, WebSocket handling.
- `db.py`: asyncpg pool helpers.
- `security.py`: hashing, membership checks, input validation, CSP middleware.
- `dice.py`: server-side dice rolling.
- `rules_engine.py`: starter action validation and mechanics.
- `turn_manager.py`: enqueue and process round resolution.
- `llm_dm.py`: Ollama calls and prompt boundaries.
- `gm_takeover.py`: emergency human GM takeover helpers.
- `worker.py`: SKIP LOCKED job processor.
- `rag/`: ingestion, chunking, embeddings, and retrieval.

## Authority Boundary

The backend owns campaign truth. LLM output is text unless a future reviewed workflow explicitly converts suggestions into backend-validated mutations.

## Data Flow

Players use HTTP to create/join campaigns and WebSocket for session updates. A resolve request inserts a single pending job per campaign. The worker locks the job, gathers active actions, rolls dice, resolves starter mechanics, and either writes official narration or creates a hybrid draft.
