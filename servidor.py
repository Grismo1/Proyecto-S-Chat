from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

clients = set()
clients_lock = asyncio.Lock()


@app.get("/")
def health():
    return {"status": "ok"}


# ---------------- BROADCAST SEGURO ----------------
async def broadcast(data: str):
    dead = []

    async with clients_lock:
        for c in clients:
            try:
                await c.send_text(data)
            except:
                dead.append(c)

        for d in dead:
            clients.discard(d)


# ---------------- WEBSOCKET ----------------
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        raw = await websocket.receive_text()
        print("📩 LOGIN RAW:", raw)

        auth = json.loads(raw)

        user = auth.get("user")
        password = auth.get("password")

        if USERS_DB.get(user) != password:
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        async with clients_lock:
            clients.add(websocket)

        print(f"✅ LOGIN OK: {user}")
        print(f"👥 CLIENTS ONLINE: {len(clients)}")

        await websocket.send_text("OK_LOGIN")

        while True:
            msg = await websocket.receive_text()
            print(f"📨 {user}: {msg}")

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            await broadcast(data)

    except WebSocketDisconnect:
        print(f"❌ DISCONNECTED: {user}")

    except Exception as e:
        print("🔥 SERVER ERROR:", repr(e))

    finally:
        async with clients_lock:
            clients.discard(websocket)

        print("🧹 CLEANUP DONE")
