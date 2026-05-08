# AGENTS.md

This repository is the initial scaffold for TabletopGPT, a self-hosted multiplayer tabletop RPG engine powered by local/offline LLMs.

## Project Priorities

- Keep the app self-hosted and Docker Compose friendly.
- Prefer simple, working scaffolds over production complexity.
- The backend is authoritative for dice, HP, conditions, membership, campaign truth, and event logs.
- LLMs may narrate, roleplay NPCs, answer read-only questions, and suggest state updates. LLMs must never directly mutate game state.
- Use round batching: one official narration per resolved round, not one LLM call per player action.
- Keep Ask the DM separate from official actions. It is read-only with respect to game state.
- Keep chat, presence, and event logs separate.

## Core Stack

- FastAPI backend in `game-api/`
- PostgreSQL schema in `game-api/models.sql`
- Redis for lightweight coordination/future queues
- Qdrant for RAG vector search
- Ollama for local LLM and embedding calls
- Static frontend first in `game-api/static/index.html`
- React placeholder tree in `frontend/`

## Commands

Run these after meaningful backend changes:

```sh
python -m compileall game-api
```

For local services:

```sh
cp .env.example .env
docker compose up -d --build
docker compose down
```

Model pulls:

```sh
docker exec -it tabletop-gpt-ollama ollama pull qwen3:8b
docker exec -it tabletop-gpt-ollama ollama pull llama3.2:3b
docker exec -it tabletop-gpt-ollama ollama pull nomic-embed-text
```

## Security Rules

- Use parameterized SQL only. Do not interpolate user input into SQL strings.
- Do not add arbitrary SQL/admin endpoints.
- Keep PostgreSQL, Redis, and Qdrant off public ports.
- Do not commit `.env`, PDFs, EPUBs, DOCX/XLSX files, character sheets, private notes, or copyrighted rulebooks.
- Use bcrypt/passlib for campaign passwords.
- Enforce input length limits at API boundaries.
- Render frontend user text with `textContent`, not raw `innerHTML`.
- Treat prompt-injection-like official actions as invalid input.

## DM Modes

Campaigns support:

- `llm_dm`
- `hybrid`
- `human_gm`

In `hybrid`, LLM output becomes a draft in `dm_drafts` until a human GM or owner approves or edits it. In `human_gm`, official narration must come from controlled application endpoints.

## RAG Boundaries

RAG should retrieve a small number of relevant chunks from user-provided lawful sources. It can support rules lookup, lore lookup, character references, house rules, item descriptions, and NPC/world knowledge. It must not mutate game state.

## Style

- Keep changes scoped and readable.
- Add TODOs for future production work instead of overbuilding.
- Prefer small modules with clear responsibilities.
- Preserve the documented folder structure unless a task explicitly changes it.
