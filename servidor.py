import json
import sqlite3

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI()


clients = {}

# username : websocket


# ---------------- DB ----------------


def init_db():

    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()


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



# ---------------- MENSAJES ----------------


def save_message(username, message):

    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()


    cur.execute(
        """
        INSERT INTO messages(username,message)
        VALUES (?,?)
        """,
        (
            username,
            message
        )
    )


    conn.commit()
    conn.close()





def get_history(limit=500):

    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()


    cur.execute(
        """
        SELECT username,message
        FROM messages
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )


    rows = cur.fetchall()


    conn.close()


    rows.reverse()


    return [
        {
            "user": r[0],
            "msg": r[1]
        }
        for r in rows
    ]





# ---------------- BROADCAST ----------------


async def broadcast(message):

    dead = []


    for ws in clients.values():

        try:

            await ws.send_text(
                json.dumps(message)
            )


        except:

            dead.append(ws)



    for ws in dead:

        for user, socket in list(clients.items()):

            if socket == ws:

                del clients[user]





# ---------------- WEBSOCKET ----------------


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()


    user = None


    try:


        # Primera comunicación
        raw = await ws.receive_text()

        data = json.loads(raw)


        action = data.get("action")
        username = data.get("user")



        if action != "join":

            await ws.send_text(
                json.dumps({
                    "type":"error",
                    "msg":"Acción inválida"
                })
            )

            return




        if not username or username.strip() == "":

            await ws.send_text(
                json.dumps({
                    "type":"error",
                    "msg":"Nombre inválido"
                })
            )

            return




        username = username.strip()



        # Usuario ocupado

        if username in clients:


            await ws.send_text(
                json.dumps({
                    "type":"error",
                    "msg":"Ese usuario ya está conectado"
                })
            )


            return





        user = username


        clients[user] = ws




        # Confirmación

        await ws.send_text(
            json.dumps({
                "type":"joined",
                "msg":"Entraste al chat"
            })
        )





        # Historial

        await ws.send_text(
            json.dumps({
                "type":"history",
                "messages":get_history(500)
            })
        )





        # Aviso

        await broadcast({

            "user":"SYSTEM",

            "msg":f"{user} se conectó"

        })





        # CHAT LOOP


        while True:


            raw = await ws.receive_text()



            try:

                data = json.loads(raw)

                msg = data.get("msg","")


            except:

                msg = raw





            if msg.strip() == "":

                continue





            save_message(
                user,
                msg
            )



            await broadcast({

                "user":user,

                "msg":msg

            })





    except WebSocketDisconnect:

        pass



    finally:


        if user in clients:

            del clients[user]



        if user:


            await broadcast({

                "user":"SYSTEM",

                "msg":f"{user} se desconectó"

            })
