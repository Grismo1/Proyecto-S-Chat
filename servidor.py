import json
import sqlite3
import bcrypt

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# ---------------------------
# CONEXIONES ACTIVAS
# ---------------------------

clients = set()

# ---------------------------
# BASE DE DATOS
# ---------------------------

def init_db():
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


def user_exists(username):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT username FROM users WHERE username=?",
        (username,)
    )

    row = cur.fetchone()

    conn.close()

    return row is not None


def create_user(username, password):
    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users(username,password) VALUES(?,?)",
        (username, hashed)
    )

    conn.commit()
    conn.close()


def check_login(username, password):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return False

    return bcrypt.checkpw(
        password.encode(),
        row[0].encode()
    )


# ---------------------------
# BROADCAST
# ---------------------------

async def broadcast(message):
    dead = []

    for client in clients:
        try:
            await client.send_text(json.dumps(message))
        except Exception:
            dead.append(client)

    for client in dead:
        clients.discard(client)


# ---------------------------
# WEBSOCKET
# ---------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    user = None

    try:

        # LOGIN O REGISTER
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

        await ws.send_text("OK_LOGIN")

        clients.add(ws)

        await broadcast({
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        })

        # CHAT
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

        clients.discard(ws)

        if user:
            await broadcast({
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            })
