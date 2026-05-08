import os
from pathlib import Path

import asyncpg

_pool: asyncpg.Pool | None = None


def database_url() -> str:
    user = os.getenv("POSTGRES_USER", "game")
    password = os.getenv("POSTGRES_PASSWORD", "change-this-password")
    db = os.getenv("POSTGRES_DB", "tabletop_gpt")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    return os.getenv("DATABASE_URL", f"postgresql://{user}:{password}@{host}:{port}/{db}")


async def connect() -> None:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(database_url(), min_size=1, max_size=10)


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool has not been initialized")
    return _pool


async def install_schema() -> None:
    schema = Path(__file__).with_name("models.sql").read_text(encoding="utf-8")
    async with pool().acquire() as conn:
        await conn.execute(schema)


async def fetch(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.execute(query, *args)
