#!/usr/bin/python

import os.path
import Logger
from time import strftime, localtime

class Directory:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise Exception(path + " does not exist or is not a directory")
        self.path = path
        self.fpFile = os.path.join(path, ".dp", "fingerprints.txt")
        self.logFile = os.path.join(path, ".dp", Logger.Logger.newLogFileName())
        self.logger = Logger.Logger(self.logFile, self.path)

    ## This function determines if there have been changes to the directory by comparing the mtime
    #  for the finger print file against the mtime of the directory
    def dirHasChanged(self):
        # finger print file must exist
        assert os.path.isfile(self.fpFile)
        self.logger.debug("fingerprint was file modified at {}".
                          format(strftime("%Y-%m-%d %H:%M:%S", localtime(os.stat(self.fpFile).st_mtime))))
        self.logger.debug("directory was modified at        {}".
                          format(strftime("%Y-%m-%d %H:%M:%S", localtime(os.stat(self.path).st_mtime))))

        return os.stat(self.fpFile).st_mtime < os.stat(self.path).st_mtime

    def fingerPrint(self, force=False):
        # figure out if the finger print file exists
        if not os.path.isfile(self.fpFile):
            raise Exception("this mode is not supported yet")
            force = True

        if force:
            raise Exception("This mode is not supported yet")

        if not force and not self.dirHasChanged():
            # there is nothing to do here
            self.logger.debug("no changes to {}".format(self.path))
            return
