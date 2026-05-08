# Project Spec

## Name

TabletopGPT

## Tagline

A self-hosted multiplayer tabletop RPG engine powered by local LLMs.

## Target Hosts

Primary target:

- Gaming PC
- 11th Gen Intel CPU
- 32 GB DDR4 RAM
- RTX 3060 8GB GPU
- Docker Compose
- Ollama with NVIDIA GPU support

Secondary target:

- Steam Deck as lightweight/demo host or browser client
- Do not optimize Steam Deck as the main LLM host

## Core Architecture

- FastAPI backend
- WebSocket multiplayer
- PostgreSQL
- Redis
- Qdrant for RAG vector search
- Ollama for local LLMs and embeddings
- Docker Compose
- Simple static frontend first
- React frontend later

## Model Guidance

- Main DM model: `qwen3:8b` or `llama3.1:8b`
- Ask-the-DM helper model: `llama3.2:3b`
- Embedding model: `nomic-embed-text`
- Optional embedding upgrade: `mxbai-embed-large`

The main DM generates one narration per resolved round. It must not generate one response per player action. Ask-the-DM queries are read-only, queueable/rate-limitable, and may use the smaller helper model. RAG retrieval includes a few relevant chunks, never entire PDFs.

## Campaign Features

- Multiple campaigns
- Campaign list and campaign creation
- Optional campaign password
- Listed and unlisted campaigns
- Up to 12 users per campaign/session
- Member roles: `owner`, `human_gm`, `co_gm`, `player`, `spectator`
- Campaign statuses: `draft`, `active`, `paused`, `completed`, `failed`, `total_party_kill`, `archived`
- DM modes: `llm_dm`, `hybrid`, `human_gm`

## Turn Flow

1. Campaign is in planning phase.
2. Players submit/update one official action.
3. Server validates actions.
4. Server rolls dice.
5. Server resolves mechanics.
6. Depending on DM mode:
   - `llm_dm`: LLM narration becomes official.
   - `hybrid`: LLM narration becomes a draft.
   - `human_gm`: human GM writes narration.
7. Official event is saved.
8. Players receive update.
9. Next round begins.

## Action Control

- One active official action per player per round.
- New action replaces old active action before resolution.
- Chat is separate from official actions.
- Presence is separate from event log.
- One pending resolve job per campaign.
- Background worker handles LLM calls.
- Campaign phases: `planning`, `resolving`, `narrating`, `paused`, `completed`, `failed`.

## Human GM Takeover

Emergency takeover keys are generated as temporary secrets, stored only as hashes, expire, are single-use, and produce audit events when claimed. Claiming switches the campaign to `human_gm`. Human GM controls must go through controlled endpoints and never arbitrary SQL/admin access.

## Database Scope

The schema includes players, campaigns, campaign members, characters, character conditions, world states, action submissions, dice rolls, game events, player campaign status, campaign summaries, campaign jobs, DM drafts, GM takeover keys, knowledge sources, and knowledge chunks.

Optional RLS scaffolding is included as comments for future hardening but does not block the first scaffold from running.
