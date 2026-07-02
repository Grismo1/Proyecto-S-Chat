print("######## VERSION NUEVA ########")
# servidor.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import sqlite3
import bcrypt

app = FastAPI()

clients = set()
lock = asyncio.Lock()

# ---------------- DB ----------------

def init_db():
    conn = sqlite3.connect("chat.db")
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

def user_exists(u):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=?", (u,))
    r = cur.fetchone()
    conn.close()
    return r is not None

def create_user(u, p):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    cur.execute("INSERT INTO users VALUES (?,?)", (u, hashed))
    conn.commit()
    conn.close()

def check_login(u, p):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (u,))
    r = cur.fetchone()
    conn.close()

    if not r:
        return False
    return bcrypt.checkpw(p.encode(), r[0].encode())


# ---------------- BROADCAST ----------------

async def broadcast(data):
    msg = json.dumps(data)
    async with lock:
        dead = []
        for c in clients:
            try:
                await c.send_text(msg)
            except:
                dead.append(c)

        for d in dead:
            clients.discard(d)


# ---------------- WS ----------------

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()

    user = None

    try:
        raw = await ws.receive_text()
        data = json.loads(raw)

        action = data.get("action")
        user = data.get("user")
        password = data.get("password")

        if action == "register":
            if user_exists(user):
                await ws.send_text("ERROR_USER_EXISTS")
                return
            create_user(user, password)
            await ws.send_text("REGISTER_OK")
            return

        if not check_login(user, password):
            await ws.send_text("ERROR_LOGIN")
            return

        async with lock:
            clients.add(ws)

        await ws.send_text("OK_LOGIN")

        await broadcast({
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        })

        while True:
    raw = await ws.receive_text()

    try:
        data = json.loads(raw)

        if isinstance(data, dict):
            texto = data.get("msg", "")
        else:
            texto = raw

    except Exception:
        texto = raw

    await broadcast({
        "user": user,
        "msg": texto
    })

    except WebSocketDisconnect:
        pass

    finally:
        async with lock:
            clients.discard(ws)

        if user:
            await broadcast({
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            })
