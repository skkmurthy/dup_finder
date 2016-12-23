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
        self.file = file
        self.md5 = md5
        self.mtime = mtime
        self.size = size

    def __str__(self):
        return "<Fingerprint file: {}, md5: {}, mtime: {}, size: {}>" \
                    .format(self.file, self.md5, self.mtime, self.size)

class FPCache:
    def __init__(self, path):
        self.path = path
        self.fpByFile = dict()
        self.fpByMd5 = dict()
        self.deletedFiles = []
        self.__readDB()
        self.__cacheDirty = False

    def __del__(self):
        self.__flushDB()

    def __readDB(self):
        if not os.path.isfile(self.path):
            # there is nothing to read
            return

        fh = open(self.path, 'r')
        for line in fh:
            line = line.rstrip()
            if not line:
                continue
            vals = line.split('|')

            fp = Fingerprint(vals[0], vals[1], float(vals[2]), long(vals[3]))

            self.fpByFile[vals[0]] = fp
            self.fpByMd5[vals[1]] = fp

    def __flushDB(self):
        if not self.__cacheDirty:
            return

        fh = open(self.path, "w")
        for f, fp in self.fpByFile:
            if f in self.deletedFiles:
                continue

            fh.write("{}|{}|{}|{}\n".format(fp.file, fp.md5, fp.mtime, fp.size))

        fh.close()

        # also create deletedFiles variable
        self.deletedFiles = []

        self.__cacheDirty = False

    def fpForFile(self, file):
        if not self.fpByFile:
            return None
        elif file in self.fpByFile:
            return self.fpByFile[file]
        else:
            return None

    def addFingerprint(self, file, md5, mtime, size):
        if file in self.fpByFile:
            # modify FP in fpByFile and then for dpByMd5, delete entry for old md5 and add it an
            # entry for new md5

            assert self.fpByFile[file].file == file
            # record old FP
            oldFp = self.fpByFile[file].md5

            self.fpByFile[file].md5 = md5
            self.fpByFile[file].mtime = mtime
            self.fpByFile[file].size = size

            # add by new fingerprint
            del self.fpByMd5[oldFp]
            self.fpByMd5[md5] = self.fpByFile[file]
        else:
            # we need to create a new fingerprint and add to both dictionaries
            fp = Fingerprint(file, md5, float(mtime), long(size))

            self.fpByFile[vals[0]] = fp
            self.fpByMd5[vals[1]] = fp

        self.__cacheDirty = True

    def handleDeletedFiles(self, lsFiles):
        # for each file in the cache, check if it can be 'ls'ed
        for f, fp in self.fpByFile:
            if f not in lsFiles:
                # remove from the cache and mark dirty
                assert self.fpByMd5[fp.md5]
                del self.fpByMd5[fp.md5]
                del self.fpByFile[f]

                self.__cacheDirty = True

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
        self.subDirs = []
        self.files = dict()
        self.deletedFiles = []
        self.__lsDir()
        self.__readFpDB()

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
                self.files[element.name] = File(element)

    def __readFpDB(self):
        if not os.path.isfile(self.fpDBFile):
            return

        fh = open(self.fpDBFile, 'r')
        for line in fh:
            line = line.rstrip()
            if not line:
                continue
            vals = line.split('|')
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
            fh.write("{}|{}|{}|{}\n".format(fp.file, fp.md5, fp.mtime, fp.size))

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
