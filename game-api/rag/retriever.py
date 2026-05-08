import os
from typing import Any

from qdrant_client import AsyncQdrantClient

from .embeddings import embed_text

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "campaign_knowledge")


async def retrieve(query: str, campaign_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    vector = await embed_text(query)
    client = AsyncQdrantClient(url=QDRANT_URL)
    # TODO: add a campaign_id filter once ingestion writes payload metadata.
    hits = await client.search(collection_name=QDRANT_COLLECTION, query_vector=vector, limit=min(limit, 5))
    return [{"score": hit.score, "payload": hit.payload} for hit in hits]
