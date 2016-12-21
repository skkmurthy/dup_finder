#!/usr/bin/python

from Directory import *
from Logger import *

Logger.logToStdOut()
Logger.setLogLevel(Logger.Level.Debug)

#dir = Directory("/Users/sathyam/python/dup_finder")
dir = Directory("test")
dir.fingerPrint()
