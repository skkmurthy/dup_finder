#!/usr/bin/python

import os.path
import Logger
from time import strftime, localtime
import ntpath

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
        self.initSubDirs()

    def __getfpDBMTime(self):
        if not os.path.isfile(self.fpDBFile):
            return 0
        else:
            return os.stat(self.fpDBFile).st_mtime

    def __getMTimeForFile(self, file):
        return os.stat(os.path.join(self.path, file)).st_mtime


    ## This function determines if there have been changes to the directory by comparing the mtime
    #  for the finger print file against the mtime of the directory
    def dirHasChanged(self):
        # finger print file must exist
        self.logger.debug("fingerprint DB file modified at {}".
                          format(strftime("%Y-%m-%d %H:%M:%S", localtime(self.fpDBMTime))))
        self.logger.debug("{} was modified at {}".
                          format(self.path, strftime("%Y-%m-%d %H:%M:%S", localtime(self.dirMTime))))

        return self.fpDBMTime < self.dirMTime

    def initSubDirs(self, checkForModifiedFiles=False):
        self.subDirs = []
        headerPrinted = False
        for subdir in os.listdir(self.path):
            if subdir != ".dp" and os.path.isdir(os.path.join(self.path, subdir)):
                p = os.path.join(self.path, subdir)
                if not headerPrinted:
                    self.logger.debug("list of sub directories for {}:".format(self.path))
                    headerPrinted = True 

                self.logger.debug(p)
                self.subDirs.append(Directory(p))

    def fingerPrint(self, checkForModifiedFiles=False):
        self.logger.debug("fingerprinting {}...".format(self.path))

        # figure out if all the files need to be fingerprinted
        fpAllFiles = False
        if not os.path.isfile(self.fpDBFile):
            fpAllFiles = True

        # finger print sub directories first
        [subdir.fingerPrint(checkForModifiedFiles) for subdir in self.subDirs]

        if not checkForModifiedFiles and not fpAllFiles and not self.dirHasChanged():
            # there is nothing to do here
            self.logger.info("no files to fingerprint in '{}'".format(self.path))
            return

        # list files that need to be finger printed
        files = []
        [files.append(f) 
         for f in os.listdir(self.path) 
         if os.path.isfile(os.path.join(self.path, f)) and (fpAllFiles or self.__getMTimeForFile(f) > self.fpDBMTime)]

        self.logger.info("files that need to be fingerprinted in '{}': {}".format(self.path, ', '.join(files)))

        # TODO - need to handle deleted files
