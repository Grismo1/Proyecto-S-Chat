from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import sqlite3
import bcrypt
import traceback

app = FastAPI()

DB_NAME = "chat.db"

clients = set()
clients_lock = asyncio.Lock()


# ---------------- DB ----------------

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

    return bcrypt.checkpw(password.encode(), r[0].encode())


# ---------------- BROADCAST ----------------

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


# ---------------- WS ----------------

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        # ---------------- LOGIN FIRST MESSAGE ----------------
        raw = await websocket.receive_text()
        data = json.loads(raw)

        action = data.get("action")
        user = data.get("user")
        password = data.get("password")

        # ---------------- REGISTER ----------------
        if action == "register":
            if user_exists(user):
                await websocket.send_text("ERROR_USER_EXISTS")
                await websocket.close()
                return

            create_user(user, password)

            await websocket.send_text("REGISTER_OK")
            return  # ❗ no cerrar socket duro en algunos browsers

        # ---------------- LOGIN ----------------
        if not check_login(user, password):
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        async with clients_lock:
            clients.add(websocket)

        await websocket.send_text("OK_LOGIN")

        await broadcast(json.dumps({
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        }))

        # ---------------- CHAT LOOP ----------------
        while True:
            msg = await websocket.receive_text()

            await broadcast(json.dumps({
                "user": user,
                "msg": msg
            }))

    except WebSocketDisconnect:
        pass

    except Exception:
        traceback.print_exc()

    finally:
        async with clients_lock:
            clients.discard(websocket)

        if user:
            await broadcast(json.dumps({
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            }))
