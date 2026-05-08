# Security

TabletopGPT starts as a local-first scaffold. Do not expose it directly to the public internet.

## Network

- Run on a trusted LAN or behind a private VPN.
- Do not expose PostgreSQL, Redis, or Qdrant publicly.
- Ollama is exposed only for local development convenience.

## Data

- Do not commit `.env`.
- Do not commit PDFs, EPUBs, DOCX/XLSX files, character sheets, private notes, or copyrighted tabletop material.
- Knowledge files under `data/knowledge/` are for local user-provided sources.

## Application Patterns

- Use parameterized SQL only.
- Do not add arbitrary SQL/admin endpoints.
- Hash campaign passwords with bcrypt/passlib.
- Enforce input length limits.
- Enforce WebSocket message size limits.
- Render user-generated frontend text with `textContent`, never raw `innerHTML`.
- Reject prompt-injection-like official actions before resolution.
- Keep Ask the DM read-only with respect to game state.

## LLM Boundary

The LLM may narrate, roleplay NPCs, answer read-only questions, and suggest state updates. It may not alter HP, damage, inventory, conditions, dice, membership, or campaign truth. The backend is authoritative.

## Future Hardening

- Add real authentication and sessions.
- Add authorization tests for every campaign-scoped endpoint.
- Wire PostgreSQL RLS with per-request context.
- Add TLS/reverse proxy guidance.
- Add backups, audit review tools, and rate limiting.
