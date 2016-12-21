#!/usr/bin/python

from enum import IntEnum
import sys
import datetime
from time import gmtime, strftime
from inspect import currentframe, getframeinfo
import ntpath

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
    logLevel = Level.Debug

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
    #  @param logPrefix - A prefix string that will be added to all log message in Stdout mode
    def __init__(self, logFilePath, logPrefix=None):
        self.logFile = logFilePath
        self.logPrefix = logPrefix
        self.logFh = None

    ## Destructor
    def __del__(self):
        if False == Logger.logToStdOut and None != self.logFh:
            close(self.logFh)

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

    # helper functions
    def __getLogFh(self):
        if None == self.logFh:
            if True == Logger.toStdOut:
                self.logFh = sys.stdout
            else:
                self.logFh = open(self.logFile, "a")

        return self.logFh

    def __logMsg(self, msg, level):
        # capture caller info
        frameinfo = getframeinfo(currentframe().f_back.f_back)

        if level < Logger.logLevel:
            return

        if None != self.logPrefix:
            self.__getLogFh().write(self.logPrefix + " -- ")

        self.__getLogFh().write("{} - [{}] - [{}:{}] {}\n".
                                format(datetime.datetime.now(),
                                       Logger.Level.toStr(level),
                                       ntpath.basename(frameinfo.filename),
                                       frameinfo.lineno, msg))

