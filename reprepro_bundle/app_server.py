#!/usr/bin/python3
'''
   This is the starter for the bundle-tool frontend.

   It uses xdg-open to start the web-frontend of the bundle-tool and
   runs the corresponding backend service.
'''

import logging
import os
from reprepro_bundle_appserver import common_app_server, common_interfaces
from aiohttp import web
from reprepro_bundle.BundleCLI import scanBundles

progname = "bundle-app"
logger = logging.getLogger("reprepro_bundle_appserver.bundle_app")

APP_DIST = './ng-bundle/'
if not os.path.exists(APP_DIST):
    APP_DIST = "/usr/lib/reprepro-bundle-apps/ng-bundle/"


async def handle_get_bundleList(request):
    res = list()
    for bundle in sorted(scanBundles()):
        res.append(common_interfaces.Bundle(bundle))
    return web.json_response(res)


async def handle_get_metadata(request):
    for bundle in sorted(scanBundles()):
        if bundle.bundleName == request.rel_url.query['bundlename']:
            return web.json_response(common_interfaces.BundleMetadata(bundle))
    return web.Response(text="error")


async def handle_router_link(request):
    '''
        pass router-links to angular' main entry page so that
        they are handled by angulars router module
    '''
    return web.FileResponse(os.path.join(APP_DIST, 'index.html'))


def registerRoutes(args, app):
    app.router.add_routes([
        # api routes
        web.get('/api/bundleList', handle_get_bundleList),
        web.get('/api/bundleMetadata', handle_get_metadata),
    ])
    if not args.no_static_files:
        app.router.add_routes([
            # angular router-links
            web.get('/', handle_router_link),
            web.get('/bundle-list', handle_router_link),
            web.get('/bundle-list/{tail:.*}', handle_router_link),
            web.get('/bundle/{tail:.*}', handle_router_link),
        ])


if __name__ == "__main__":
    common_app_server.mainLoop(**{
        'progname': progname,
        'description': __doc__,
        'registerRoutes': registerRoutes,
        'serveDistPath': APP_DIST,
        'port': 4253
    })
