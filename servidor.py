import json
import sqlite3

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI()


clients = set()

# websocket -> username
active_users = {}



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

        active_users.pop(client, None)







async def send_online_users():


    await broadcast({

        "type":"users",

        "users":list(active_users.values())

    })









# ================= WEBSOCKET =================



@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    # Confirmar al cliente que el WebSocket ya está listo
    await ws.send_text(
        json.dumps({
            "type": "connected"
        })
    )

    user = None

    try:

        raw = await ws.receive_text()
        
        print("PRIMER MENSAJE")
        print(raw)

       
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






            # comprobar usuario conectado


            if username in active_users.values():



                await ws.send_text(
                    json.dumps({

                        "type":"error",

                        "msg":"Ese usuario ya esta conectado"

                    })
                )


                return






            user = username



            clients.add(ws)


            active_users[ws] = user






            await ws.send_text(
                json.dumps({

                    "type":"joined",

                    "msg":"Entraste al chat"

                })
            )








            # mandar historial


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





            # actualizar lista online


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
            
            print("MENSAJE DEL CHAT")
            print(raw)


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






        if ws in active_users:


            disconnected_user = active_users[ws]


            del active_users[ws]





            await broadcast({

                "user":"SYSTEM",

                "msg":f"{disconnected_user} se desconecto"

            })





            await send_online_users()
