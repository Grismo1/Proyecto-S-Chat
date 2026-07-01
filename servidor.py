from fastapi import FastAPI, WebSocket
import json

app = FastAPI()

USERS_DB = {
    "admin": "1234",
    "user1": "pass1"
}

CONNECTED = {}

@app.get("/")
def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    user = None

    try:
        auth = json.loads(await websocket.receive_text())

        username = auth["user"]
        password = auth["password"]

        if USERS_DB.get(username) != password:
            await websocket.send_text("ERROR_LOGIN")
            return

        CONNECTED[username] = websocket
        await websocket.send_text("OK_LOGIN")

        while True:
            msg = await websocket.receive_text()

            data = json.dumps({
                "user": username,
                "msg": msg
            })

            for conn in list(CONNECTED.values()):
                try:
                    await conn.send_text(data)
                except:
                    pass

    except:
        pass
