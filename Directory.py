#!/usr/bin/python

import os.path
import Logger
try:
    from os import scandir
except ImportError:
    from scandir import scandir

from time import strftime, localtime
import ntpath
import hashlib
from enum import IntEnum
import pprint

class Fingerprint:
    def __init__(self, file, md5, mtime, size):
        self.file = file.replace(',', '_')
        self.md5 = md5
        self.mtime = mtime
        self.size = size

    def __str__(self):
        return "<Fingerprint file: {}, md5: {}, mtime: {}, size: {}>".format(self.file, self.md5, self.mtime, self.size)

class File:
    def __init__(self, dirEntry, fingerPrint=None):
        assert dirEntry.is_file()

        self.fileName = dirEntry.name
        self.dirEntry = dirEntry
        self.fingerPrint = fingerPrint
        assert None == fingerPrint or self.fingerPrint.file == self.dirEntry.name

    def setFingerprint(self, fp):
        self.fingerPrint = fp

    def needsRefingerprint(self):
        return None == self.fingerPrint or self.dirEntry.stat().st_size != self.fingerPrint.size or long(self.fingerPrint.mtime) < long(self.dirEntry.stat().st_mtime)

    def reFingerprint(self, force=False):
        if not force and not self.needsRefingerprint():
            return

        self.fingerPrint = Fingerprint(self.dirEntry.name, hashlib.md5(self.dirEntry.path).hexdigest(), self.dirEntry.stat().st_mtime, self.dirEntry.stat().st_size)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "file: {}, dirEntry: {}, fp: {}".format(self.fileName, self.dirEntry, self.fingerPrint)

class Directory:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise Exception(path + " does not exist or is not a directory")
        self.path = path
        self.fpDBFile = os.path.join(path, ".dp", "fpDB.txt")
        self.logFile = os.path.join(path, ".dp", Logger.Logger.newLogFileName())
        self.__createPrivateDirectory()
        self.logger = Logger.Logger(self.logFile, ntpath.basename(self.path))
        self.dirMTime = os.stat(self.path).st_mtime
        self.fpDBMTime = self.__getfpDBMTime()
        self.subDirs = []
        self.files = dict()
        self.deletedFiles = []
        self.__lsDir()
        self.__readFpDB();

    def __getfpDBMTime(self):
        if not os.path.isfile(self.fpDBFile):
            return 0
        else:
            return os.stat(self.fpDBFile).st_mtime

    def __getMTimeForFile(self, file):
        return os.stat(os.path.join(self.path, file)).st_mtime

    ## This function creates Directory object for each subdirectory and caches the modify times for
    #  all files
    def __lsDir(self):
        headerPrinted = False

        for element in scandir(self.path):
            if element.name == ".dp":
                continue
            if element.is_dir():
                if not headerPrinted:
                    headerPrinted = True 

                self.subDirs.append(Directory(element.path))
            elif element.is_file():
                self.files[element.name.replace(',', '_')] = File(element)

    def __readFpDB(self):
        if not os.path.isfile(self.fpDBFile):
            return

        fh = open(self.fpDBFile, 'r')
        for line in fh:
            line = line.rstrip()
            if not line:
                continue
            vals = line.split(',')
            fp = Fingerprint(vals[0], vals[1], float(vals[2]), long(vals[3]))

            # handle file deletes
            if not vals[0] in self.files:
                self.deletedFiles.append(vals[0])
            else:
                self.files[vals[0]].setFingerprint(fp)

    def __createPrivateDirectory(self):
        privDir = os.path.join(self.path, ".dp")
        if os.path.isdir(privDir):
            return
        else:
            assert os.path.isdir(self.path)
            os.makedirs(privDir)

    def __flushFpDB(self):
        self.__createPrivateDirectory()

        fh = open(self.fpDBFile, "w")
        for f, info in self.files.iteritems():
            assert not info.needsRefingerprint()
            fp = info.fingerPrint
            fh.write("{},{},{},{}\n".format(fp.file, fp.md5, fp.mtime, fp.size))

        fh.close()

        # also create deletedFiles variable
        self.deletedFiles = []

    def fingerPrintNeeded(self):
        self.logger.debug("checking {} if fingerpring is needed...".format(self.path))
        if not os.path.isfile(self.fpDBFile):
            self.logger.debug("fpDBFile does not exist; finger print needed")
            return True

        # check if there are files that are deleted
        if self.deletedFiles:
            self.logger.debug("files has been deleted ({}); fingerprint needed".format(','.join(self.deletedFiles)))
            return True

        # check if sub directories need to be fingerPrinted
        for d in self.subDirs:
            if d.fingerPrintNeeded():
                self.logger.debug("sud dir {} need to be fingerprinted, so fingerprint needed".format(d.path))
                return True

        # check if files have changed or have been modified
        for f, info in self.files.iteritems():
            if info.needsRefingerprint():
                self.logger.debug("{} needs to be fingerprinted, so fingerprint needed".format(f))
                return True

        # no changes detected
        self.logger.debug("{} does not have to fingerprinted".format(self.path))
        return False

    def fingerPrint(self, dryRun=False):
        self.logger.debug("fingerprinting {}...".format(self.path))

        # finger print sub directories first
        [subdir.fingerPrint(dryRun) for subdir in self.subDirs]

        # fingerprint files
        for f, info in self.files.iteritems():
            if info.needsRefingerprint():
                self.logger.debug("fingerprinting {}...".format(f))
                if not dryRun:
                    info.reFingerprint()

        # flush to DB
        if not dryRun:
            self.__flushFpDB()
