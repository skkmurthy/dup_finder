#!/usr/bin/python

from Directory import *
from Logger import *
import pprint

Logger.logToStdOut()
Logger.setLogLevel(Logger.Level.Debug)

dir = Directory("test")
dir.fingerPrint()
print "-------------"
print dir.fingerPrintNeeded()


