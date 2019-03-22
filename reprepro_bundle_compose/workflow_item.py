#!/usr/bin/python3 -Es
# -*- coding: utf-8 -*-
##########################################################################
# Copyright (c) 2019 Landeshauptstadt München
#           (c) 2019 Christoph Lutz (InterFace AG)
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

class WorkflowItem:

    def __init__(self, ord, name, comment,
                 stage=None, candidates=None, repoSuiteTag=None,
                 tracStatus=None, tracResolution=None, tracOverride=True):
        self.ord = ord
        self.name = name
        self.stage = stage
        self.candidates = candidates
        self.repoSuiteTag = repoSuiteTag
        self.tracStatus = tracStatus
        self.tracResolution = tracResolution
        self.tracOverrice = tracOverride
        self.comment = comment

    @staticmethod
    def parseFromConfFile(confFile):
        workflow = WorkflowItem.__getDefaultWorkflowItems()

        pass

    @staticmethod
    def __getDefaultWorkflowItems():
        res = dict()
        
        key = 'UNKONWN'
        res[key] = WorkflowItem(0, key, comment='''
            The status is unkonwn.
        ''')
        
        key = 'STAGING'
        res[key] = WorkflowItem(100, key, repoSuiteTag='staging', comment='''
            The bundle is still in development but already transferred to the backbone for developer tests ('staging').
            In this stage there is no ticket assigned to the bundle.
        ''')

        key = 'NEW'
        res[key] = WorkflowItem(100, key, repoSuiteTag='sealed', stage='dev',
            tracStatus='new', comment='''
            The bundle is available (transferred to the backbone by the development) and 'sealed' which means
            it is ready for internal tests.
        ''')

        key = 'PRODUCTION'
        res[key] = WorkflowItem(800, key, stage='prod',
            tracStatus='closed', tracResolution='fixed', tracOverride=False, comment='''
            The bundle succesfully finished the customer tests and is now available for production.
        ''')

        key = 'DROPPED'
        res[key] = WorkflowItem(1000, key, stage='drop',
            tracStatus='closed', tracResolution='invalid', tracOverride=False, comment='''
            A test for the bundle failed and the bundle has to be dropped.
            A new bundle has to be created instead of fixing the old one.
        ''')

        return res