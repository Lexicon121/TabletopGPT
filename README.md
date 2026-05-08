# TabletopGPT

A self-hosted multiplayer tabletop RPG engine powered by local LLMs.

TabletopGPT is an early scaffold for running campaign sessions on a gaming PC with Docker Compose, FastAPI, PostgreSQL, Redis, Qdrant, and Ollama. The backend owns rules, dice, HP, conditions, membership, campaign truth, and event logs. Local LLMs narrate validated outcomes, answer read-only questions, and help retrieve campaign/rules context.

## Quick Start

Requirements:

- Docker Desktop or Docker Engine with Docker Compose
- NVIDIA Container Toolkit for GPU-backed Ollama on Linux/WSL2
- A gaming PC-class host is the primary target: 11th Gen Intel CPU, 32 GB RAM, RTX 3060 8GB GPU

```sh
cp .env.example .env
docker compose up -d --build
docker exec -it tabletop-gpt-ollama ollama pull qwen3:8b
docker exec -it tabletop-gpt-ollama ollama pull llama3.2:3b
docker exec -it tabletop-gpt-ollama ollama pull nomic-embed-text
```

Open the local app at:

- http://localhost:8080

Ollama is also exposed for local development at:

- http://localhost:11434

## Local Models

Recommended models:

- Main DM model: `qwen3:8b` or `llama3.1:8b`
- Ask-the-DM helper model: `llama3.2:3b`
- Embedding model: `nomic-embed-text`
- Optional embedding upgrade: `mxbai-embed-large`

You can pull a model through the helper script:

```sh
./scripts/pull-model.sh qwen3:8b
```

## DM Modes

DM mode is a first-class campaign setting:

- `llm_dm`: the LLM generates official narration after backend validation, dice, and mechanics resolution.
- `hybrid`: the LLM creates a draft narration, then a human GM or owner approves, edits, or rejects it.
- `human_gm`: a human GM writes official narration while the backend remains authoritative for dice, HP, conditions, campaign truth, and logs.

The main DM model should produce one narration per resolved round. TabletopGPT does not call the LLM once per player action.

## Multiplayer Flow

Players submit or update one official action during the planning phase. When the round resolves, the server validates actions, rolls dice, applies starter mechanics, and either writes narration, drafts narration, or waits for a human GM depending on the campaign DM mode. Party chat, presence, and Ask the DM are intentionally separate from official actions.

## RAG And Privacy

The repository includes empty folders for a local knowledge base:

- `data/knowledge/uploads`
- `data/knowledge/processed`
- `data/knowledge/indexes`

Use these for lawfully owned rule PDFs, character sheets, campaign notes, homebrew rules, NPC notes, item catalogs, and world lore. Do not commit PDFs, private notes, character sheets, or copyrighted materials. RAG retrieves only a few relevant chunks and never mutates game state.

## Security Notes

Run TabletopGPT on a trusted LAN or behind a private VPN. This scaffold does not implement production-grade authentication, public hosting hardening, account recovery, or moderation. PostgreSQL, Redis, and Qdrant are internal Docker services and are not exposed publicly. Campaign passwords are hashed with bcrypt.

## Development

Useful commands:

```sh
./scripts/dev-up.sh
./scripts/dev-down.sh
python -m compileall game-api
```

The static first-pass frontend lives at `game-api/static/index.html`. Placeholder React files live under `frontend/` for a later development pass.

## First Development Roadmap

1. Add real player authentication and session tokens.
2. Expand rules resolution beyond starter dice/action scaffolding.
3. Implement hybrid draft approval UI.
4. Add RAG upload/indexing jobs and source management.
5. Build the React frontend from the placeholder component map.
6. Add tests for dice, campaign membership, action replacement, job locking, and GM takeover.
7. Add production deployment guidance, TLS, backups, and observability.
