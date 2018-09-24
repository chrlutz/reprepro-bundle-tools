#!/usr/bin/python3 -Es
# -*- coding: utf-8 -*-
import os
import logging
import re
import apt_pkg
import getpass
import apt_repos

from reprepro_bundle import PROJECT_DIR, BundleError
from DeploymentStatus import DeploymentStatus
from PackageStatus import PackageStatus
from Package import Package
from apt_repos import PackageField
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class Bundle():
    '''
        This class represents and manages the configuration files of a bundle.
        A bundle typically is a folder repo/bundle/<distribution>/<bundleID> in a
        GIT-Project. The project base of this GIT-Project is the `basedir`.
        The parts <distribution>/<bundleID> form the `bundleName`.
        For each bundle there should also exist an apt-repos configuration and
        a suite-identifier for apt-repos. apt-repos is used to scan the content of
        repositories involved in filling the bundle with packages.
    '''

    def __init__(self, bundleName, basedir=PROJECT_DIR):
        '''
            Parses `bundleName` which could be in the form [repo/bundle/]<distribution>[/<bundleID>]
            and either uses the specified bundleID or creates a new bundleID (after scanning the
            already exising bundles for <distribution>).
        '''
        regex = re.compile(r"^(repo/bundle/)?([\w\.]+)(/(\d+))?$")
        m = regex.match(bundleName)
        if not m:
            raise BundleError("bundleName '{}' doesn't match the pattern '{}'".format(bundleName, regex.pattern))
        else:
            (_, distribution, _, number) = m.groups()
        if not number: # create a new one
            highest = 0
            mydir = os.path.join(basedir, "repo", "bundle", distribution)
            if os.path.isdir(mydir):
                for f in os.listdir(mydir):
                    f = os.path.join(distribution, f)
                    m = regex.match(f)
                    if m:
                        number = int(m.group(4))
                        if number > highest:
                            highest = number
            number = highest + 1
        self.basedir = basedir
        self.distribution = distribution
        self.bundleName = "{}/{:04d}".format(distribution, int(number))
        self.__confDir = os.path.join(self.basedir, "repo", "bundle", self.bundleName, "conf")
        self.scl = os.path.join(self.__confDir, "sources_control.list")
        self._blacklist = "FilterList-blacklisted-binary-packages"
        self._infofile = "info"
        self._updatesfile = "updates"
        self._ownSuite = None
        self._templateEnv = Environment(loader=FileSystemLoader(self.getTemplateDir()))


    def setOwnSuite(self, ownSuiteStr):
        '''
            Sets the bundles `ownSuite` to a apt_repos.RepoSuite object derived from `ownSuiteStr`.
            `ownSuiteStr` could be a template string that after filling in the templates should
            describe the apt-repos suite identifier of the (typically server side) apt-repository
            representing the bundle's content.
        '''
        selector = ownSuiteStr
        if ownSuiteStr:
            (suites, selector) = self.parseSuitesStr(ownSuiteStr)
            if len(suites) > 0:
                self._ownSuite = sorted(suites)[0]
        if not self._ownSuite:
            raise BundleError("Own-Suite selector '{}' doesn't match an apt-repos suite for bundle '{}'.".format(selector, self.bundleName))


    def getOwnSuiteName(self):
        '''
            returns the apt-repos suite identifier for the bundle itself or None if
            `setOwnSuite()` was not called or apt-repos could not find a suite that matches ownSuiteStr.
        '''
        if self._ownSuite:
            return self._ownSuite.getSuiteName()
        return None


    def isEditable(self):
        '''
            This method checks the bundle's distribution file to see if the bundle is ReadOnly.
            It returns True if ReadOnly is not set.
        '''
        distributions = os.path.join(self.__confDir, "distributions")
        if os.path.isfile(distributions):
            tagfile = apt_pkg.TagFile(distributions)
            try:
                for distri in tagfile:
                    ro = distri.get('ReadOnly', 'No')
                    if ro.upper() == "YES":
                        return False
            finally:
                '''tagfile.close() - not supported by old apt-pkg'''
        return True


    def getInfoTag(self, tagname, fallback=None):
        '''
            This method extracts the tag <tagname> from the bundle's info-file
            and returns it's value or None, if the info-file or the tag doesn't exit.
        '''
        if os.path.isfile(self.getInfoFile()):
            tagfile = apt_pkg.TagFile(self.getInfoFile())
            try:
                for distri in tagfile:
                    value = distri.get(tagname, None)
                    if value:
                        return value
            finally:
                '''tagfile.close() - not supported by old apt-pkg'''
        return fallback


    def getTemplateDir(self):
        '''
            returns the path of the template folder that provides the template files
            for the creation of new BundleConfig.
        '''
        return os.path.join(self.basedir, "templates", self.distribution)

    def getBlacklistFile(self):
        return os.path.join(self.__confDir, self._blacklist)

    def getInfoFile(self):
        return os.path.join(self.__confDir, self._infofile)
    
    def getUpdatesFile(self):
        return os.path.join(self.__confDir, self._updatesfile)


    def getAptReposBasedir(self):
        '''
            Returns the path to the apt-repos configuration relative to this bundles basedir.
        '''
        return os.path.join(self.basedir, '.apt-repos')
    

    def createConfigFiles(self, updateRules, readOnly=False, deploymentStatus=DeploymentStatus.STAGING):
        '''
            This method creates config Files for this bundle based on the files found in the path
            provided by getTemplateDir(). `updateRules` is a list of UpdateRule objects.
            For each UpdateRule object, the content of the template file updates.skel
            is evaluated and added as one entry to conf/updates. Template files not
            ending with ".skel" or ".once" are also evaluated and written to a equally
            named file in the bundle's config folder. Files ending with ".once" are
            only created if they are not already present in the config folder (without
            the suffix .once). FilterSrcFiles are also created based on the provided
            `updateRules`. The value of `readOnly` will be transformed to "Yes" and "No"
            and passed as a value to the template evaluation (for the creation of a distributions
            file). The string value of `deploymentStatus` is also to the template evaluation.
            
            This method returns the path to the bundle's conf-Folder.
        '''
        logger.info("Creating config files for bundle '{}'".format(self.bundleName))
        if not os.path.isdir(self.__confDir):
            os.makedirs(self.__confDir)
        readOnly = "Yes" if readOnly else "No"
        # evaluate main templates
        for templateFile in [ "info.once", "distributions", "sources_control.list.once" ]:
            targetFile = os.path.join(self.__confDir, templateFile)
            if templateFile.endswith(".once"):
                targetFile = os.path.join(self.__confDir, templateFile[0:-len(".once")])
                if os.path.isfile(targetFile):
                    continue
            template = self._templateEnv.get_template(templateFile)
            with open(targetFile, "w", encoding="utf-8") as outfile:
                outfile.write(template.render(
                    creator=getpass.getuser(),
                    release=self.distribution,
                    readOnly=readOnly,
                    deploymentStatus=str(deploymentStatus),
                    bundleName=self.bundleName,
                    baseBundleName="NEW",
                    updateRules=" ".join([r.getRuleName() for r in updateRules])))
        # creating conf/updates file
        updatesSkel = self._templateEnv.get_template("updates.skel")
        blacklistFile = self._blacklist if os.path.exists(self.getBlacklistFile()) else ""
        with open(self.getUpdatesFile(), "w") as fh:
            print("\n".join([r.getUpdateRule(updatesSkel, self.getOwnSuiteName(), blacklistFile) for r in updateRules]), file=fh)
        # remove old FilterSrcLists:
        for f in os.listdir(self.__confDir):
            if re.match("^FilterSrcList-", f):
                os.remove(os.path.join(self.__confDir, f))    
        # creating FilterSrcLists:
        for r in updateRules:
            filename = os.path.join(self.__confDir, r.getFilterListFilename())
            with open(filename, "w") as fh:
                fh.write(r.getFilterFileContent())
        return self.__confDir


    def parseSuitesStr(self, suitesStr):
        '''
            Parses and replaces contained placeholders in suiteStr and returns a tuple
            (list, selector) where `list` is a the list of apt_repos.RepoSuite objects
            matched by the resulting suite selector and `selector` is the replaced suitesStr.
        '''
        if not suitesStr:
            return ([], suitesStr)
        subst = {"distribution" : self.distribution, "user" : getpass.getuser(), "bundle" : self.bundleName}
        suitesStr = suitesStr.format(**subst)
        return (sorted(apt_repos.getSuites(suitesStr.split(','))), suitesStr)


    def parseBlacklist(self):
        '''
            Parses the blacklist bundle and returns a set of blacklisted binary packages.
        '''
        blacklisted = set()
        if not os.path.isfile(self.getBlacklistFile()):
            return blacklisted
        with open(self.getBlacklistFile(), "r") as blacklistIn:
            for line in blacklistIn.readlines():
                line = line.strip()
                if len(line) == 0 or line.startswith('#'):
                    continue
                parts = line.split(" ")
                if len(parts) != 2 or parts[1] != "purge":
                    logger.warn("Ignoring invalid line in blacklist: {}".format(line))
                blacklisted.add(parts[0])
        return blacklisted


    def parseSourcesControlList(self):
        '''
            Parses the sources_control.list of the bundle and returns a mapping of
            `sourceName` to a set of `Package`-Objects for all active entries found
            in the sources_control.list. (active means no comments and package.status
            != isInfo()).
        '''
        sourcesDict = dict() # mapping sourceName -> set_of_packages
        if not os.path.isfile(self.scl):
            return sourcesDict
        try:
            with open(self.scl, "r") as sclIn:
                for line in sclIn.readlines():
                    line = line.strip()
                    if len(line) == 0 or line.startswith('#'):
                        continue
                    package = Package.getByActionString(line)
                    if not package or package.status.isInfo():
                        continue
                    packages = sourcesDict.get(package.sourceName, set())
                    sourcesDict[package.sourceName] = packages
                    packages.add(package)
        except Exception as e:
            msg = "Could not parse {}:\n{}".format(self.scl, e)
            for l in msg.split("\n"):
                logger.warn(l)
        for unused_source, packages in sorted(sourcesDict.items()):
            self._markActive(packages, packages)
        return sourcesDict


    def normalizeSourcesControlList(self):
        '''
            Minimizes and normalizes the sources_control.list. This is done just by parsing
            and rewriting the file since parseSourceControlList filters active lines.
            (see `parseSourcesControlList()`)
        '''
        if os.path.isfile(self.scl):
            sourcesDict = self.parseSourcesControlList()
            self._writeSourcesControlList(sourcesDict, dict())


    def normalizeBlacklist(self):
        '''
            Minimizes and normalizes the blacklist. This is done just by parsing
            and rewriting the file.
        '''
        if os.path.isfile(self.getBlacklistFile()):
            blacklisted = self.parseBlacklist()
            self._writeBlacklist(blacklisted)


    def updateSourcesControlList(self, supplierSuites, refSuites, prevSourcesDict, highlightedSuites, addFrom, upgradeFrom, no_update, cancel_remark=None):
        '''
           This method scans the provided `supplierSuites`, `refSuites` and the bundles ownSuite to
           create an user editable version of the sources_control.list providing a full overview
           about the bundles content and packages available from all supplierSuites.
           
           `refSuites` and the bundles ownSuite are used to determine if packages from supplierSuites
           should be regarded as new-, same-version-, upgrade- or downgrade-Packages (for a complete
           list of available classifiers see class PackageStatus).
           
           `prevSourcesDict` could be the result of parsing an already existing sources_control.list
           to ensure that the previous version of the sources_control.list can be merged to the
           updated list without loosing active entries (see `parseSourcesControlList(self)`).

           `highlightedSuites` defines a list of suites whose packages are sorted on top of the
           generated sources_control_list (for a better overview). Typically highlightesSuites 
           contains the bundles ownSuite (and maybe more).

           `addFrom` (a) and `upgradeFrom` (b) could be set to the suite identifiers whose packages
           should be automatically marked as active if they a) not alrady exits or b) are upgrades.
           This is to make mass add's or mass upgrades possible.

           All the above mentioned lists of suite identifiers expext apt_repos.RepoSuite Objects.
           If `no_update` is true, apt-repos is adviced to don't update it's apt cache for the
           particular repositories.
        '''
        reqFields = PackageField.getByFieldsString('CvsS')
        suites = set(supplierSuites)
        suites = suites.union(refSuites)
        logger.info("Creating sources_control.list for {} suites".format(len(suites)))

        sources = dict() # maps suite -> source-name -> QueryResult
        binaries = dict() # maps suite -> source-name (grouping binaries by their source-name) -> QueryResult
        sourcesNames = set() # set of all sources names
        highlighted = set(prevSourcesDict.keys()) # set of names of sources that should be highlighted
        action = ("Updating and " if not no_update else "") + "Querying"
        for suite in sorted(suites):
            logger.info("{} suite {}".format(action, suite))
            suite.scan(not no_update)
            sources[suite] = self._setToMap(suite.querySources('.', True, None, None, reqFields))
            # scan sources associated to binaries and filter the latest version for each source
            mostRecent = dict()
            for binSrc in sorted(suite.queryPackages('.', True, None, None, reqFields)):
                k = binSrc.getData()[0]
                mostRecent[k] = binSrc
            binaries[suite] = self._setToMap([ v for k, v in mostRecent.items() ])
            if suite in highlightedSuites:
                highlighted = highlighted.union(sources[suite].keys()).union(binaries[suite].keys())
            sourcesNames = sourcesNames.union(sources[suite].keys()).union(binaries[suite].keys())

        sourcesDict = dict()
        for source in sourcesNames:
            packages = sourcesDict.get(source, set())
            sourcesDict[source] = packages
            mergePackages = prevSourcesDict.get(source, set())
            for suite in suites:
                s = sources.get(suite, dict()).get(source, None)
                b = binaries.get(suite, dict()).get(source, None)
                package = Package.getByQueryResults(s, b)
                if package:
                    packages.add(package)
            # update PackageStatus and activate (only one)
            current = self._getCurrentReferenceVersion(packages, refSuites)
            for package in sorted(packages):
                package.updateStatus(current)
                if package.status == PackageStatus.IS_CURRENT and package.suiteName == self.getOwnSuiteName():
                    package.status = PackageStatus.SHOULD_BE_KEPT
            self._markActive(packages, mergePackages, addFrom, upgradeFrom)

        self._writeSourcesControlList(sourcesDict, highlighted, cancel_remark)


    def updateBlacklist(self, already_blacklisted, no_update, cancel_remark=None):
        '''
           This method scans the ownSuite for binary packages and adds these packages in deactivated form to
           the blacklist (if they are not already contained in blacklisted).

           All the above mentioned lists of suite identifiers expext apt_repos.RepoSuite Objects.
           If `no_update` is true, apt-repos is adviced to don't update it's apt cache for the
           particular repositories.
        '''
        if not self._ownSuite:
            logger.error("Can't update Blacklist as own-suite is not (yet) available.")
            return
        logger.info("Creating blacklist containing binary packages from the bundles own suite {}.".format(self._ownSuite))
        blacklisted = set()
        proposed = set()
        self._ownSuite.scan(not no_update)
        for p in self._ownSuite.queryPackages('.', True, None, None, PackageField.getByFieldsString('p')):
            package = p.getData()[0]
            if package in already_blacklisted:
                blacklisted.add(package)
            else:
                proposed.add(package)
        self._writeBlacklist(blacklisted, proposed, cancel_remark)


    def updateInfofile(self, basedOn=None):
        '''
            Rewrites the value of the properties 'Bundlename' and 'BasedOn' of the bundles infofile
            to self.bundleName and basedOn (if basedOn is set).

            This method returns the path to the updated infofile
        '''
        logger.info("Setting Bundlename in infofile to '{}'".format(self.bundleName))
        if basedOn:
            logger.info("Setting BasedOn in infofile to '{}'".format(basedOn))
        content = None
        with open(self.getInfoFile(), "r", encoding="utf-8") as infile:
            content = infile.readlines()
        if content:  
            with open(self.getInfoFile(), "w", encoding="utf-8") as out:
                for line in content:
                    line = re.sub("^Bundlename: (.*)$", "Bundlename: {}".format(self.bundleName), line)
                    if basedOn:
                        line = re.sub("^BasedOn: (.*)$", "BasedOn: {}".format(basedOn), line)
                    print(line, file=out, end='')
        return self.getInfoFile()
                

    def __len__(self):
        return len(self.bundleName)


    def __str__(self):
        return self.bundleName


    def __hash__(self):
        return hash((self.bundleName))


    def __eq__(self, other):
        if other == None:
            return False
        return self.bundleName == other.bundleName


    def __ne__(self, other):
        return not(self == other)


    def __lt__(self, other):
        return self.bundleName < other.bundleName


    def _getCurrentReferenceVersion(self, packages, refSuites):
        '''
        returns the one package from the list of (all equally named!) packages that
        is the `current` package from the view of this bundle. The `current` package
        is either the package found in Own-Suite (if so) or the package with
        the highest version found in any of the reference suites refSuites. This method
        returns None if the package is not contained in Own-Suite or refSuites.
        '''
        latest = None
        for package in sorted(packages):
            if package.suiteName == self.getOwnSuiteName():
                return package
            elif package.suiteName in [s.getSuiteName() for s in refSuites]:
                latest = package
        return latest


    def _markActive(self, packages, mergePackages, addFrom=None, upgradeFrom=None):
        '''
            This method has some kind of precedence mechanism to ensure that only one
            package from a list of (equally named) `packages` is marked active.

            In this context the lowest priority is given to all packages that are currently
            available (from scanning refSuites and ownSuite).
            
            medium priority to `mergePackages` which contains the packages that were active
            in a previous version of the sources_control.list and thus should set active
            (merged) into the new list.

            `addFrom`- and `upgradeFrom`-suites describe suites whose new / upgradable
            packages should always be marked as active (with highest precidence)
        '''
        markedForActivation = (None, 0) # tuple of (package, precedence)
        for package in sorted(packages):
            (_, precedence) = markedForActivation
            if   precedence < 1 and (package.status == PackageStatus.IS_CURRENT or package.status == PackageStatus.SHOULD_BE_KEPT):
                markedForActivation = (package, 1)
            elif precedence < 2 and package in mergePackages:
                markedForActivation = (package, 2)
            elif precedence < 3 and addFrom and package.status == PackageStatus.IS_MISSING and package.suiteName in [s.getSuiteName() for s in addFrom]:
                markedForActivation = (package, 3)
            elif precedence < 4 and upgradeFrom and package.status == PackageStatus.IS_UPGRADE and package.suiteName in [s.getSuiteName() for s in upgradeFrom]:
                markedForActivation = (package, 4)
        (markedForActivation, _) = markedForActivation
        if markedForActivation:
            markedForActivation.active = True


    def _writeSourcesControlList(self, sourcesDict, highlighted, cancel_remark=None):
        sep = "\n#" + "=" * 80
        with open(self.scl, 'w') as outfile:
            if cancel_remark:
                print(cancel_remark, file=outfile)
            s = None
            sourcesReordered = list()
            sourcesReordered.extend(sorted(highlighted))
            sourcesReordered.extend(sorted(sourcesDict.keys() - highlighted))
            for source in sourcesReordered:
                packages = sourcesDict.get(source, set())
                for package in sorted(packages):
                    if sep and len(highlighted) > 0 and not source in highlighted:
                        print(sep, file=outfile)
                        sep = None
                    if s and s != source:
                        print(file=outfile)
                    s = source
                    actionString = package.formatActionString()
                    print(actionString, file=outfile)


    def _writeBlacklist(self, blacklisted, proposed=set(), cancel_remark=None):
        sep = "\n#" + "=" * 20 + " uncomment to blacklist: " + "=" * 20
        with open(self.getBlacklistFile(), 'w') as outfile:
            if cancel_remark:
                print(cancel_remark, file=outfile)
            for package in sorted(blacklisted):
                print("{} purge".format(package), file=outfile)
            if proposed and len(proposed) > 0:
                print(sep, file=outfile)
                for package in sorted(proposed):
                    print("# {} purge".format(package), file=outfile)


    def _setToMap(self, myset):
        res = dict()
        for r in myset:
            if len(r.getData()) > 0:
                k = r.getData()[0]
                res[k] = r
        return res