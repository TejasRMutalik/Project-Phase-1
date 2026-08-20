import os

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "configs", "default.yaml"
)
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Set by main.py's startup event. Routers read these as module attributes
# (shared.pipeline, not `from shared import pipeline`) so they see the real
# values once startup runs, not the None each was initialized with here.
pipeline = None
MAIN_LOOP = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: list = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()
