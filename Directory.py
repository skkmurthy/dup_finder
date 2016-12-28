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
from shutil import copyfile
import time

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

            fp = Fingerprint(vals[0],\
                             self.dir,\
                             vals[1],\
                             float(vals[2]),\
                             long(vals[3]))

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

            fh.write("{}|{}|{}|{}\n"\
                     .format(fp.file, fp.md5, fp.mtime, fp.size))

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
            # modify FP in fpByFile and then for dpByMd5, delete entry 
            # for old md5 and add it an
            # entry for new md5
            self.logger.info("modifying {} with digest {} in cache..."\
                             .format(file, md5))

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

            # this assert should not fire unless there are duplicates in 
            # the same directory
            if  md5 in self.fpByMd5:
                self.logger.warn("{} is same as {} in {}"\
                    .format(file, self.fpByMd5[md5].file,self.dir))

            # we need to create a new fingerprint and add to dictionaries
            self.logger.info("adding file {} with digest {} to cache..."\
                .format(file, md5))
            fp = Fingerprint(file, self.dir, md5, float(mtime), long(size))

            self.fpByFile[file] = fp
            self.fpByMd5[md5] = fp

        self.__cacheDirty = True

    def deleteFingerprint(self, fp):
        assert fp.file in self.fpByFile
        # TD01: This assert is hit if there are duplicates in the same directory
        # assert fp.md5 in self.fpByMd5

        del self.fpByFile[fp.file]
        # TD01: The if condition is needed to handle the case when there are duplicates
        # in the same directory
        if fp.md5 in self.fpByMd5:
            del self.fpByMd5[fp.md5]

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
                self.logger.warn("deleting {} with digest {} from cache..."\
                                 .format(f, self.fpByFile[f].md5))
                # assert self.fpByMd5[self.fpByFile[f].md5]
                if self.fpByFile[f].md5 in self.fpByMd5:
                    del self.fpByMd5[self.fpByFile[f].md5]
                del self.fpByFile[f]

                self.__cacheDirty = True

    def checkFile(self, fp):
        # check if a file with the fingerprint exists and also confirm 
        # that the size matches.
        if fp.md5 in self.fpByMd5:
            orig = self.fpByMd5[fp.md5]
            self.logger.info(
                "found a dup. remote: <{},{},{}>, local: <{},{},{}>"\
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

class FileStat:
    def __init__(self, dirEntry):
        assert dirEntry.is_file()

        self.fileName = dirEntry.name
        self.dirEntry = dirEntry

class Directory:
    def __repr__(self):
        return "Directory"

    IgnoredFiles = (\
                    ".DS_Store",\
                    "._.DS_Store",\
                    )

    IgnoredDirs = (\
                   "/media/divya/win_vol/Users/manaswini/Desktop/Desktop",\
                   "/media/divya/win_vol/Users/manaswini/Documents/Sony",\
                   )

    class __DupInfo:
        def __init__(self, file, fp, origFp):
            self.file = file
            self.fp = fp
            self.origFp = origFp

    @staticmethod
    def __getScriptDir():
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        if scriptDir == None or not os.path.isdir(scriptDir):
            raise Exception("unable to figure out script directory")
        return scriptDir

    __rdOnlyDirs = []
    __rdOnlyDirsCheckDone = False
    @staticmethod
    def __getRdOnlyDirsList():
        if Directory.__rdOnlyDirsCheckDone:
            return __rdOnlyDirs

        Directory.rdOlyDirs = True

        f = os.path.join(Directory.__getScriptDir(), "rd_only_dirs")
        if not os.path.isfile(f):
            # no read only dirs have been defined
            return Directory.__rdOnlyDirs

        fh = open(f, "r")
        for l in fh:
            l = l.rstrip()
            if not l:
                continue
            Directory.__rdOnlyDirs.append(l)

        return Directory.__rdOnlyDirs

    # This function returns path to dpWorkDir if the directory provided is in a
    # read only directory
    @staticmethod
    def __getAltWorkDir(dir):
        path = os.path.abspath(dir)

        # check if the directory is in read only directory and get the path to the
        # parent
        rdDirs = Directory.__getRdOnlyDirsList()
        rdParent = None
        for d in rdDirs:
            if d in path:
                rdParent = d
                break

        # return None if the directory is not in a read-only parent
        if rdParent == None:
           return None

        # replace rdParent with path to the dpWorkDir
        dpWorkDir = os.path.join(Directory.__getScriptDir(), 'dp_work_dir')
        path = path.replace(rdParent, dpWorkDir)
        return path
 


    def __init__(self, path, checkMode=False):
        if not os.path.isdir(path):
            raise Exception(path + " does not exist or is not a directory")

        self.path = os.path.abspath(path)
        self.dpWorkDir = Directory.__getAltWorkDir(self.path)
        if None == self.dpWorkDir:
            self.dpWorkDir = self.path
	else:
            print "using {} as work dir...".format(self.dpWorkDir)

        self.checkMode = checkMode
        self.dirName = ntpath.basename(self.path)

        self.privDir = os.path.join(self.dpWorkDir, ".dp")
        self.logDir = os.path.join(self.privDir, "logs")
        Directory.__createDirectory(self.logDir)
        self.logFile = os.path.join(self.logDir, Logger.Logger.newLogFileName())
        self.logger = Logger.Logger(self.logFile, self.dirName)

        self.fpDBFile = os.path.join(self.privDir, "fpDB.txt")
        self.fpCache = FPCache(self.fpDBFile, self.logger)

        self.fstatByName = dict()
        self.subDirs = []
        self.__lsDir()

    ## This function creates Directory object for each subdirectory and caches the modify times for
    #  all files
    def __lsDir(self):
        for element in scandir(self.path):
            if element.name == ".dp":
                continue
            if element.is_dir():
                if element.path in Directory.IgnoredDirs:
                    self.logger.warn("ignoring {}...".format(element.path))
                    continue

                self.subDirs.append(Directory(element.path))
            elif element.is_file() and element.name not in Directory.IgnoredFiles:
                self.fstatByName[element.name] = FileStat(element)

    @staticmethod
    def __createDirectory(path):
        if os.path.isdir(path):
            return
        else:
            os.makedirs(path)

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

        self.logger.info("fingerprinting {}...".format(os.path.basename(self.path)))

        # finger print sub directories first
        for subdir in self.subDirs:
            self.logger.info("fingerprinting {}...".format(os.path.basename(subdir.path)))
            subdir.fingerPrint(dryRun)

        # fingerprint files
        for f, info in self.fstatByName.iteritems():
            if self.__hasFileChanged(info):
                self.logger.info("fingerprinting {}...".format(f))
                if not dryRun:
                    self.__fingerprintFile(info)

        # handle file deletes
        if self.fpCache.haveDeletedFiles(self.fstatByName.keys()):
            self.logger.info("removing fingerprint for deletes files...")
            if not dryRun :
                self.fpCache.removeDeletedFiles(self.fstatByName.keys())

        # flush to DB
        if dryRun:
            assert not self.fpCache.isDirty()
        else:
            self.fpCache.flushCache()

        self.logger.info("fingerprinting done")

    def checkFile(self, fp):
        self.logger.debug("checking for file <{},{},{}>...".format(fp.file, fp.md5, fp.size))

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

    def removeDups(self, refDir, compareOnly=False):
        self.logger.info("removing dups with ref dir {}...".format(refDir.path))
        dups = dict()

        # remove dups from sub directories
        for subDir in self.subDirs:
            self.logger.info("removing dups from {}...".format(subDir.dirName))
            subDir.removeDups(refDir, compareOnly)

        # make a list of dups
        for f in self.fstatByName.keys():
            self.logger.info("checking for {} in {}...".format(f, refDir.path))
            fp = self.fpCache.getFpForFile(f)
            orig = refDir.checkFile(fp)
            if None != orig:
                dups[f] = Directory.__DupInfo(f, fp, orig)

        if not dups:
            self.logger.info("no dups found")
            return
        else:
            self.logger.debug("list of dups:")
            for f, info in dups.iteritems():
                self.logger.debug("{} is a dup of {}".format(info.fp.path, info.origFp.path))

        if compareOnly:
            self.logger.info("remove dups done")
            return

        # remove dups
        dupsDir = os.path.join(self.privDir, "dups")
        Directory.__createDirectory(dupsDir)
        origsDir = os.path.join(dupsDir, "origs")
        Directory.__createDirectory(origsDir)
        for f, info in dups.iteritems():
            self.logger.info("removing {}...".format(f))
            # move file to dup/<filename>
            os.rename(info.fp.path, os.path.join(dupsDir, f))

            # add a symlink
            os.symlink(info.origFp.path, os.path.join(origsDir, f))

            # remove from fingerprint from cache
            self.fpCache.deleteFingerprint(info.fp)

        # update FP DB
        self.fpCache.flushCache()

        self.logger.info("remove dups done")

    def __addFilesToHash(self, hash):
        # pass it down to sub dirs first
        [subdir.__addFilesToHash(hash) for subdir in self.subDirs]

        for f in self.fstatByName.keys():
            fp = self.fpCache.getFpForFile(f)
            if None == fp:
                raise Exception("directory {} needs to be fingerprinted".format(self.path))

            if fp.md5 not in hash:
                hash[fp.md5] = [fp.path]
            else:
                hash[fp.md5].append(fp.path)

    def checkForInternalDups(self):
        self.logger.info("checking for internal dups...")
        # collect all the hashes by file and check for hashes that have more than one file
        md5Hash = dict()
        self.__addFilesToHash(md5Hash)

        self.logger.info("list of dups:")
        for md5, files in md5Hash.iteritems():
            if len(files) > 1:
                msg = ""
                firstDone = False
                for f in files:
                    if not firstDone:
                        msg = f
                        firstDone = True
                    else:
                        msg = msg + ", " + f

                self.logger.info(msg)

        self.logger.info("internal dup check done")

    ## This function copies over the srcFile to current directory and then adds
    #  the fingerprint to cache
    #  @param srcFile - Fully qualified path to the source file.
    #  @param srcFileFP - Source file fingerprint
    def __copyFile(self, srcFile, srcFileFP):
        # move the file on disk
        copyfile(srcFile, os.path.join(self.path, os.path.basename(srcFile)))

        # add FP to cache
        self.fpCache.addFingerprint(srcFileFP.file, srcFileFP.md5, time.time(), srcFileFP.size)

    ## This function compares files in the current directory against the
    #  the reference directory and then copies unique files over to the specified
    #  destination folder.
    #  @param refDir - Directory object for reference directory. All files in
    #                  the current directory will be checked against refDir to
    #                  check if they are uinque.
    #  @param dst    - Directory object for destination directory. 
    def copyUniques(self, refDir, dst):
        self.logger.info("copying unique files to {} with reference dir {}".format(dst.path, refDir.path))
        # move uniques from sub dirs first
        for subDir in self.subDirs:
            self.logger.info("copying unique files from {}...".format(subDir.dirName))
            p = os.path.join(dst.path, subDir.dirName)
            if not os.path.isdir(p):
                Directory.__createDirectory(p)
            d = Directory(p)
            subDir.copyUniques(refDir, d)

        # copy unique files
        for f in self.fstatByName.keys():
            fp = self.fpCache.getFpForFile(f)
            orig = refDir.checkFile(fp)
            if None == orig:
                self.logger.info("{} is unique".format(f))
                dst.__copyFile(os.path.join(self.path, f), fp)
            else:
                self.logger.info("{} is a dup of {}".format(f, orig.path))

        self.logger.info("copying unique files done")
