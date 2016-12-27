#!/usr/bin/python

import sys, getopt

from Directory import *
from Logger import Logger
import pprint

def printUsage():
    print "Modes: "
    print "fingerprint:         main.py --mode=fingerprint [-v -n --no-log] <dir>"
    print "remove dups:         main.py --mode=remove-dups [-v -n --no-log] <dir> <refDir>"
    print "check internal dups: main.py --mode=check-int-dups [-v -n --no-log] <dir>"
    print "copy unique files:   main.py --mode=copy-uniq-files [-v --no-log] <dir> <refDir> <dst>"

def main(argv):
    dryRun = False
    mode = None
    try:
        opts, args = getopt.getopt(argv,"vn",["no-log","mode="])
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
        elif opt == "--mode":
            mode = arg
        else:
            printUsage()
            sys.exit(2)


    # enable debug logging till we have some confidence in the implementation
    Logger.setLogLevel(Logger.Level.Debug)

    if 'fingerprint' == mode or 'check-int-dups' == mode:
        if len(args) != 1:
            print "specify directory to fingerprint"
            printUsage()
            sys.exit(2)

        if not os.path.isdir(args[0]):
            print "Directory '" + args[0] + "' does not exist or is not a directory"
            printUsage()
            sys.exit(2)

        dir = Directory(args[0])
        if 'fingerprint' == mode:
            dir.fingerPrint(dryRun)
        else:
            dir.checkForInternalDups()

    elif mode == 'remove-dups':
        if len(args) != 2:
            print "specify candidate and reference directories"
            printUsage()
            sys.exit(2)

        if not os.path.isdir(args[0]) or not os.path.isdir(args[1]):
            print "Eiter of {} and {} is not a directory or is not accessible".format(args[0], args[1])
            printUsage()
            sys.exit(2)

        cDir = Directory(args[0])
        refDir = Directory(args[1], True)
        cDir.removeDups(refDir, dryRun)

    elif mode == 'copy-uniq-files':
        if dryRun:
            raise Exception("dry run is not supported in this mode")

        if len(args) != 3:
            print "specify candidate, reference and destination directories"
            printUsage()
            sys.exit(2)

        cDir = Directory(os.path.abspath(args[0]))
        refDir = Directory(os.path.abspath(args[1]))
        if not os.path.isdir(os.path.abspath(args[2])):
            raise Exception("destination directory does not exist")

        dPath = os.path.join(os.path.join(os.path.abspath(args[2]), cDir.dirName))
        if not os.path.isdir(dPath):
            os.makedirs(dPath)

        dst = Directory(dPath)
        cDir.copyUniques(refDir, dst)

    else:
        print "invalid mode"
        printUsage()
        sys.exit(2)

if __name__ == "__main__":
    main(sys.argv[1:])
