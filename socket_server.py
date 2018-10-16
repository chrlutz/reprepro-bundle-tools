#!/usr/bin/python3

import asyncio
import websockets
import logging
logger = logging.getLogger('websockets')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
count = 0

async def echo(websocket, path):
    async for message in websocket:
        global count
        count+=1
        msg = f"{message} {count}"
        await websocket.send(msg)
        print(msg)

asyncio.get_event_loop().run_until_complete(
    websockets.serve(echo, '127.0.0.1', 8765))
asyncio.get_event_loop().run_forever()

