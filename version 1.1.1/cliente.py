import asyncio
import websockets
import json
import hashlib

from colorama import init

# 🔥 IMPORTANTE: habilita ANSI en CMD viejo
init()

URI = "wss://proyecto-s-chat.onrender.com/ws"


# ---------------- COLORS ----------------

COLORS = [
    "\033[91m",  # rojo
    "\033[92m",  # verde
    "\033[93m",  # amarillo
    "\033[94m",  # azul
    "\033[95m",  # magenta
    "\033[96m",  # cyan
    "\033[97m",  # blanco
]

RESET = "\033[0m"


def get_color(username: str):
    h = int(hashlib.md5(username.encode()).hexdigest(), 16)
    return COLORS[h % len(COLORS)]


# ---------------- RECEIVER ----------------

async def receiver(ws):
    print("🔵 Receiver activo")

    try:
        async for msg in ws:
            try:
                data = json.loads(msg)

                user = data.get("user")
                text = data.get("msg")

                if user == "SYSTEM":
                    print(f"\n⚙ {text}")
                else:
                    color = get_color(user)
                    print(f"\n{color}{user}{RESET}: {text}")

            except json.JSONDecodeError:
                print("\nSERVER:", msg)

    except Exception as e:
        print("❌ RECEIVE ERROR:", e)


# ---------------- SENDER ----------------

async def sender(ws):
    loop = asyncio.get_event_loop()

    while True:
        msg = await loop.run_in_executor(None, input)

        if not msg.strip():
            continue

        await ws.send(msg)


# ---------------- MAIN ----------------

async def main():
    try:
        print("🔗 Conectando...")

        async with websockets.connect(URI) as ws:

            print("\n1 - Login\n2 - Registrarse\n")
            option = input("> ").strip()

            user = input("Usuario: ")
            password = input("Contraseña: ")

            if option == "2":
                await ws.send(json.dumps({
                    "action": "register",
                    "user": user,
                    "password": password
                }))

                resp = await ws.recv()
                print("REGISTER:", resp)

                if resp != "REGISTER_OK":
                    input("ENTER para salir...")
                    return

                print("✔ Usuario creado. Ahora logueate.")
                return

            # ---------------- LOGIN ----------------
            await ws.send(json.dumps({
                "action": "login",
                "user": user,
                "password": password
            }))

            resp = await ws.recv()
            print("LOGIN:", resp)

            if resp != "OK_LOGIN":
                input("ENTER para salir...")
                return

            print("\n💬 Chat listo...\n")

            await asyncio.gather(
                receiver(ws),
                sender(ws)
            )

    except Exception as e:
        print("❌ CONNECTION ERROR:", e)
        input("ENTER para salir...")


asyncio.run(main())
