from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

clients = set()


@app.get("/")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    print("🔥 ENTERED WEBSOCKET HANDLER")

    await websocket.accept()
    print("🔌 ACCEPTED CONNECTION")

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
            print("❌ LOGIN FAILED")
            return

        clients.add(websocket)

        await websocket.send_text("OK_LOGIN")
        await websocket.send_text("CHAT_READY")

        print(f"✅ LOGIN OK: {user}")

        while True:
            print("⏳ WAITING MESSAGE...")

            msg = await websocket.receive_text()

            print(f"📨 RECEIVED: {msg}")

            data = json.dumps({
                "user": user,
                "msg": msg
            })

            print("📤 BROADCAST:", data)

            for c in list(clients):
                try:
                    await c.send_text(data)
                except Exception as e:
                    print("❌ SEND ERROR:", e)
                    clients.discard(c)

    except WebSocketDisconnect:
        print(f"❌ DISCONNECTED: {user}")

    except Exception as e:
        print("🔥 SERVER ERROR:", repr(e))

    finally:
        clients.discard(websocket)
        print("🧹 CLEANUP DONE")
