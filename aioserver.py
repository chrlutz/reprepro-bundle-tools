#!/usr/bin/python3

import time
import aiohttp
from aiohttp import web
import asyncio

async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                for i in range(1,100):
                    await ws.send_str(f"this is log {i}")
                    await asyncio.sleep(1)
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
                web.get('/{name}', handle)])
    web.run_app(app)

run_webserver()
