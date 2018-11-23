#!/usr/bin/python3
'''
   This is the starter for the bundle-compose-tool frontend.

   It uses xdg-open to start the web-frontend of the bundle-compose-tool and
   runs the corresponding backend service.
'''

import logging
import json
import os
import io
from aiohttp import web
import git
import reprepro_bundle_compose
from reprepro_bundle_compose import PROJECT_DIR, BUNDLES_LIST_FILE, BundleStatus, getTargetRepoSuites, getBundleRepoSuites, parseBundles, updateBundles, trac_api, getTracConfig, markBundlesForStatus, git_commit, ensure_clean_git_repo, GitNotCleanException
from reprepro_bundle_appserver import common_app_server, common_interfaces


progname = "bundle-compose-app"
logger = logging.getLogger("reprepro_bundle_appserver.bundle_compose_app")

APP_DIST = './ng-bundle-compose/'


async def handle_latest_published_change(request):
    repo = git.Repo(PROJECT_DIR)
    tracking = repo.head.ref.tracking_branch()
    if tracking:
      res = common_interfaces.VersionedChange(tracking.commit, True)
      return web.json_response(res)
    return web.json_response(None)


async def handle_list_changes(request):
    res = []
    repo = git.Repo(PROJECT_DIR)
    published = getPublishedCommits(repo)
    c = repo.head.commit
    while c:
        res.append(common_interfaces.VersionedChange(c, c.hexsha in published))
        c = c.parents[0] if len(c.parents) > 0 else None
    return web.json_response(res)


def getPublishedCommits(repo):
    commits = set()
    remote = repo.head.ref.tracking_branch()
    c = remote.commit if remote else None
    while c:
      commits.add(c.hexsha)
      c = c.parents[0] if len(c.parents) > 0 else None
    return commits


async def handle_undo_last_change(request):
    logger.info("handling 'Undo last Change'")
    res = []
    with common_app_server.logging_redirect_for_webapp() as logs:
        try:
            repo = git.Repo(PROJECT_DIR)
            ensure_clean_git_repo(repo)
            repo.git.reset('--hard', "HEAD^1")
            logger.info("Undoing last Change was successfull")
        except git.exc.GitCommandError as e:
            logger.error("Undoing last Change failed:\n{}".format(e))
        except GitNotCleanException as e:
            logger.error(e)
        finally:
            res = logs.toBackendLogEntryList()
    return web.json_response(res)


async def handle_publish_changes(request):
    logger.info("handling 'Publish Changes'")
    res = ["default"]
    with common_app_server.logging_redirect_for_webapp() as logs:
        try:
            repo = git.Repo(PROJECT_DIR)
            repo.git.push()
            logger.info("Successfully Pusblished changes")
        except git.exc.GitCommandError as e:
            logger.error("Publishing Changes failed:\n{}".format(e))
        res = logs.toBackendLogEntryList()
    return web.json_response(res)


async def handle_mark_for_status(request):
    status = BundleStatus.getByName(request.rel_url.query['status'])
    ids = json.loads(request.rel_url.query['bundles'])
    logger.info("mark for status: {} --> {}".format(ids, status))
    res = []
    with common_app_server.logging_redirect_for_webapp() as logs:
        try:
            repo = git.Repo(PROJECT_DIR)
            ensure_clean_git_repo(repo)
            bundles = parseBundles(getBundleRepoSuites())
            markBundlesForStatus(bundles, set(ids), status, True)
            msg = "MARKED for status '{}'\n\n - {}".format(status, "\n - ".join(sorted(ids)))
            if len(ids) == 1:
              msg = "MARKED {} for status '{}'".format("".join(ids), status)
            git_commit(repo, [BUNDLES_LIST_FILE], msg)
        except GitNotCleanException as e:
            logger.error(e)
        finally:
            res = logs.toBackendLogEntryList()
    return web.json_response(res)


async def handle_update_bundles(request):
    logger.info("handling 'Update Bundles'")
    res = []
    with common_app_server.logging_redirect_for_webapp() as logs:
        try:
            repo = git.Repo(PROJECT_DIR)
            ensure_clean_git_repo(repo)
            updateBundles()
            git_commit(repo, [BUNDLES_LIST_FILE], "UPDATED {}".format(BUNDLES_LIST_FILE))
        except GitNotCleanException as e:
            logger.error(e)
        finally:
            res = logs.toBackendLogEntryList()
    return web.json_response(res)


async def handle_get_managed_bundles(request):
    # faster (doesn't need to resolve info file)
    res = list()
    bundles = parseBundles(getBundleRepoSuites())
    for (unused_id, bundle) in sorted(bundles.items()):
        res.append(common_interfaces.ManagedBundle(bundle, **{'tracBaseUrl': getTracConfig().get('TracUrl')}))
    return web.json_response(res)


async def handle_get_managed_bundle_infos(request):
    # slower (as it needs to resolve info files)
    res = list()
    bundles = parseBundles(getBundleRepoSuites())
    for (unused_id, bundle) in sorted(bundles.items()):
        res.append(common_interfaces.ManagedBundleInfo(bundle, **{'tracBaseUrl': getTracConfig().get('TracUrl')}))
    return web.json_response(res)


async def handle_get_configured_stages(request):
    res = list()
    for stage in sorted(BundleStatus.getAvailableStages()):
        targets = getTargetRepoSuites(stage)
        if len(targets) > 0:
            res.append(stage)
    return web.json_response(res)


async def handle_get_workflow_metadata(request):
    res = list()
    for status in sorted(BundleStatus):
        res.append(common_interfaces.WorkflowMetadata(status))
    return web.json_response(res)


async def handle_router_link(request):
    '''
        pass router-links to angular' main entry page so that
        they are handled by angulars router module
    '''
    return web.FileResponse(os.path.join(APP_DIST, 'index.html'))


def registerRoutes(args, app):
    app.add_routes([
        # api routes
        web.get('/api/workflowMetadata', handle_get_workflow_metadata),
        web.get('/api/configuredStages', handle_get_configured_stages),
        web.get('/api/managedBundles', handle_get_managed_bundles),
        web.get('/api/managedBundleInfos', handle_get_managed_bundle_infos),
        web.get('/api/updateBundles', handle_update_bundles),
        web.get('/api/markForStatus', handle_mark_for_status),
        web.get('/api/listChanges', handle_list_changes),
        web.get('/api/latestPublishedChange', handle_latest_published_change),
        web.get('/api/undoLastChange', handle_undo_last_change),
        web.get('/api/publishChanges', handle_publish_changes),
    ])
    if not args.no_static_files:
        app.add_routes([
            # angular router-links
            web.get('/', handle_router_link),
            web.get('/workflow-status-editor', handle_router_link),
            web.get('/workflow-status-editor/{tail:.*}', handle_router_link),
            #web.get('/bundle/{tail:.*}', handle_router_link),
        ])


if __name__ == "__main__":
    common_app_server.mainLoop(**{
        'progname': progname,
        'description': __doc__,
        'registerRoutes': registerRoutes,
        'serveDistPath': APP_DIST,
        'port': 4255
    })
