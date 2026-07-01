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

    try:
        return bcrypt.checkpw(password.encode(), r[0].encode())
    except Exception as e:
        print("🔥 BCRYPT ERROR:", e)
        return False


# ---------------- ROUTES ----------------

@app.get("/")
def root():
    return {"status": "ok"}


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


# ---------------- WEBSOCKET ----------------

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    print("\n🚀 WEBSOCKET ENTERED")
    print("🔌 ACCEPTED CONNECTION")

    try:
        print("⏳ WAITING FIRST MESSAGE...")

        raw = await websocket.receive_text()

        print("📩 RAW:", raw)

        try:
            data = json.loads(raw)
        except Exception as e:
            print("❌ JSON ERROR:", e)
            await websocket.close()
            return

        print("📦 PARSED:", data)

        action = data.get("action")
        user = data.get("user")
        password = data.get("password")

        print("🎯 ACTION:", action, "| USER:", user)

        # ---------------- REGISTER ----------------
        if action == "register":

            if user_exists(user):
                print("⚠️ USER EXISTS")
                await websocket.send_text("ERROR_USER_EXISTS")
                await websocket.close()
                return

            create_user(user, password)

            print("🟢 USER CREATED:", user)

            await websocket.send_text("REGISTER_OK")
            await websocket.close()
            return

        # ---------------- LOGIN ----------------
        if not check_login(user, password):
            print("❌ LOGIN FAILED:", user)
            await websocket.send_text("ERROR_LOGIN")
            await websocket.close()
            return

        async with clients_lock:
            clients.add(websocket)

        print("🟢 LOGIN OK:", user)
        print("👥 ONLINE:", len(clients))

        await websocket.send_text("OK_LOGIN")

        await broadcast(json.dumps({
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        }))

        # ---------------- CHAT LOOP ----------------
        while True:
            msg = await websocket.receive_text()

            print("💬 MSG:", user, "->", msg)

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
