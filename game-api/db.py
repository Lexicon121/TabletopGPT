import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import asyncpg

_pool: asyncpg.Pool | None = None


def database_url() -> str:
    user = os.getenv("POSTGRES_USER", "game")
    password = os.getenv("POSTGRES_PASSWORD", "change-this-password")
    db = os.getenv("POSTGRES_DB", "tabletop_gpt")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    return os.getenv("DATABASE_URL", f"postgresql://{user}:{password}@{host}:{port}/{db}")


def _validate_database_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid database name: {name}")
    return name


async def _ensure_database_exists() -> None:
    url = database_url()
    parsed = urlparse(url)
    target_db = parsed.path.lstrip("/")
    if not target_db:
        raise ValueError("Database URL must contain a target database")
    _validate_database_name(target_db)

    host = parsed.hostname or os.getenv("POSTGRES_HOST", "postgres")
    port = parsed.port or int(os.getenv("POSTGRES_PORT", "5432"))
    user = parsed.username or os.getenv("POSTGRES_USER", "game")
    password = parsed.password or os.getenv("POSTGRES_PASSWORD", "change-this-password")
    maintenance_db = "postgres"

    conn = await asyncpg.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=maintenance_db,
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            target_db,
        )
        if not exists:
            await conn.execute(f"CREATE DATABASE {target_db}")
    finally:
        await conn.close()


async def connect(max_retries: int = 20, initial_delay: float = 1.0, max_delay: float = 5.0) -> None:
    global _pool
    if _pool is not None:
        return

    attempt = 0
    last_exc: Exception | None = None
    while attempt < max_retries:
        try:
            await _ensure_database_exists()
            _pool = await asyncpg.create_pool(database_url(), min_size=1, max_size=10)
            return
        except (OSError, ConnectionRefusedError, asyncpg.PostgresError, ValueError) as exc:
            last_exc = exc
            attempt += 1
            wait = min(initial_delay * attempt, max_delay)
            print(f"Database not ready yet, retrying in {wait:.1f}s ({attempt}/{max_retries})...")
            await asyncio.sleep(wait)

    raise RuntimeError(
        f"Unable to connect to database after {max_retries} attempts: {last_exc}"
    ) from last_exc


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
        await conn.execute("SELECT pg_advisory_lock(907651234)")
        try:
            await conn.execute(schema)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(907651234)")


async def fetch(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args):
    async with pool().acquire() as conn:
        return await conn.execute(query, *args)
