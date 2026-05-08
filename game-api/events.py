from collections import defaultdict

from fastapi import WebSocket

_connections: dict[str, set[WebSocket]] = defaultdict(set)


async def connect(campaign_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    _connections[campaign_id].add(websocket)


def disconnect(campaign_id: str, websocket: WebSocket) -> None:
    _connections[campaign_id].discard(websocket)


async def broadcast(campaign_id: str, message: dict) -> None:
    dead = []
    for websocket in list(_connections[campaign_id]):
        try:
            await websocket.send_json(message)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        disconnect(campaign_id, websocket)
