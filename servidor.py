import json
import sqlite3
import bcrypt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

clients = set()

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


def user_exists(user):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM users WHERE username=?", (user,))
    r = cur.fetchone()

    conn.close()
    return r is not None


def create_user(user, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users VALUES (?,?)",
        (user, hashed)
    )

    conn.commit()
    conn.close()


def check_login(user, password):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute("SELECT password FROM users WHERE username=?", (user,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return False

    return bcrypt.checkpw(password.encode(), row[0].encode())


# ---------------- BROADCAST ----------------

async def broadcast(msg):
    dead = []

    for c in clients:
        try:
            await c.send_text(json.dumps(msg))
        except:
            dead.append(c)

    for d in dead:
        clients.discard(d)


# ---------------- SOCKET ----------------

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

        # ---------------- REGISTER ----------------
        if action == "register":

            if user_exists(user):
                await ws.send_text("❌ Ese usuario ya existe")
                return

            create_user(user, password)

            await ws.send_text("✅ Usuario registrado correctamente. Ahora podés iniciar sesión.")
            return

        # ---------------- LOGIN ----------------
        if not check_login(user, password):
            await ws.send_text("❌ Usuario o contraseña incorrectos")
            return

        await ws.send_text("✅ Login exitoso")

        clients.add(ws)

        await broadcast({
            "user": "SYSTEM",
            "msg": f"👋 {user} se unió al chat"
        })

        # ---------------- CHAT LOOP ----------------
        while True:
            raw = await ws.receive_text()

            try:
                data = json.loads(raw)
                text = data.get("msg", "")
            except:
                text = raw

            await broadcast({
                "user": user,
                "msg": text
            })

    except WebSocketDisconnect:
        pass

    finally:
        clients.discard(ws)

        if user:
            await broadcast({
                "user": "SYSTEM",
                "msg": f"👋 {user} salió del chat"
            })
