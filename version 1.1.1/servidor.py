from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import sqlite3
import bcrypt
import traceback

print("🔥 SERVER ONLINE - FIXED VERSION")

app = FastAPI()

DB_NAME = "chat.db"

clients = set()
clients_lock = asyncio.Lock()


# ======================================================
# DB INIT
# ======================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

init_db()


def user_exists(username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE username=?", (username,))
    r = cur.fetchone()

    conn.close()
    return r is not None


def create_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cur.execute(
        "INSERT INTO users(username,password) VALUES(?,?)",
        (username, hashed)
    )

    conn.commit()
    conn.close()


def check_login(username, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    r = cur.fetchone()

    conn.close()

    if not r:
        return False

    try:
        return bcrypt.checkpw(password.encode(), r[0].encode())
    except Exception as e:
        print("🔥 BCRYPT ERROR:", e)
        return False


# ======================================================
# BROADCAST
# ======================================================
async def broadcast(msg: str):
    dead = []

    async with clients_lock:
        for c in clients:
            try:
                await c.send_text(msg)
            except:
                dead.append(c)

        for d in dead:
            clients.discard(d)


# ======================================================
# WEBSOCKET (FIX REAL)
# ======================================================
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    print("\n🚀 NEW CONNECTION OPENED")

    try:
        async with clients_lock:
            clients.add(websocket)

        while True:
            raw = await websocket.receive_text()
            print("📩 RAW:", raw)

            try:
                data = json.loads(raw)
            except:
                print("❌ INVALID JSON")
                continue

            action = data.get("action")

            # ---------------- REGISTER ----------------
            if action == "register":
                username = data.get("user")
                password = data.get("password")

                if not username or not password:
                    await websocket.send_text("ERROR_MISSING_FIELDS")
                    continue

                if user_exists(username):
                    await websocket.send_text("ERROR_USER_EXISTS")
                    continue

                create_user(username, password)

                print("🟢 REGISTER OK:", username)

                await websocket.send_text("REGISTER_OK")
                continue

            # ---------------- LOGIN ----------------
            if action == "login":
                username = data.get("user")
                password = data.get("password")

                if not check_login(username, password):
                    await websocket.send_text("ERROR_LOGIN")
                    continue

                user = username

                await websocket.send_text("OK_LOGIN")

                print("🟢 LOGIN OK:", user)

                await broadcast(json.dumps({
                    "user": "SYSTEM",
                    "msg": f"{user} se conectó"
                }))
                continue

            # ---------------- CHAT MESSAGE ----------------
            if not user:
                await websocket.send_text("ERROR_NOT_LOGGED")
                continue

            msg = data.get("msg")

            if not msg:
                continue

            print(f"💬 CHAT: {user} -> {msg}")

            await broadcast(json.dumps({
                "user": user,
                "msg": msg
            }))

    except WebSocketDisconnect:
        print("❌ DISCONNECT:", user)

    except Exception as e:
        print("🔥 SERVER ERROR:")
        print(e)
        traceback.print_exc()

    finally:
        async with clients_lock:
            clients.discard(websocket)

        if user:
            await broadcast(json.dumps({
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            }))

        print("🧹 CLEANUP DONE")
