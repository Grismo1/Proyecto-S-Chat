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

    # Usuarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    # Historial de mensajes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


def user_exists(username):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM users WHERE username=?",
        (username,)
    )

    exists = cur.fetchone()

    conn.close()

    return exists is not None


def create_user(username, password):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    cur.execute(
        "INSERT INTO users VALUES (?,?)",
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

    if not row:
        return False

    return bcrypt.checkpw(
        password.encode(),
        row[0].encode()
    )


# ---------------- MENSAJES ----------------

def save_message(username, message):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO messages (username, message)
        VALUES (?,?)
        """,
        (username, message)
    )

    conn.commit()
    conn.close()


def get_history(limit=500):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()

    cur.execute(
        """
        SELECT username, message
        FROM messages
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cur.fetchall()

    conn.close()

    # Los invertimos para mostrar del más viejo al más nuevo
    rows.reverse()

    return [
        {
            "user": row[0],
            "msg": row[1]
        }
        for row in rows
    ]


# ---------------- BROADCAST ----------------

async def broadcast(message: dict):
    dead = []

    for c in clients:
        try:
            await c.send_text(json.dumps(message))
        except:
            dead.append(c)

    for c in dead:
        clients.discard(c)


# ---------------- WEBSOCKET ----------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    user = None

    try:

        # Primera comunicación: login/register
        raw = await ws.receive_text()

        data = json.loads(raw)

        action = data.get("action")
        username = data.get("user")
        password = data.get("password")


        # ---------- REGISTER ----------

        if action == "register":

            if user_exists(username):

                await ws.send_text(json.dumps({
                    "type": "error",
                    "msg": "Ese usuario ya existe"
                }))

                return


            create_user(username, password)


            await ws.send_text(json.dumps({
                "type": "ok",
                "msg": "Usuario registrado correctamente. Ahora inicia sesión."
            }))

            return



        # ---------- LOGIN ----------

        if action == "login":

            if not check_login(username, password):

                await ws.send_text(json.dumps({
                    "type": "error",
                    "msg": "Usuario o contraseña incorrectos"
                }))

                return


            user = username

            clients.add(ws)


            # Confirmación login
            await ws.send_text(json.dumps({
                "type": "ok_login",
                "msg": "Login correcto. Bienvenido al chat."
            }))


            # Enviar historial de últimos 500 mensajes
            await ws.send_text(json.dumps({
                "type": "history",
                "messages": get_history(500)
            }))


            # Aviso de conexión
            await broadcast({
                "user": "SYSTEM",
                "msg": f"{user} se conectó"
            })



        # ---------- CHAT LOOP ----------

        while True:

            raw = await ws.receive_text()

            try:

                data = json.loads(raw)
                msg = data.get("msg", "")

            except:

                msg = raw


            if msg.strip() == "":
                continue


            # Guardar mensaje en historial
            save_message(user, msg)


            # Mandar a todos
            await broadcast({
                "user": user,
                "msg": msg
            })


    except WebSocketDisconnect:

        pass


    finally:

        if ws in clients:
            clients.remove(ws)


        if user:

            await broadcast({
                "user": "SYSTEM",
                "msg": f"{user} se desconectó"
            })
