import asyncio
import websockets
import json
import hashlib

from colorama import init

init()

URI = "wss://proyecto-s-chat.onrender.com/ws"

# ---------------- COLORS ----------------

COLORS = [
    "\033[91m",
    "\033[92m",
    "\033[93m",
    "\033[94m",
    "\033[95m",
    "\033[96m",
    "\033[97m",
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

                user = data.get("user", "SYSTEM")
                text = data.get("msg", "")

                if user.upper() == "SYSTEM":
                    print(f"\n⚙ {text}")
                else:
                    color = get_color(user)
                    print(f"\n{color}{user}{RESET}: {text}")

            except Exception:
                print("\nSERVER:", msg)

    except Exception as e:
        print("❌ RECEIVE ERROR:", e)


# ---------------- SENDER ----------------

async def sender(ws):
    loop = asyncio.get_running_loop()

    while True:
        msg = await loop.run_in_executor(None, input)

        if not msg.strip():
            continue

        await ws.send(json.dumps({
            "msg": msg
        }))


# ---------------- MAIN ----------------

async def main():
    try:
        print("🔗 Conectando...")

        async with websockets.connect(URI) as ws:

            print("\n1 - Login")
            print("2 - Registrarse\n")

            option = input("> ").strip()

            user = input("Usuario: ").strip()
            password = input("Contraseña: ").strip()

            # ---------------- REGISTER ----------------

            if option == "2":

                await ws.send(json.dumps({
                    "action": "register",
                    "user": user,
                    "password": password
                }))

                raw = await ws.recv()
                print("SERVER:", raw)

                try:
                    resp = json.loads(raw)
                except:
                    print("Respuesta inválida del servidor.")
                    input("ENTER para salir...")
                    return

                if resp.get("type") != "ok_register":
                    print(resp.get("msg", "Registro rechazado"))
                    input("ENTER para salir...")
                    return

                print("✔ Usuario creado correctamente.")
                input("ENTER para salir...")
                return

            # ---------------- LOGIN ----------------

            await ws.send(json.dumps({
                "action": "login",
                "user": user,
                "password": password
            }))

            raw = await ws.recv()

            print("SERVER:", raw)

            try:
                resp = json.loads(raw)
            except:
                print("Respuesta inválida del servidor.")
                input("ENTER para salir...")
                return

            if resp.get("type") != "ok_login":
                print(resp.get("msg", "Login incorrecto"))
                input("ENTER para salir...")
                return

            print("\n✅ Login correcto.")
            print("💬 Chat listo.\n")

            await asyncio.gather(
                receiver(ws),
                sender(ws)
            )

    except Exception as e:
        print("❌ CONNECTION ERROR:", e)
        input("ENTER para salir...")


if __name__ == "__main__":
    asyncio.run(main())
