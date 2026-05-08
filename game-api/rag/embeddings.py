import os

import httpx

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


async def embed_text(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{LLM_BASE_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]
