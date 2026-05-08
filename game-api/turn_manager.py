import json

import db
import llm_dm
import rules_engine


async def enqueue_resolve_round(campaign_id: str, username: str):
    await db.execute(
        """
        INSERT INTO campaign_jobs (campaign_id, job_type, payload)
        VALUES ($1::uuid, 'resolve_round', jsonb_build_object('requested_by', $2))
        ON CONFLICT DO NOTHING
        """,
        campaign_id,
        username,
    )


async def process_resolve_round(campaign_id: str) -> None:
    async with db.pool().acquire() as conn:
        campaign = await conn.fetchrow("SELECT * FROM campaigns WHERE id = $1::uuid", campaign_id)
        if not campaign:
            raise ValueError("campaign not found")
        await conn.execute("UPDATE campaigns SET phase = 'resolving' WHERE id = $1::uuid", campaign_id)
        actions = await conn.fetch(
            """
            SELECT a.id, a.action_text, p.id AS player_id, p.username
            FROM action_submissions a
            JOIN players p ON p.id = a.player_id
            WHERE a.campaign_id = $1::uuid AND a.round_number = $2 AND a.active = true
            ORDER BY a.created_at
            """,
            campaign_id,
            campaign["current_round"],
        )

        resolved = []
        for action in actions:
            result = rules_engine.resolve_action(action["action_text"])
            roll = result["roll"]
            await conn.execute(
                """
                INSERT INTO dice_rolls (campaign_id, action_submission_id, player_id, notation, rolls, modifier, total, purpose)
                VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7, 'official_action')
                """,
                campaign_id,
                action["id"],
                action["player_id"],
                roll["notation"],
                json.dumps(roll["rolls"]),
                roll["modifier"],
                roll["total"],
            )
            await conn.execute(
                "UPDATE action_submissions SET validated = true, resolution = $1::jsonb WHERE id = $2",
                json.dumps(result),
                action["id"],
            )
            resolved.append(
                {
                    "username": action["username"],
                    "action_text": action["action_text"],
                    "total": roll["total"],
                }
            )

        await conn.execute("UPDATE campaigns SET phase = 'narrating' WHERE id = $1::uuid", campaign_id)

    narration = await llm_dm.narrate_round(dict(campaign), resolved) if campaign["dm_mode"] != "human_gm" else ""

    async with db.pool().acquire() as conn:
        async with conn.transaction():
            if campaign["dm_mode"] == "hybrid":
                await conn.execute(
                    """
                    INSERT INTO dm_drafts (campaign_id, round_number, draft_body)
                    VALUES ($1::uuid, $2, $3)
                    """,
                    campaign_id,
                    campaign["current_round"],
                    narration or "No narration generated.",
                )
                await conn.execute("UPDATE campaigns SET phase = 'paused' WHERE id = $1::uuid", campaign_id)
            elif campaign["dm_mode"] == "human_gm":
                await conn.execute("UPDATE campaigns SET phase = 'paused' WHERE id = $1::uuid", campaign_id)
            else:
                await conn.execute(
                    """
                    INSERT INTO game_events (campaign_id, round_number, event_type, body, metadata)
                    VALUES ($1::uuid, $2, 'round_narration', $3, $4::jsonb)
                    """,
                    campaign_id,
                    campaign["current_round"],
                    narration or "The round resolves quietly.",
                    json.dumps({"actions": resolved}),
                )
                await conn.execute(
                    """
                    UPDATE campaigns
                    SET current_round = current_round + 1, phase = 'planning', status = 'active', updated_at = now()
                    WHERE id = $1::uuid
                    """,
                    campaign_id,
                )
