from fastapi import FastAPI, WebSocket
import json

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

CONNECTED = set()

@app.get("/")
def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        auth = json.loads(await websocket.receive_text())

        username = auth.get("user", "").strip()
        password = auth.get("password", "").strip()

        if USERS_DB.get(username) != password:
            await websocket.send_text("ERROR_LOGIN")
            return

        user = username
        CONNECTED.add(websocket)

        await websocket.send_text("OK_LOGIN")

        while True:
            msg = await websocket.receive_text()

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            # 🔥 COPY LIST para evitar errores durante iteración
            for conn in list(CONNECTED):
                try:
                    await conn.send_text(data)
                except:
                    CONNECTED.remove(conn)

    except:
        pass

    finally:
        if websocket in CONNECTED:
            CONNECTED.remove(websocket)
