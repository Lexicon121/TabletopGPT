import json
import os
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import campaigns
import db
import events
import gm_takeover
import llm_dm
import presence
import rules_engine
import security
import turn_manager

MAX_WS_MESSAGE_BYTES = 4096
MAX_ALLOWED_PLAYERS = int(os.getenv("MAX_ALLOWED_PLAYERS", "12"))

app = FastAPI(title=os.getenv("APP_NAME", "TabletopGPT"))
app.add_middleware(security.SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    owner_username: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=1000)
    password: str | None = Field(default=None, max_length=200)
    listed: bool = True
    max_players: int = Field(default=12, ge=1, le=12)
    dm_mode: Literal["llm_dm", "hybrid", "human_gm"] = "llm_dm"


class JoinRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    password: str | None = Field(default=None, max_length=200)


class CharacterCreate(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    sheet: dict = Field(default_factory=dict)


class ResolveRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)


class DmModeRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    dm_mode: Literal["llm_dm", "hybrid", "human_gm"]


class AskRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    question: str = Field(min_length=1, max_length=1000)
    mode: Literal["rules_help", "character_help", "campaign_recap", "lore", "scene_clarification", "app_help"]
    shared: bool = False


class TakeoverKeyRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    expires_minutes: int = Field(default=30, ge=5, le=120)


class ClaimGmRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    takeover_key: str = Field(min_length=10, max_length=200)


class HumanGmResolveRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    narration: str = Field(min_length=1, max_length=8000)


@app.on_event("startup")
async def startup():
    await db.connect()
    await db.install_schema()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"ok": True, "app": "TabletopGPT"}


@app.get("/api/campaigns")
async def list_campaigns():
    return await campaigns.list_campaigns()


@app.post("/api/campaigns")
async def create_campaign(payload: CampaignCreate):
    if payload.max_players > MAX_ALLOWED_PLAYERS:
        raise HTTPException(400, "max_players exceeds configured limit")
    return await campaigns.create_campaign(payload)


@app.post("/api/campaigns/{campaign_id}/join")
async def join_campaign(campaign_id: str, payload: JoinRequest):
    player = await campaigns.get_or_create_player(payload.username)
    campaign = await db.fetchrow("SELECT * FROM campaigns WHERE id = $1::uuid", campaign_id)
    if not campaign:
        raise HTTPException(404, "campaign not found")
    if not security.verify_password(payload.password or "", campaign["password_hash"]):
        raise HTTPException(403, "invalid campaign password")
    count = await db.fetchrow("SELECT count(*) AS count FROM campaign_members WHERE campaign_id = $1::uuid", campaign_id)
    if count["count"] >= campaign["max_players"]:
        raise HTTPException(409, "campaign is full")
    await db.execute(
        """
        INSERT INTO campaign_members (campaign_id, player_id, role)
        VALUES ($1::uuid, $2, 'player')
        ON CONFLICT DO NOTHING
        """,
        campaign_id,
        player["id"],
    )
    return {"joined": True, "campaign_id": campaign_id, "username": payload.username}


@app.post("/api/campaigns/{campaign_id}/characters")
async def create_character(campaign_id: str, payload: CharacterCreate):
    player = await security.require_member(campaign_id, payload.username)
    character = await db.fetchrow(
        """
        INSERT INTO characters (campaign_id, player_id, name, sheet)
        VALUES ($1::uuid, $2, $3, $4::jsonb)
        RETURNING *
        """,
        campaign_id,
        player["id"],
        security.clamp_text(payload.name, "name", 1, 80),
        json.dumps(payload.sheet),
    )
    return dict(character)


@app.get("/api/campaigns/{campaign_id}/characters")
async def get_characters(campaign_id: str):
    rows = await db.fetch(
        """
        SELECT c.id, c.name, c.hp, c.max_hp, c.temporary_hp, c.armor_class, c.status, p.username
        FROM characters c
        JOIN players p ON p.id = c.player_id
        WHERE c.campaign_id = $1::uuid
        ORDER BY c.created_at
        """,
        campaign_id,
    )
    return [dict(row) for row in rows]


@app.get("/api/campaigns/{campaign_id}/catchup/{username}")
async def catchup(campaign_id: str, username: str):
    player = await security.require_member(campaign_id, username)
    events_rows = await db.fetch(
        """
        SELECT id, round_number, event_type, body, metadata, created_at
        FROM game_events
        WHERE campaign_id = $1::uuid
        ORDER BY created_at DESC
        LIMIT 50
        """,
        campaign_id,
    )
    await db.execute(
        """
        INSERT INTO player_campaign_status (campaign_id, player_id, last_seen_at)
        VALUES ($1::uuid, $2, now())
        ON CONFLICT (campaign_id, player_id) DO UPDATE SET last_seen_at = now()
        """,
        campaign_id,
        player["id"],
    )
    return {"events": [dict(row) for row in reversed(events_rows)], "presence": presence.list_presence(campaign_id)}


@app.post("/api/campaigns/{campaign_id}/resolve-round")
async def resolve_round(campaign_id: str, payload: ResolveRequest):
    await security.require_member(campaign_id, payload.username, roles=("owner", "human_gm", "co_gm"))
    await turn_manager.enqueue_resolve_round(campaign_id, payload.username)
    return {"queued": True}


@app.post("/api/campaigns/{campaign_id}/dm-mode")
async def set_dm_mode(campaign_id: str, payload: DmModeRequest):
    player = await security.require_member(campaign_id, payload.username, roles=("owner", "human_gm", "co_gm"))
    await db.execute(
        """
        UPDATE campaigns
        SET dm_mode = $1::dm_mode,
            active_human_gm = CASE WHEN $1::dm_mode = 'human_gm'::dm_mode THEN $2 ELSE active_human_gm END,
            updated_at = now()
        WHERE id = $3::uuid
        """,
        payload.dm_mode,
        player["id"],
        campaign_id,
    )
    return {"dm_mode": payload.dm_mode}


@app.post("/api/campaigns/{campaign_id}/ask")
async def ask_dm(campaign_id: str, payload: AskRequest):
    await security.require_member(campaign_id, payload.username)
    answer = await llm_dm.answer_player_question(payload.question, payload.mode)
    return {"answer": answer, "mutated_state": False}


@app.post("/api/campaigns/{campaign_id}/gm-takeover-key")
async def create_gm_takeover_key(campaign_id: str, payload: TakeoverKeyRequest):
    key = await gm_takeover.create_takeover_key(campaign_id, payload.username, payload.expires_minutes)
    return {"takeover_key": key, "expires_minutes": payload.expires_minutes}


@app.post("/api/campaigns/{campaign_id}/claim-gm")
async def claim_gm(campaign_id: str, payload: ClaimGmRequest):
    try:
        event = await gm_takeover.claim_takeover(campaign_id, payload.username, payload.takeover_key)
    except ValueError as exc:
        raise HTTPException(403, str(exc)) from exc
    await events.broadcast(campaign_id, {"type": "game_event", "event": event})
    return {"claimed": True, "event": event}


@app.post("/api/campaigns/{campaign_id}/human-gm/resolve-round")
async def human_gm_resolve(campaign_id: str, payload: HumanGmResolveRequest):
    player = await security.require_member(campaign_id, payload.username, roles=("owner", "human_gm", "co_gm"))
    campaign = await db.fetchrow("SELECT current_round FROM campaigns WHERE id = $1::uuid", campaign_id)
    event = await db.fetchrow(
        """
        INSERT INTO game_events (campaign_id, round_number, event_type, body, created_by)
        VALUES ($1::uuid, $2, 'human_gm_narration', $3, $4)
        RETURNING *
        """,
        campaign_id,
        campaign["current_round"],
        security.clamp_text(payload.narration, "narration", 1, 8000),
        player["id"],
    )
    await db.execute(
        "UPDATE campaigns SET current_round = current_round + 1, phase = 'planning', status = 'active' WHERE id = $1::uuid",
        campaign_id,
    )
    await events.broadcast(campaign_id, {"type": "game_event", "event": dict(event)})
    return dict(event)


@app.websocket("/ws/{campaign_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, campaign_id: str, username: str):
    username = security.validate_username(username)
    await security.require_member(campaign_id, username)
    await events.connect(campaign_id, websocket)
    await events.broadcast(campaign_id, {"type": "presence", "users": presence.touch(campaign_id, username)})
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > MAX_WS_MESSAGE_BYTES:
                await websocket.send_json({"type": "error", "message": "message too large"})
                continue
            message = json.loads(raw)
            kind = message.get("type")
            if kind == "official_action":
                text = rules_engine.validate_official_action(message.get("text", ""))
                player = await security.require_member(campaign_id, username)
                campaign = await db.fetchrow("SELECT current_round, phase FROM campaigns WHERE id = $1::uuid", campaign_id)
                if campaign["phase"] != "planning":
                    await websocket.send_json({"type": "error", "message": "campaign is not accepting actions"})
                    continue
                await db.execute(
                    """
                    UPDATE action_submissions
                    SET active = false
                    WHERE campaign_id = $1::uuid AND player_id = $2 AND round_number = $3 AND active = true
                    """,
                    campaign_id,
                    player["id"],
                    campaign["current_round"],
                )
                await db.execute(
                    """
                    INSERT INTO action_submissions (campaign_id, player_id, round_number, action_text)
                    VALUES ($1::uuid, $2, $3, $4)
                    """,
                    campaign_id,
                    player["id"],
                    campaign["current_round"],
                    text,
                )
                await websocket.send_json({"type": "official_action_saved"})
            elif kind == "party_chat":
                text = security.clamp_text(message.get("text", ""), "chat", 1, 1000)
                await events.broadcast(campaign_id, {"type": "party_chat", "username": username, "text": text})
            elif kind == "presence":
                await events.broadcast(campaign_id, {"type": "presence", "users": presence.touch(campaign_id, username)})
    except WebSocketDisconnect:
        pass
    finally:
        events.disconnect(campaign_id, websocket)
        await events.broadcast(campaign_id, {"type": "presence", "users": presence.remove(campaign_id, username)})
