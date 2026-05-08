import os
from pathlib import Path
from typing import Any

import httpx

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
ASK_MODEL = os.getenv("ASK_MODEL", "llama3.2:3b")

BOUNDARY = """
You may narrate scenes, roleplay NPCs, summarize context, and suggest possible state updates.
You may not alter HP, damage, inventory, conditions, dice, campaign membership, or campaign truth.
The backend is authoritative. Never claim that you rolled dice.
"""


def _prompt(name: str) -> str:
    path = Path(__file__).parent / "prompts" / name
    return path.read_text(encoding="utf-8")


async def call_ollama(prompt: str, model: str | None = None, system: str | None = None) -> str:
    payload: dict[str, Any] = {
        "model": model or LLM_MODEL,
        "prompt": prompt,
        "system": system or BOUNDARY,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{LLM_BASE_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("response", "").strip()


async def narrate_round(campaign: dict, actions: list[dict], rag_chunks: list[str] | None = None) -> str:
    system = _prompt("dm_system.txt") + "\n" + BOUNDARY
    context = "\n".join(f"- {chunk}" for chunk in (rag_chunks or [])[:5])
    action_lines = "\n".join(
        f"- {item['username']}: {item['action_text']} | roll total {item['total']}" for item in actions
    )
    prompt = f"""
Campaign: {campaign.get('name')}
Round: {campaign.get('current_round')}

Relevant context:
{context or 'No retrieved context.'}

Resolved player actions:
{action_lines or 'No active actions.'}

Write one concise official narration for this resolved round.
"""
    return await call_ollama(prompt, model=LLM_MODEL, system=system)


async def answer_player_question(question: str, mode: str, rag_chunks: list[str] | None = None) -> str:
    system = _prompt("ask_dm.txt") + "\n" + BOUNDARY
    context = "\n".join(f"- {chunk}" for chunk in (rag_chunks or [])[:5])
    prompt = f"""
Ask mode: {mode}
Relevant context:
{context or 'No retrieved context.'}

Question:
{question}

Answer helpfully without changing game state.
"""
    return await call_ollama(prompt, model=ASK_MODEL, system=system)
