#!/usr/bin/python

from Logger import Logger
from Directory import Directory
import os
import ntpath

class Comparator:
    class DupInfo:
        def __init__(self, file, fp, origFp):
            self.file = file
            self.fp = fp
            self.origFp = origFp

    def __init__(self, refDir, candidateDir):
        self.refDir = Directory(refDir, True)
        self.candidateDir = Directory(candidateDir, True)

        self.logFile = os.path.join(candidateDir, ".dp", Logger.newLogFileName() + "_compare")
        self.logger = Logger(self.logFile, ntpath.basename(candidateDir) + "_compare")

    def compare(self):
        dups = dict()
        # make a list of dups
        for f in self.candidateDir.getFileList():
            self.logger.info("checking for {} in {}...".format(f, self.refDir.path))
            fp = self.candidateDir.getFpForFile(f)
            orig = self.refDir.checkFile(fp)
            if None != orig:
                dups[f] = Comparator.DupInfo(f, fp, orig)

        if not dups:
            self.logger.info("no dups found")
        else:
            self.logger.info("list of dups:")
            for f, info in dups.iteritems():
                self.logger.info("{} is a dup of {}".format(info.fp.path, info.origFp.path))

