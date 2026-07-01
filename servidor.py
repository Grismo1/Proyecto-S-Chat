import asyncio
import websockets

clientes = set()

async def manejar_cliente(websocket):

    clientes.add(websocket)

    print("Usuario conectado")

    try:
        async for mensaje in websocket:

            print("Mensaje:", mensaje)

            desconectados = []

            for cliente in clientes:
                try:
                    if cliente != websocket:
                        await cliente.send(mensaje)
                except:
                    desconectados.append(cliente)

            for c in desconectados:
                clientes.discard(c)

    except:
        pass

    finally:
        clientes.discard(websocket)
        print("Usuario desconectado")


async def main():

    puerto = 10000

    print(f"Servidor iniciado en puerto {puerto}")

    async with websockets.serve(
        manejar_cliente,
        "0.0.0.0",
        puerto
    ):
        await asyncio.Future()


asyncio.run(main())
