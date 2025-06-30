from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Set
import asyncio

connected_rollover_clients: Set[WebSocket] = set()

router = APIRouter()

@router.websocket("/api/rollover-updates")
async def rollover_updates_ws(websocket: WebSocket):
    await websocket.accept()
    connected_rollover_clients.add(websocket)
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        connected_rollover_clients.remove(websocket)

async def broadcast_rollover_update(message: dict):
    disconnected = set()
    for ws in connected_rollover_clients:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        connected_rollover_clients.remove(ws) 