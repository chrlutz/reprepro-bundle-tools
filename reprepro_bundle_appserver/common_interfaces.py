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
    This file contains interface implementations for common/shared interfaces
'''
from urllib.parse import urljoin
import re
bundleRe = re.compile(r"(bundle:)?(\w+)\/(\d+)")

def BundleID_validate(data):
    match = bundleRe.match(data)
    if match:
        return match.group(2), match.group(3)
    raise TypeError("invalid bundleID")

def BundleIDs_validate(data):
    if isinstance(data, list):
        for bid in data:
            BundleID_validate(bid)
        return data
    raise TypeError("invalid bundleIDs")

def Bundle(bundle):
    info = bundle.getInfo() or dict()
    return {
        'name': bundle.bundleName,
        'distribution': bundle.bundleName.split("/", 1)[0],
        'target': info.get("Target", "unknown"),
        'subject': info.get("Releasenotes", "--no-subject--").split("\n", 1)[0],
        'readonly': not bundle.isEditable(),
        'creator': info.get("Creator", "unknown")
    }

def Bundle_validate(data):
    if isinstance(data, dict):
      dist, bnum = BundleID_validate(data['name'])
      return {
          'name': 'bundle:{}/{}'.format(dist, bnum),
          'distribution': data['distribution'],
          'target': data['target'],
          'distribution': data['distribution'],
          'subject': data['subject'],
          'readonly': data['readonly'],
          'creator': data['creator']
      }
    raise TypeError("invalid AuthRequired")

def BundleMetadata(bundle):
    info = bundle.getInfo() or dict()
    rnParts = info.get("Releasenotes", "").split("\n", 2)
    return {
        'bundle': Bundle(bundle),
        'basedOn': info.get("BasedOn"),
        'releasenotes': rnParts[2] if (len(rnParts) == 3) else "",
    }

def BundleMetadata_validate(data):
    if isinstance(data, dict):
      return {
          'bundle': Bundle_validate(data['bundle']),
          'basedOn': data['basedOn'],
          'releasenotes': data['releasenotes']
      }
    raise TypeError("invalid BundleMetadata")

def ManagedBundle(bundle, tracBaseUrl=None):
    ticket = ""
    ticketUrl = ""
    if tracBaseUrl and bundle.getTrac():
        if not tracBaseUrl.endswith("/"):
            tracBaseUrl += "/"
        ticket = bundle.getTrac()
        ticketUrl = urljoin(tracBaseUrl, "ticket/{}".format(ticket))
    (dist, _) = BundleID_validate(bundle.getID())

    return {
        'id': bundle.getID(),
        'distribution': bundle.getAptSuite() or dist,
        'status': WorkflowMetadata(bundle.getStatus()),
        'target': bundle.getTarget(),
        'ticket': ticket,
        'ticketUrl': ticketUrl,
        'ignores': bundle.getIgnores()
    }

def ManagedBundleInfo(bundle, tracBaseUrl=None):
    info = bundle.getInfo() or dict()
    repoInfo = dict()
    if bundle.getRepoSuite():
        repoInfo = {
            'infoFileUrl': bundle.getInfoFileUrl(),
            'sourcesList' : bundle.getRepoSuite().getSourcesList(),
            'repoUrl' : bundle.getRepoSuite().getRepoUrl()
        }
    return {
        'id': bundle.getID(),
        'basedOn': info.get("BasedOn"),
        'subject': info.get("Releasenotes", "--no-subject--").split("\n", 1)[0],
        'creator': info.get("Creator", "unknown"),
        **repoInfo
    }

def Suite(suite):
    return {
        'name': suite.getSuiteName(), #str
        'tags': suite.getTags(), #list
        'architectures': suite.getArchitectures(), #list
        'components': suite.getComponents(), #list
        'aptSuite': suite.getAptSuite(), #str
        'distsUrl': suite.getDistsUrl(), #str
        'repoUrl': suite.getRepoUrl(), #str
        'hasSources': suite.hasSources(), #bool
        'trustedGPG': str(suite.getTrustedGPG()), #str
        'aptConf': suite.getAptConf(), #str
        'sourcesList': suite.getSourcesList() #str
    }

def WorkflowMetadata(status):
    return {
        'ord': status.value.get('ord'),
        'name': status.name,
        'comment': status.value.get('comment'),
        'repoSuiteTag': status.value.get('repoSuiteTag'),
        'tracStatus': status.value.get('tracStatus'),
        'stage': status.value.get('stage'),
        'override': status.value.get('override'),
        'tracResolution': status.value.get('tracResolution'),
        'candidates': status.value.get('candidates')
    }

def BackendLogEntry(record):
    return {
        'logger': record.name,
        'level': record.levelname,
        'message': record.message
    }

def VersionedChange(commit, published):
    return {
        'id': commit.hexsha,
        'author': commit.author.name,
        'message': commit.message,
        'date': commit.authored_date,
        'published': published
    }

def TargetDescription(value, description):
    return {
        'value': value,
        'description': description
    }

def AuthType(authId, requiredFor=None):
    return {
        'authId': authId, # a key identifying the credentials
        'requiredFor': requiredFor # e.g. "Required to Synchronize with GIT"
    }

def AuthRef(authId, user, storageSlotId, key):
    return {
        'authId': authId_validate(authId),
        'user': user,
        'storageSlotId': storageSlotId_validate(storageSlotId),
        'key': key
    }

def authId_validate(authId):
    if re.match(r"[a-zA-Z][0-9a-zA-Z_]{0,50}", authId):
        return authId
    raise TypeError("invalid authId")

def storageSlotId_validate(storageSlotId):
    if storageSlotId == None: # initially allow None value
        return None
    if re.match(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", storageSlotId):
        return storageSlotId
    raise TypeError("invalid storageSlotId")

def AuthRef_validate(data):
    if isinstance(data, dict):
        return AuthRef(data['authId'], data['user'], data['storageSlotId'], data['key'])
    raise TypeError("invalid AuthRef")

def AuthRefList_validate(data):
    if isinstance(data, list):
        res = list()
        for el in data:
            res.append(AuthRef_validate(el))
        return res
    raise TypeError("invalid AuthRefList")

def AuthRequired_validate(data):
    if isinstance(data, dict):
      return {
          'actionId': actionId_validate(data['actionId']),
          'refs': AuthRefList_validate(data['refs'])
      }
    raise TypeError("invalid AuthRequired")

def actionId_validate(actionId):
    if actionId in ["login", "publishChanges", "bundleSync", "gitPullRebase"]:
        return actionId
    raise TypeError("invalid actionId")

def SessionInfo(repoUrl, branch):
    return {
        'repoUrl': repoUrl,
        'branch': branch
    }