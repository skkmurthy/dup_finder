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
    def __init__(self, file, dir, md5, mtime, size):
        self.file = file
        self.md5 = md5
        self.mtime = mtime
        self.size = size
        # this is for processing purposes only. it is not persisted in FP DB
        self.path = os.path.join(dir,file)

class FPCache:
    def __init__(self, path, logger):
        self.path = path
        self.logger = logger
        self.dir = os.path.dirname(os.path.dirname(path))

        self.fpByFile = dict()
        self.fpByMd5 = dict()
        self.deletedFiles = []

        self.__readDB()
        self.__cacheDirty = False

    def __del__(self):
        self.flushCache()

    def __readDB(self):
        self.logger.debug("reading fingerprint database...")

        if not os.path.isfile(self.path):
            # there is nothing to read
            self.logger.warn("fingerprint database file not found")
            return

        fh = open(self.path, 'r')
        for line in fh:
            line = line.rstrip()
            if not line:
                continue
            vals = line.split('|')

            fp = Fingerprint(vals[0], self.dir, vals[1], float(vals[2]), long(vals[3]))

            self.fpByFile[vals[0]] = fp
            self.fpByMd5[vals[1]] = fp

    def flushCache(self):
        if not self.__cacheDirty:
            return

        self.logger.info("flushing fingerprints to file...")
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
            self.logger.info("modifying {} with digest {} in cache...".format(file, md5))

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
            self.logger.info("adding new file {} with digest {} to cache...".format(file, md5))
            fp = Fingerprint(file, self.dir, md5, float(mtime), long(size))

            self.fpByFile[file] = fp
            self.fpByMd5[md5] = fp

        self.__cacheDirty = True

    def haveDeletedFiles(self, lsFiles):
        # for each file in the cache, check if it can be 'ls'ed
        for f, fp in self.fpByFile.iteritems():
            if f not in lsFiles:
                return True

    def isDirty(self):
        return self.__cacheDirty

    def removeDeletedFiles(self, lsFiles):
        # for each file in the cache, check if it can be 'ls'ed
        for f in self.fpByFile.keys():
            if f not in lsFiles:
                # remove from the cache and mark dirty
                self.logger.warn("deleting file {} with digest {} from cache..."\
                                 .format(f, self.fpByFile[f].md5))
                assert self.fpByMd5[self.fpByFile[f].md5]
                del self.fpByMd5[self.fpByFile[f].md5]
                del self.fpByFile[f]

                self.__cacheDirty = True

    def checkFile(self, fp):
        # check if a file with the fingerprint exists and also confirm that the size matches.
        if fp.md5 in self.fpByMd5:
            orig = self.fpByMd5[fp.md5]
            self.logger.info("found a dup. remote: <{},{},{}>, local: <{},{},{}>"\
                             .format(fp.path, fp.md5, fp.size, orig.path, orig.md5, orig.size))
            if fp.size != orig.size:
                msg = "sizes don't match! remote file size: {}, local file size: {}"\
                        .format(fp.size, orig.size)
                self.logger.warn(msg)
                raise Exception(msg)
                return None

            return orig
        else:
            return None

class File:
    def __init__(self, dirEntry):
        assert dirEntry.is_file()

        self.fileName = dirEntry.name
        self.dirEntry = dirEntry

class Directory:
    def __init__(self, path, checkMode=False):
        if not os.path.isdir(path):
            raise Exception(path + " does not exist or is not a directory")
        self.path = os.path.abspath(path)
        self.checkMode = checkMode

        self.logFile = os.path.join(self.path, ".dp", Logger.Logger.newLogFileName())
        self.__createPrivateDirectory()
        self.logger = Logger.Logger(self.logFile, ntpath.basename(self.path))

        self.fpDBFile = os.path.join(self.path, ".dp", "fpDB.txt")
        self.fpCache = FPCache(self.fpDBFile, self.logger)

        self.files = dict()
        self.subDirs = []
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
                self.files[element.name] = File(element)

    def __createPrivateDirectory(self):
        privDir = os.path.join(self.path, ".dp")
        if os.path.isdir(privDir):
            return
        else:
            assert os.path.isdir(self.path)
            os.makedirs(privDir)

    def __hasFileChanged(self, file):
        fp = self.fpCache.getFpForFile(file.fileName)
        return None == fp\
                or fp.size != file.dirEntry.stat().st_size\
                or long(fp.mtime) < long(file.dirEntry.stat().st_mtime)

    @staticmethod
    def __hashFile(file):
        BUF_SIZE = 65536

        md5 = hashlib.md5()

        with open(file, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break

                md5.update(data)

        return md5.hexdigest()

    def __fingerprintFile(self, file):
        self.fpCache.addFingerprint(file.dirEntry.name,
                                    Directory.__hashFile(file.dirEntry.path),\
                                    file.dirEntry.stat().st_mtime,\
                                    file.dirEntry.stat().st_size)

    def fingerPrint(self, dryRun=False):
        if self.checkMode:
            raise Exception("fingerprinting is not allowed in check mode")

        self.logger.debug("fingerprinting {}...".format(self.path))

        # finger print sub directories first
        [subdir.fingerPrint(dryRun) for subdir in self.subDirs]

        # fingerprint files
        for f, info in self.files.iteritems():
            if self.__hasFileChanged(info):
                self.logger.debug("fingerprinting {}...".format(f))
                if not dryRun:
                    self.__fingerprintFile(info)

        # handle file deletes
        if self.fpCache.haveDeletedFiles(self.files.keys()):
            self.logger.debug("removing fingerprint for deletes files...")
            if not dryRun :
                self.fpCache.removeDeletedFiles(self.files.keys())

        # flush to DB
        if dryRun:
            assert not self.fpCache.isDirty()
        else:
            self.fpCache.flushCache()

    def checkFile(self, fp):
        self.logger.debug("checking for file <{},{},{}> exists...".format(fp.file, fp.md5, fp.size))

        # check current directory first
        orig = self.fpCache.checkFile(fp)
        if orig != None:
            return orig

        # check sub directories
        for dir in self.subDirs:
            orig = dir.checkFile(fp)
            if None != orig:
                return orig

        return None

    def getFileList(self):
        return self.files.keys()

    def getFpForFile(self, f):
        return self.fpCache.getFpForFile(f)
