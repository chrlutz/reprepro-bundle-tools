#!/usr/bin/python3
##########################################################################
# Copyright (c) 2018 Landeshauptstadt München
#           (c) 2018 Christoph Lutz (InterFace AG)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the European Union Public Licence (EUPL),
# version 1.1 (or any later version).
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# European Union Public Licence for more details.
#
# You should have received a copy of the European Union Public Licence
# along with this program. If not, see
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-11-12
##########################################################################
'''
   This is the common_app_server that contains shared code for concrete
   app_servers like bundle_compose.app_server.

   It uses xdg-open to start the web-frontend of the bundle-tool and
   runs the corresponding backend service.
'''

import time
import aiohttp
import logging
from logging import handlers
import argparse
import sys
import os
import io
import queue
import subprocess
import uuid
import json
import datetime
import binascii
import Crypto
from Crypto.Cipher import AES
from aiohttp import web
from aiohttp.web import run_app
import asyncio
from reprepro_bundle_appserver import common_interfaces, IllegalArgumentException
from reprepro_bundle_compose import PROJECT_DIR

PROGNAME = "common_app_server"
logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4253
RE_REGISTER_DELAY_SECONDS = 2

events = set()
__sessions = dict() # of session-id to dict (with session data)
SESSION_TIMEOUT_S = 60*60*24 # increased session timeout to 1d
registeredClients = set()
__storedPwds = dict() # storageId -> encryptedPwd


def setupLogging(loglevel):
    '''
       Initializing logging and set log-level
    '''
    kwargs = {
        'format': '%(levelname)s[%(name)s]: %(message)s',
        'level': loglevel,
        'stream': sys.stderr
    }
    logging.basicConfig(**kwargs)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("aiohttp").setLevel(logging.ERROR if loglevel != logging.DEBUG else logging.INFO)
    logging.getLogger("apt_repos").setLevel(logging.ERROR if loglevel != logging.DEBUG else logging.INFO)


def mainLoop(progname=PROGNAME, description=__doc__, registerRoutes=None, serveDistPath=None, host=DEFAULT_HOST, port=DEFAULT_PORT):
    parser = argparse.ArgumentParser(description=description, prog=progname)
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Show debug messages.")
    parser.add_argument("--no-open-url", action="store_true", help="""
            Don't try to open the backend url in a browser.""")
    parser.add_argument("--no-static-files", action="store_true", help="""
            Don't serve static files in the backend.""")
    parser.add_argument("--host", default=host, help="""
            Hostname for the backend to listen on. Default is '{}'.""".format(host))
    parser.add_argument("--port", default=port, help="""
            Port for the backend to listen on. Default is '{}'.""".format(port))
    args = parser.parse_args()

    setupLogging(logging.DEBUG if args.debug else logging.INFO)

    loop = asyncio.get_event_loop()
    (backendStarted, runner, url) = loop.run_until_complete(run_webserver(args, registerRoutes, serveDistPath))
    if not args.no_open_url:
        loop.run_until_complete(start_browser(url))
    if backendStarted:
        loop.run_forever()
        loop.run_until_complete(runner.cleanup())


def create_session(expireSessionCallback=None):
    '''
        This method creates and returns a new session object as a (generic) dict
        for holding session data. The session object already contains the following
        attributes:
        - 'id': containing the uniq session Id
        - 'touchedTime': initially holding a datetime object with the creation time
        - 'expireSessionCallback': if provided at creation time, this callback will
            be called for at destruction time with the session object as first
            argument. It could contain app specific code for cleaning up the session.
    '''
    global __sessions
    session = dict()
    sid = None
    while not sid or sid in __sessions:
        sid = str(uuid.uuid4())
    session['id'] = sid
    session['touchedTime'] = datetime.datetime.now()
    if expireSessionCallback:
        session['expireSessionCallback'] = expireSessionCallback
    __sessions[sid] = session
    return session


def get_session(sid):
    '''
        This method cleans up expired sessions and returns the session for session id `sid`
        or None, if there is no such valid session. It also updates the 'touchedTime' attribute
        of the session to the datetime.datetime.now().
    '''
    global __sessions
    # cleanup expired Sessions
    keys = list(__sessions.keys())
    for sid in keys:
        session = __sessions.get(sid)
        if session and (datetime.datetime.now() - session['touchedTime']).seconds > SESSION_TIMEOUT_S:
            expire_session(session)
    session = __sessions.get(sid)
    if session:
        session['touchedTime'] = datetime.datetime.now()
    return session


def expire_session(session):
    sid = session['id']
    expireSessionCallback = session.get('expireSessionCallback')
    if expireSessionCallback:
        expireSessionCallback(session)
    del __sessions[sid]


def __expire_all_session():
    keys = list(__sessions.keys())
    for sid in keys:
        session = __sessions.get(sid)
        if session:
            expire_session(session)


async def handle_store_credentials(request):
    global __storedPwds
    res = list()
    try:
        refs = common_interfaces.AuthRefList_validate(json.loads(request.rel_url.query['refs']))
        pwds = json.loads(request.rel_url.query['pwds'])
        for x, authRef in enumerate(refs):
            slotId = str(uuid.uuid4())
            authRef['storageSlotId'] = slotId
            __storedPwds[slotId] = pwds[x]
            res.append(authRef)
            logger.info("stored encrypted password for authId '{}'".format(authRef.get('authId')))
        return web.json_response(res)
    except Exception as e:
        return web.Response(text="IllegalArgumentsProvided:{}".format(e), status=400)


async def handle_register(request):
    global registeredClients
    uuid = request.rel_url.query['uuid']
    registeredClients.add(uuid)
    logger.info("registered frontend with uuid '{}'".format(uuid))
    return web.json_response("registered")


async def handle_unregister(request):
    global registeredClients
    uuid = request.rel_url.query['uuid']
    if uuid in registeredClients:
        registeredClients.remove(uuid)
        logger.info("unregistered frontend with uuid '{}'".format(uuid))
        loop = asyncio.get_event_loop()
        loop.call_later(RE_REGISTER_DELAY_SECONDS, stop_backend_if_unused)
        return web.json_response("unregistered")
    else:
        logger.debug("ignoring unregister unknown frontend with uuid '{}'".format(uuid))
        return web.json_response("error", status=400)


def stop_backend_if_unused():
    logger.debug("triggered: stop_backend_if_unused")
    global registeredClients
    if len(registeredClients) == 0:
        logger.info("stopping backend as there are no more frontends registered")
        __expire_all_session()
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(loop.stop)
    else:
        logger.debug("keep running as there are still frontends registered")


async def start_browser(url):
    logger.info("trying to open browser with url '{}'".format(url))
    subprocess.call(["xdg-open", url])


async def run_webserver(args, registerAdditionalRoutes=None, serveDistPath=None):
    app = web.Application()

    app.router.add_routes([
        # api routes
        web.get('/api/unregister', handle_unregister),
        web.get('/api/register', handle_register),
        web.get('/api/storeCredentials', handle_store_credentials)
    ])
    if registerAdditionalRoutes:
        registerAdditionalRoutes(args, app)
    if serveDistPath and not args.no_static_files:
        app.router.add_static('/', serveDistPath)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, args.host, args.port)
    url = "http://{}:{}/".format(args.host, args.port)
    started = False
    try:
        await site.start()
        started = True
        logger.info("starting backend at url '{}'".format(url))
    except OSError as e:
        logger.info("could not start backend: {}".format(e))
    return (started, runner, url)


def is_valid_authRef(authRef):
    global __storedPwds
    return authRef['storageSlotId'] in __storedPwds


def invalidate_credentials(storageSlotId):
    global __storedPwds
    __storedPwds.pop(storageSlotId, None)


def get_credentials(request, authId):
    global __storedPwds
    authRefs = common_interfaces.AuthRefList_validate(json.loads(request.rel_url.query['refs']))
    ref = None
    for _, r in enumerate(authRefs):
        if r['authId'] == authId:
            ref = r
            break
    if not ref:
        raise IllegalArgumentException("No AuthRef for authId='{}' found.".format(authId))
    slotId = ref['storageSlotId']
    aesCipherParamsStr = __storedPwds[slotId]
    username = ref['user']
    try:
        pwd = decrypt(aesCipherParamsStr, ref['key'])
    except Exception as e:
        logger.error("Could not decrypt Credentials for user {}: {}".format(username, e))
        logger.exception(e)
        return(username, None, slotId)
    #logger.info("Got credentials user, pwd: '{}', '{}'".format(username, pwd))
    return (username, pwd, slotId)


def decrypt(aesCipherParamsStr, key):
    aesCipherParams = json.loads(aesCipherParamsStr)
    #logger.info(f"Params: '{aesCipherParams}'', Key: '{key}'")
    cipher = binascii.a2b_hex(aesCipherParams["cipher"])
    iv =     binascii.a2b_hex(aesCipherParams["iv"])
    key =    binascii.a2b_hex(key)
    aes = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CFB, iv, segment_size=128)
    res = aes.decrypt(cipher)
    return res.decode("utf-8")


class WebappLoggingHandler(logging.handlers.QueueHandler):
    def toBackendLogEntryList(self):
        res = list()
        while not self.queue.empty():
          res.append(common_interfaces.BackendLogEntry(self.queue.get()))
        return res


import contextlib
@contextlib.contextmanager
def logging_redirect_for_webapp():
    que = queue.Queue(-1)
    hndlr = WebappLoggingHandler(que)
    logger.addHandler(hndlr)
    logging.getLogger('reprepro_bundle').addHandler(hndlr)
    logging.getLogger('reprepro_bundle_compose').addHandler(hndlr)
    logging.getLogger('reprepro_bundle_appserver').addHandler(hndlr)
    logging.getLogger('apt_repos').addHandler(hndlr)
    yield hndlr
    logging.getLogger('apt_repos').removeHandler(hndlr)
    logging.getLogger('reprepro_bundle_appserver').removeHandler(hndlr)
    logging.getLogger('reprepro_bundle_compose').removeHandler(hndlr)
    logging.getLogger('reprepro_bundle').removeHandler(hndlr)
    logger.removeHandler(hndlr)
