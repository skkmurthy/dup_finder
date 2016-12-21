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

class Directory:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise Exception(path + " does not exist or is not a directory")
        self.path = path
        self.fpDBFile = os.path.join(path, ".dp", "fpDB.txt")
        self.logFile = os.path.join(path, ".dp", Logger.Logger.newLogFileName())
        self.logger = Logger.Logger(self.logFile, ntpath.basename(self.path))
        self.dirMTime = os.stat(self.path).st_mtime
        self.fpDBMTime = self.__getfpDBMTime()
        self.subDirs = []
        self.files = dict()
        self.lsDir()

    def __getfpDBMTime(self):
        if not os.path.isfile(self.fpDBFile):
            return 0
        else:
            return os.stat(self.fpDBFile).st_mtime

    def __getMTimeForFile(self, file):
        return os.stat(os.path.join(self.path, file)).st_mtime

    ## This function creates Directory object for each subdirectory and caches the modify times for all files
    def lsDir(self):
        headerPrinted = False

        for element in scandir(self.path):
            if element.name == ".dp":
                continue
            if element.is_dir():
                p = os.path.join(self.path, element.name)
                if not headerPrinted:
                    self.logger.debug("list of sub directories for {}:".format(self.path))
                    headerPrinted = True 

                self.logger.debug(p)
                self.subDirs.append(Directory(p))
            elif element.is_file():
                self.files[element.name] = element.stat().st_mtime

    def fingerPrint(self):
        self.logger.debug("fingerprinting {}...".format(self.path))

        # figure out if all the files need to be fingerprinted
        fpAllFiles = False
        if not os.path.isfile(self.fpDBFile):
            fpAllFiles = True

        # finger print sub directories first
        [subdir.fingerPrint() for subdir in self.subDirs]

        # list files that need to be finger printed
        files = []
        for file, mTime in self.files.iteritems():
            if fpAllFiles or mTime > self.fpDBMTime:
                files.append(file)

        if not files:
            self.logger.info("no files to fingerprint in '{}'".format(self.path))
        else:
            self.logger.info("files that need to be fingerprinted in '{}': {}".format(self.path, ', '.join(files)))

        [self.logger.debug(hashlib.md5(os.path.join(self.path, file)).hexdigest()) for file in files]
        # TODO - need to handle deleted files
