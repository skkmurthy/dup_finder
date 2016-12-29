#!/usr/bin/python

from enum import IntEnum
import sys
import datetime
from time import gmtime, strftime, localtime
from inspect import currentframe, getframeinfo
import ntpath
import os
import errno
import pylru

# allowed maximum number of open log file handles
MAX_OPEN_LOG_FILES = 20

## Logging infrastructure
#  - Two modes:
#    - File mode: This is the default mode.
#    - Stdout mode: Logger provides a static function to globally redirect all logs to stdout.
#          In this mode, each log message is prefixed with the log prefix.
#  - 4 logging levels -- debug, info, warning and error -- with corresponding logging functions are
#    available.
#  - Log message format:<br/>
#    File mode:   <Time> - [<Log Level>] - [<File>:<Line>] <message><br/>
#    Stdout mode: <Log prefix> -- <Time> - [<Log Level>] - [<File>:<Line>] <message><br/>
class Logger:
    def __lruEvictionCallback(path, fh):
        fh.close()

    # an lru cache of log file handles
    __logFhByPath = pylru.lrucache(MAX_OPEN_LOG_FILES, __lruEvictionCallback)

    @staticmethod
    def __getLogFh(path):
        if Logger.toStdOut:
            return sys.stdout

        if path in Logger.__logFhByPath:
            return Logger.__logFhByPath[path]
        else:
            logFh = open(path, "a", 0)
            Logger.__logFhByPath[path] = logFh
            # update symlink
            logDir = os.path.dirname(os.path.abspath(path))
            latest = os.path.join(logDir, "latest")
            try:
                os.symlink(path, latest)
            except OSError, e:
                if e.errno == errno.EEXIST:
                    os.remove(latest)
                    os.symlink(path, latest)

            return logFh

    @staticmethod
    def __closeLogFh(path):
        if not Logger.toStdOut and path in Logger.__logFhByPath:
            Logger.__logFhByPath[path].close()
            del Logger.__logFhByPath[path]

    ## Logging levels
    class Level(IntEnum):
        Debug = 1
        Info = 2
        Warn = 3
        Error = 4

        ## A helper function to give a pretty version of logging level
        @staticmethod
        def toStr(level):
            return {
                Logger.Level.Debug : "DEBUG",
                Logger.Level.Info : "INFO",
                Logger.Level.Warn : "WARN",
                Logger.Level.Error : "ERROR",
                }.get(level)

    ## Global override to direct all logs to stdout
    toStdOut = False

    ## Loggig level
    logLevel = Level.Info

    ## A global override method, if called, will redirect all logs to stdout
    @staticmethod
    def logToStdOut():
        Logger.toStdOut = True

    ## A function to change logging level
    @staticmethod
    def setLogLevel(level):
        Logger.logLevel = level

    ## A helper function to create a filename that is the timestamp
    @staticmethod
    def newLogFileName():
        return strftime("%Y%m%d_%H%M%S", gmtime())

    ## Constructor
    #  @param logFilePath - fully qualified path to the log file
    #  @param logPrefix - A prefix string that will be added to all log message
    #                    in Stdout mode
    def __init__(self, logFilePath, logPrefix=None):
        self.logFile = os.path.abspath(logFilePath)
        self.logPrefix = logPrefix

    ## Destructor
    def __del__(self):
        Logger.__closeLogFh(self.logFile)

    ## Log debug message
    #  @param msg - Log message
    def debug(self, msg):
        self.__logMsg(msg, Logger.Level.Debug)

    ## Log informational message
    #  @param msg - Log message
    def info(self, msg):
        self.__logMsg(msg, Logger.Level.Info)

    ## Log warning message
    #  @param msg - Log message
    def warn(self, msg):
        self.__logMsg(msg, Logger.Level.Warn)

    ## Log error message
    #  @param msg - Log message
    def error(self, msg):
        self.__logMsg(msg, Logger.Level.Error)

        return self.logFh

    def __logMsg(self, msg, level):
        if level < Logger.logLevel:
            return

        # capture caller info
        frameinfo = getframeinfo(currentframe().f_back.f_back)

        fh = Logger.__getLogFh(self.logFile)
        if None != self.logPrefix and Logger.toStdOut:
            fh.write(self.logPrefix + " -- ")

        fh.write("{} - [{}] - [{}:{}] {}\n".
                 format(strftime("%Y-%m-%d %H:%M:%S", localtime()),
                        Logger.Level.toStr(level),
                        ntpath.basename(frameinfo.filename),
                        frameinfo.lineno, msg))

