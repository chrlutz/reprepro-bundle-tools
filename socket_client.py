#!/usr/bin/python3

import time
import asyncio
import websockets

async def hello(uri):
    async with websockets.connect(uri) as websocket:
        await websocket.send("getlog")
        while True:
            try:
                answer = await websocket.recv()
                print(answer)
            except websockets.exceptions.ConnectionClosed as e:
                print(f"closed: {e}")
                break

asyncio.get_event_loop().run_until_complete(
    hello('ws://localhost:8080/log'))

