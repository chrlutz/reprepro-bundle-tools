#!/usr/bin/python3

import time
import aiohttp
from aiohttp import web
import asyncio

events = set()


def logMessage(msg):
    for event in events:
        event.data = msg
        event.set()

async def handle_doit(request):
    for i in range(1,10):
        logMessage(f"this is log {i}")
        await asyncio.sleep(1)
    logMessage("quit")
    return web.Response(text="ok")

async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)

async def websocket_handler(request):
    global events
    ws = web.WebSocketResponse()
    print(f"request {request}")
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                event = asyncio.Event()
                events.add(event) 
                while True:
                    await event.wait()
                    if event.data == "quit":
                        event.clear()
                        break
                    await ws.send_str(event.data)
                    event.clear()
                print("event done")
                events.remove(event)
                await ws.close()
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())
    print('websocket connection closed')
    return ws

def run_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle),
                web.get('/log', websocket_handler),
                web.get('/doit', handle_doit),
                web.get('/{name}', handle)])
    web.run_app(app)

run_webserver()
