from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

connections = set()

@app.get("/")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    print("🔌 CLIENT CONNECTED")

    user = None

    try:
        # ---------------- LOGIN ----------------
        raw = await websocket.receive_text()
        print("📩 RAW LOGIN:", raw)

        auth = json.loads(raw)

        username = auth.get("user")
        password = auth.get("password")

        if USERS_DB.get(username) != password:
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            print("❌ LOGIN FAILED")
            return

        user = username
        connections.add(websocket)

        await websocket.send_text("OK_LOGIN")
        print(f"✅ {user} LOGGED IN")

        # ---------------- CHAT LOOP ----------------
        while True:
            msg = await websocket.receive_text()
            print(f"📨 FROM {user}: {msg}")

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            for conn in list(connections):
                try:
                    await conn.send_text(data)
                except:
                    connections.discard(conn)

    except WebSocketDisconnect:
        print(f"❌ {user} DISCONNECTED")

    except Exception as e:
        print("⚠️ ERROR:", e)

    finally:
        if websocket in connections:
            connections.remove(websocket)
