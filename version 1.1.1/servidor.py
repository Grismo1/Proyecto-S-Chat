from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import sqlite3
import bcrypt

app = FastAPI()

clients = set()
lock = asyncio.Lock()

DB = "chat.db"

# ================= DB =================
def init():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init()

def create_user(u, p):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    cur.execute("INSERT INTO users VALUES(?,?)", (u, hashed))
    conn.commit()
    conn.close()

def check_user(u, p):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (u,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    return bcrypt.checkpw(p.encode(), row[0].encode())

# ================= BROADCAST =================
async def broadcast(msg):
    dead = []

    async with lock:
        for c in clients:
            try:
                await c.send_text(json.dumps(msg))
            except:
                dead.append(c)

        for d in dead:
            clients.discard(d)

# ================= WS =================
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)

        action = data.get("action")
        user = data.get("user")
        password = data.get("password")

        # REGISTER
        if action == "register":
            create_user(user, password)

            await websocket.send_text(json.dumps({
                "type": "system",
                "msg": "REGISTER_OK"
            }))
            await websocket.close()
            return

        # LOGIN
        if not check_user(user, password):
            await websocket.send_text(json.dumps({
                "type": "system",
                "msg": "ERROR_LOGIN"
            }))
            await websocket.close()
            return

        async with lock:
            clients.add(websocket)

        await websocket.send_text(json.dumps({
            "type": "system",
            "msg": "OK_LOGIN"
        }))

        await broadcast({
            "type": "system",
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        })

        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            await broadcast({
                "type": "chat",
                "user": data["user"],
                "msg": data["msg"]
            })

    except WebSocketDisconnect:
        pass

    finally:
        async with lock:
            clients.discard(websocket)

        if user:
            await broadcast({
                "type": "system",
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            })
