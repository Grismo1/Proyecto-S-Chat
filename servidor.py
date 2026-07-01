ffrom fastapi import FastAPI, WebSocket
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


async def broadcast(message: str, sender_ws: WebSocket):
    """
    Envía mensaje a todos menos al que lo envió (opcional mejora)
    """
    for conn in list(CONNECTED):
        try:
            await conn.send_text(message)
        except:
            CONNECTED.discard(conn)


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        # 1. LOGIN (primer mensaje obligatorio)
        auth_raw = await websocket.receive_text()
        auth = json.loads(auth_raw)

        username = auth.get("user", "").strip()
        password = auth.get("password", "").strip()

        # validación segura
        if USERS_DB.get(username) != password:
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        user = username
        CONNECTED.add(websocket)

        await websocket.send_text("OK_LOGIN")

        print(f"[LOGIN] {user}")

        # 2. LOOP PRINCIPAL
        while True:
            msg = await websocket.receive_text()

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            print(f"[MSG] {user}: {msg}")

            # 🔥 broadcast real a todos los clientes
            await broadcast(data, websocket)

    except Exception as e:
        print("[ERROR]", repr(e))

    finally:
        CONNECTED.discard(websocket)
        print(f"[DISCONNECT] {user}")
