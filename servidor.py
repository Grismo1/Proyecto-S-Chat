import asyncio
import websockets
import json

async def chat():
    uri = "wss://TU-RENDER.onrender.com"

    async with websockets.connect(uri) as ws:

        user = input("Usuario: ")
        password = input("Contraseña: ")

        await ws.send(json.dumps({
            "user": user,
            "password": password
        }))

        resp = await ws.recv()

        if resp == "ERROR_LOGIN":
            print("Login incorrecto")
            return

        print("Conectado al chat")

        async def recibir():
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                print(f"{data['user']}: {data['msg']}")

        async def enviar():
            while True:
                msg = input()
                await ws.send(msg)

        await asyncio.gather(recibir(), enviar())

asyncio.run(chat())
