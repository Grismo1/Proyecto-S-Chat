from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

active_connections = {}  # username -> websocket


@app.get("/")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        # LOGIN
        auth = json.loads(await websocket.receive_text())

        username = auth.get("user", "")
        password = auth.get("password", "")

        if USERS_DB.get(username) != password:
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        if username in active_connections:
            await websocket.send_text("ERROR_ALREADY_LOGGED")
            await websocket.close()
            return

        user = username
        active_connections[user] = websocket

        await websocket.send_text("OK_LOGIN")

        print(f"{user} conectado")

        # LOOP DE MENSAJES
        while True:
            msg = await websocket.receive_text()

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            # broadcast seguro
            disconnected = []

            for u, conn in active_connections.items():
                try:
                    await conn.send_text(data)
                except:
                    disconnected.append(u)

            for u in disconnected:
                active_connections.pop(u, None)

    except WebSocketDisconnect:
        print(f"{user} desconectado")

    finally:
        if user in active_connections:
            active_connections.pop(user, None)
