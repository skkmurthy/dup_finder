#!/usr/bin/python

from Directory import *
from Logger import *

Logger.logToStdOut()
Logger.setLogLevel(Logger.Level.Info)

dir = Directory("/Users/sathyam/python/dup_finder")
dir.fingerPrint()
