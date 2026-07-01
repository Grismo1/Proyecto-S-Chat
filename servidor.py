import asyncio
import websockets
import json
import os
from aiohttp import web

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

CONNECTED = {}

async def handler(ws):
    user = None
    try:
        auth_data = await ws.recv()
        auth = json.loads(auth_data)

        username = auth.get("user")
        password = auth.get("password")

        if username not in USERS_DB or USERS_DB[username] != password:
            await ws.send("ERROR_LOGIN")
            return

        if username in CONNECTED:
            await ws.send("ERROR_ALREADY_LOGGED")
            return

        user = username
        CONNECTED[user] = ws

        await ws.send("OK_LOGIN")

        async for msg in ws:
            data = json.dumps({"user": user, "msg": msg})

            for conn in list(CONNECTED.values()):
                try:
                    await conn.send(data)
                except:
                    pass

    finally:
        if user:
            CONNECTED.pop(user, None)

async def ws_server():
    port = int(os.environ.get("PORT", 10000))
    return websockets.serve(handler, "0.0.0.0", port)

async def http_handler(request):
    return web.Response(text="OK")

async def main():
    port = int(os.environ.get("PORT", 10000))

    # HTTP (Render health check)
    app = web.Application()
    app.router.add_get("/", http_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # WebSocket en paralelo NO funciona así con mismo puerto en websockets puro
    # 👉 por eso esto ya te dice algo importante:
    print("Render necesita FastAPI o aiohttp completo")

    await asyncio.Future()

asyncio.run(main())
