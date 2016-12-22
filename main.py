#!/usr/bin/python

import sys, getopt

from Directory import *
from Logger import *
import pprint

#Logger.logToStdOut()
#Logger.setLogLevel(Logger.Level.Debug)

#dir = Directory("test")
#dir.fingerPrint()
#print "-------------"
#print dir.fingerPrintNeeded()
def printUsage():
    print "main.py [-v -n --no-log] <dir>"

def main(argv):
    dryRun = False
    try:
        opts, args = getopt.getopt(argv,"vn",["no-log"])
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-v':
            print "verbose logging enabled"
            Logger.setLogLevel(Logger.Level.Debug)
        elif opt == '-n':
            print "dry run mode only. no files will be fingerprinted"
            Logger.setLogLevel(Logger.Level.Debug)
            dryRun = True
        elif opt == '--no-log':
            print "logging to stdout only"
            Logger.logToStdOut()
        else:
            printUsage()
            sys.exit(2)

    if len(args) != 1:
        print "you need to specify and only one directory"
        printUsage()
        sys.exit(2)

    if not os.path.isdir(args[0]):
        raise Exception("Directory '" + args[0] + "' does not exist or is not a directory")

    dir = Directory(args[0])
    dir.fingerPrint(dryRun)

if __name__ == "__main__":
    main(sys.argv[1:])
