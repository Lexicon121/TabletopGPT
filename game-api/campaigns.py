import db
import security


async def get_or_create_player(username: str):
    username = security.validate_username(username)
    return await db.fetchrow(
        """
        INSERT INTO players (username)
        VALUES ($1)
        ON CONFLICT (username) DO UPDATE SET username = EXCLUDED.username
        RETURNING id, username
        """,
        username,
    )


async def list_campaigns():
    rows = await db.fetch(
        """
        SELECT id, name, description, listed, max_players, status, phase, dm_mode, current_round, created_at
        FROM campaigns
        WHERE listed = true AND status <> 'archived'
        ORDER BY created_at DESC
        LIMIT 100
        """
    )
    return [dict(row) for row in rows]


async def create_campaign(payload):
    owner = await get_or_create_player(payload.owner_username)
    password_hash = security.hash_password(payload.password) if payload.password else None
    campaign = await db.fetchrow(
        """
        INSERT INTO campaigns (name, description, password_hash, listed, max_players, dm_mode, created_by)
        VALUES ($1, $2, $3, $4, $5, $6::dm_mode, $7)
        RETURNING *
        """,
        security.clamp_text(payload.name, "name", 3, 80),
        (payload.description or "")[:1000],
        password_hash,
        payload.listed,
        payload.max_players,
        payload.dm_mode,
        owner["id"],
    )
    await db.execute(
        "INSERT INTO campaign_members (campaign_id, player_id, role) VALUES ($1, $2, 'owner')",
        campaign["id"],
        owner["id"],
    )
    return dict(campaign)
