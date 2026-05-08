from pathlib import Path

from pypdf import PdfReader

from .chunk_text import chunk_text


def extract_pdf_text(path: str | Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_pdf(path: str | Path) -> list[str]:
    return chunk_text(extract_pdf_text(path))


async def ingest_pdf(path: str | Path, campaign_id: str | None = None) -> dict:
    # TODO: write knowledge_sources/chunks rows, embed chunks, and upsert Qdrant points.
    chunks = chunk_pdf(path)
    return {"campaign_id": campaign_id, "chunks": len(chunks), "path": str(path)}
