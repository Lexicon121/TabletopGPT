import secrets
from datetime import datetime, timedelta, timezone

import db
import security


async def create_takeover_key(campaign_id: str, created_by: str, expires_minutes: int = 30) -> str:
    player = await security.require_member(campaign_id, created_by, roles=("owner", "human_gm", "co_gm"))
    raw_key = secrets.token_urlsafe(24)
    key_hash = security.hash_password(raw_key)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    await db.execute(
        """
        INSERT INTO gm_takeover_keys (campaign_id, key_hash, expires_at, created_by)
        VALUES ($1::uuid, $2, $3, $4)
        """,
        campaign_id,
        key_hash,
        expires_at,
        player["id"],
    )
    return raw_key


async def claim_takeover(campaign_id: str, username: str, takeover_key: str):
    player = await campaigns_player(username)
    rows = await db.fetch(
        """
        SELECT id, key_hash
        FROM gm_takeover_keys
        WHERE campaign_id = $1::uuid AND used_at IS NULL AND expires_at > now()
        ORDER BY created_at DESC
        """,
        campaign_id,
    )
    matched = next((row for row in rows if security.verify_password(takeover_key, row["key_hash"])), None)
    if not matched:
        raise ValueError("invalid or expired takeover key")

    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE gm_takeover_keys
                SET used_at = now(), claimed_by = $1
                WHERE id = $2 AND used_at IS NULL
                """,
                player["id"],
                matched["id"],
            )
            await conn.execute(
                """
                INSERT INTO campaign_members (campaign_id, player_id, role)
                VALUES ($1::uuid, $2, 'human_gm')
                ON CONFLICT (campaign_id, player_id) DO UPDATE SET role = 'human_gm'
                """,
                campaign_id,
                player["id"],
            )
            await conn.execute(
                """
                UPDATE campaigns
                SET dm_mode = 'human_gm', active_human_gm = $1, updated_at = now()
                WHERE id = $2::uuid
                """,
                player["id"],
                campaign_id,
            )
            event = await conn.fetchrow(
                """
                INSERT INTO game_events (campaign_id, round_number, event_type, body, created_by)
                SELECT id, current_round, 'gm_takeover', $2, $3
                FROM campaigns
                WHERE id = $1::uuid
                RETURNING *
                """,
                campaign_id,
                f"{username} claimed emergency human GM control.",
                player["id"],
            )
    return dict(event)


async def campaigns_player(username: str):
    player = await db.fetchrow(
        """
        INSERT INTO players (username)
        VALUES ($1)
        ON CONFLICT (username) DO UPDATE SET username = EXCLUDED.username
        RETURNING id, username
        """,
        security.validate_username(username),
    )
    return player
