from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

connections = set()

@app.get("/")
def home():
    return {"status": "ok"}

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        auth = json.loads(await websocket.receive_text())

        username = auth.get("user")
        password = auth.get("password")

        if USERS_DB.get(username) != password:
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        user = username
        connections.add(websocket)

        await websocket.send_text("OK_LOGIN")
        print(user, "connected")

        while True:
            msg = await websocket.receive_text()

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            for conn in list(connections):
                try:
                    await conn.send_text(data)
                except:
                    connections.remove(conn)

    except WebSocketDisconnect:
        pass

    finally:
        connections.discard(websocket)
