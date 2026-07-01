from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import sqlite3

app = FastAPI()

DB_NAME = "chat.db"

clients = set()
clients_lock = asyncio.Lock()


# ---------------- DATABASE ----------------

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


def user_exists(username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT username FROM users WHERE username=?",
        (username,)
    )

    result = cur.fetchone()

    conn.close()

    return result is not None


def create_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users(username,password) VALUES(?,?)",
        (username, password)
    )

    conn.commit()
    conn.close()


def check_login(username, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return False

    return row[0] == password


init_db()


# ---------------- HEALTH ----------------

@app.get("/")
def health():
    return {"status": "ok"}


# ---------------- BROADCAST ----------------

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

        auth = json.loads(raw)

        action = auth.get("action")
        user = auth.get("user")
        password = auth.get("password")

        # -------- REGISTER --------

        if action == "register":

            if not user or not password:
                await websocket.send_text("ERROR_INVALID_DATA")
                await websocket.close()
                return

            if user_exists(user):
                await websocket.send_text("ERROR_USER_EXISTS")
                await websocket.close()
                return

            create_user(user, password)

            print(f"✅ USER CREATED: {user}")

            await websocket.send_text("REGISTER_OK")
            await websocket.close()
            return

        # -------- LOGIN --------

        if not check_login(user, password):
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        async with clients_lock:
            clients.add(websocket)

        print(f"✅ LOGIN OK: {user}")
        print(f"👥 ONLINE: {len(clients)}")

        await websocket.send_text("OK_LOGIN")

        await broadcast(json.dumps({
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        }))

        while True:

            msg = await websocket.receive_text()

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

        if user:
            await broadcast(json.dumps({
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            }))

        print("🧹 CLEANUP DONE")
