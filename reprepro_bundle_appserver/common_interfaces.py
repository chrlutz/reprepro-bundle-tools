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


def Bundle(bundle):
    info = bundle.getInfo() or dict()
    return {
        'name': bundle.bundleName,
        'distribution': bundle.bundleName.split("/", 1)[0],
        'target': info.get("Target", "no-target"),
        'subject': info.get("Releasenotes", "--no-subject--").split("\n", 1)[0],
        'readonly': not bundle.isEditable(),
        'creator': info.get("Creator", "unknown")
    }

def BundleMetadata(bundle):
    info = bundle.getInfo() or dict()
    rnParts = info.get("Releasenotes", "").split("\n", 2)
    return {
        'bundle': Bundle(bundle),
        'basedOn': info.get("BasedOn"),
        'releasenotes': rnParts[2] if (len(rnParts) == 3) else "",
    }

def ManagedBundle(bundle, **kwargs):
    tracBaseUrl = kwargs.get('tracBaseUrl')

    ticket = ""
    ticketUrl = ""
    if tracBaseUrl and bundle.getTrac():
        if not tracBaseUrl.endswith("/"):
            tracBaseUrl += "/"
        ticket = bundle.getTrac()
        ticketUrl = urljoin(tracBaseUrl, "ticket/{}".format(ticket))

    return {
        'id': bundle.getID(),
        'distribution': bundle.getAptSuite() or "unknown",
        'status': WorkflowMetadata(bundle.getStatus()),
        'target': bundle.getTarget(),
        'ticket': ticket,
        'ticketUrl': ticketUrl
    }

def ManagedBundleInfo(bundle, **kwargs):
    info = bundle.getInfo() or dict()
    return {
        'managedBundle': ManagedBundle(bundle, **kwargs),
        'basedOn': info.get("BasedOn"),
        'subject': info.get("Releasenotes", "--no-subject--").split("\n", 1)[0],
        'creator': info.get("Creator", "unknown"),
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
