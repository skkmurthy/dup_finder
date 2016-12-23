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

class FPCache:
    def __init__(self, path):
        self.path = path
        self.fpByFile = dict()
        self.fpByMd5 = dict()
        self.deletedFiles = []
        self.__readDB()
        self.__cacheDirty = False

    def __del__(self):
        self.flushCache()

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

    def flushCache(self):
        if not self.__cacheDirty:
            return

        fh = open(self.path, "w")
        for f, fp in self.fpByFile.iteritems():
            if f in self.deletedFiles:
                continue

            fh.write("{}|{}|{}|{}\n".format(fp.file, fp.md5, fp.mtime, fp.size))

        fh.close()

        # also create deletedFiles variable
        self.deletedFiles = []

        self.__cacheDirty = False

    def getFpForFile(self, file):
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

            self.fpByFile[file] = fp
            self.fpByMd5[md5] = fp

        self.__cacheDirty = True

    def haveDeletedFiles(self, lsFiles):
        # for each file in the cache, check if it can be 'ls'ed
        for f, fp in self.fpByFile.iteritems():
            if f not in lsFiles:
                return True

    def dirty(self):
        return self.__cacheDirty

    def removeDeletedFiles(self, lsFiles):
        # for each file in the cache, check if it can be 'ls'ed
        for f in self.fpByFile.keys():
            if f not in lsFiles:
                # remove from the cache and mark dirty
                assert self.fpByMd5[self.fpByFile[f].md5]
                del self.fpByMd5[self.fpByFile[f].md5]
                del self.fpByFile[f]

                self.__cacheDirty = True

class File:
    def __init__(self, dirEntry, fpCache):
        assert dirEntry.is_file()

        self.fileName = dirEntry.name
        self.dirEntry = dirEntry
        self.fpCache = fpCache

    def needsRefingerprint(self):
        fp = self.fpCache.getFpForFile(self.fileName)
        return None == fp or fp.size != self.dirEntry.stat().st_size or long(fp.mtime) < long(self.dirEntry.stat().st_mtime)

    def reFingerprint(self, force=False):
        self.fpCache.addFingerprint(self.dirEntry.name, hashlib.md5(self.dirEntry.path).hexdigest(), self.dirEntry.stat().st_mtime, self.dirEntry.stat().st_size)

class Directory:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise Exception(path + " does not exist or is not a directory")
        self.path = path
        self.fpDBFile = os.path.join(path, ".dp", "fpDB.txt")
        self.fpCache = FPCache(self.fpDBFile)
        self.logFile = os.path.join(path, ".dp", Logger.Logger.newLogFileName())
        self.__createPrivateDirectory()
        self.logger = Logger.Logger(self.logFile, ntpath.basename(self.path))
        self.subDirs = []
        self.files = dict()
        self.__lsDir()

    ## This function creates Directory object for each subdirectory and caches the modify times for
    #  all files
    def __lsDir(self):
        for element in scandir(self.path):
            if element.name == ".dp":
                continue
            if element.is_dir():
                self.subDirs.append(Directory(element.path))
            elif element.is_file():
                self.files[element.name] = File(element, self.fpCache)

    def __createPrivateDirectory(self):
        privDir = os.path.join(self.path, ".dp")
        if os.path.isdir(privDir):
            return
        else:
            assert os.path.isdir(self.path)
            os.makedirs(privDir)

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

        # handle file deletes
        if self.fpCache.haveDeletedFiles(self.files.keys()):
            self.logger.debug("removing fingerprint for deletes files...")
            if not dryRun :
                self.fpCache.removeDeletedFiles(self.files.keys())

        # flush to DB
        if dryRun:
            assert not self.fpCache.dirty()
        else:
            self.fpCache.flushCache()
