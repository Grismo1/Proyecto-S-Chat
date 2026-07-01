import asyncio
import websockets
import json
import os

# Usuarios "registrados" (puedes luego mover esto a DB)
USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

# Usuarios conectados: {username: websocket}
CONNECTED = {}

async def handler(ws):

    user = None

    try:
        # 1. LOGIN
        auth_data = await ws.recv()
        auth = json.loads(auth_data)

        username = auth.get("user")
        password = auth.get("password")

        if username not in USERS_DB or USERS_DB[username] != password:
            await ws.send("ERROR_LOGIN")
            return

        # evitar doble login
        if username in CONNECTED:
            await ws.send("ERROR_ALREADY_LOGGED")
            return

        user = username
        CONNECTED[user] = ws

        await ws.send("OK_LOGIN")
        print(f"[+] {user} conectado")

        # 2. LOOP DE MENSAJES
        async for msg in ws:
            # mensaje plano del cliente
            data = {
                "user": user,
                "msg": msg
            }

            # broadcast a todos
            disconnected = []

            for u, conn in CONNECTED.items():
                try:
                    await conn.send(json.dumps(data))
                except:
                    disconnected.append(u)

            # limpiar conexiones muertas
            for u in disconnected:
                CONNECTED.pop(u, None)

    except Exception as e:
        print("Error:", e)

    finally:
        if user and user in CONNECTED:
            CONNECTED.pop(user, None)
            print(f"[-] {user} desconectado")


async def main():
    PORT = int(os.environ.get("PORT", 10000))

    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Servidor WebSocket activo en puerto {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
