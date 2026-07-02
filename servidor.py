import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# ---------------------------
# CONEXIONES ACTIVAS
# ---------------------------
clients = set()

# ---------------------------
# BROADCAST
# ---------------------------
async def broadcast(message: dict):
    dead_clients = []

    for client in clients:
        try:
            await client.send_text(json.dumps(message))
        except Exception:
            dead_clients.append(client)

    for client in dead_clients:
        clients.remove(client)


# ---------------------------
# WEBSOCKET
# ---------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)

    user = "unknown"

    try:
        # LOGIN INICIAL
        login_data = await ws.receive_text()

        try:
            data = json.loads(login_data)
            user = data.get("user", "unknown")
        except Exception:
            pass

        await broadcast({
            "user": "SYSTEM",
            "msg": f"{user} se conectó"
        })

        # LOOP PRINCIPAL
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
        clients.remove(ws)
        await broadcast({
            "user": "SYSTEM",
            "msg": f"{user} se desconectó"
        })
