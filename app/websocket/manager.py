
from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self.connections = defaultdict(list)

    async def connect(self, queue_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[queue_id].append(websocket)

    def disconnect(self, queue_id: int, websocket: WebSocket):
        if websocket in self.connections[queue_id]:
            self.connections[queue_id].remove(websocket)

    async def broadcast(self, queue_id: int, message: dict):
        for connection in self.connections[queue_id][:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(queue_id, connection)


manager = ConnectionManager()
