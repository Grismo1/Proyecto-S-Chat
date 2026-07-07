import json
import sqlite3

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI()


clients = set()

active_users = set()



# ================= DB =================


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






# ================= MENSAJES =================


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
            "user": row[0],
            "msg": row[1]
        }

        for row in rows

    ]






# ================= BROADCAST =================



async def broadcast(message):

    dead = []


    for client in clients:

        try:

            await client.send_text(
                json.dumps(message)
            )


        except:

            dead.append(client)




    for client in dead:

        clients.discard(client)








async def send_online_users():

    await broadcast({

        "type": "users",

        "users": list(active_users)

    })







# ================= WEBSOCKET =================



@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):


    await ws.accept()


    user = None



    try:



        raw = await ws.receive_text()


        data = json.loads(raw)


        action = data.get("action")

        username = data.get("user")





        # ================= JOIN =================



        if action == "join":



            if not username:


                await ws.send_text(
                    json.dumps({

                        "type":"error",

                        "msg":"Usuario invalido"

                    })
                )


                return





            if username in active_users:



                await ws.send_text(
                    json.dumps({

                        "type":"error",

                        "msg":"Ese usuario ya esta conectado"

                    })
                )


                return






            user = username



            active_users.add(user)


            clients.add(ws)




            await ws.send_text(
                json.dumps({

                    "type":"joined",

                    "msg":"Entraste al chat"

                })
            )






            await ws.send_text(
                json.dumps({

                    "type":"history",

                    "messages":get_history(500)

                })
            )






            await broadcast({

                "user":"SYSTEM",

                "msg":f"{user} se conecto"

            })





            await send_online_users()







        else:



            await ws.send_text(
                json.dumps({

                    "type":"error",

                    "msg":"Accion desconocida"

                })
            )


            return







        # ================= CHAT =================



        while True:



            raw = await ws.receive_text()




            try:


                data = json.loads(raw)


                msg = data.get(
                    "msg",
                    ""
                )



            except:


                msg = raw





            msg = msg.strip()



            if msg == "":

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



        if ws in clients:

            clients.remove(ws)





        if user:


            active_users.discard(user)



            await broadcast({

                "user":"SYSTEM",

                "msg":f"{user} se desconecto"

            })



            await send_online_users()
