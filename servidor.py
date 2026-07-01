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
    await websocket.accept()
    print("🔌 CLIENT CONNECTED")

    user = None

    try:
        # ---------------- LOGIN ----------------
        raw = await websocket.receive_text()
        print("LOGIN RAW:", raw)

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
        print(f"✅ LOGIN OK: {user}")

        # 🔥 IMPORTANTE: confirmación de loop activo
        await websocket.send_text("CHAT_READY")

        # ---------------- CHAT LOOP ----------------
        while True:
            try:
                msg = await websocket.receive_text()
                print(f"📨 MSG FROM {user}: {msg}")

                data = json.dumps({
                    "user": user,
                    "msg": msg
                })

                for c in list(clients):
                    try:
                        await c.send_text(data)
                    except Exception as e:
                        print("❌ REMOVE CLIENT:", e)
                        clients.discard(c)

            except Exception as e:
                print("⚠️ LOOP ERROR:", e)
                break

    except WebSocketDisconnect:
        print(f"❌ DISCONNECT {user}")

    except Exception as e:
        print("🔥 FATAL ERROR:", e)

    finally:
        clients.discard(websocket)
        print("🧹 CLEANUP DONE")
