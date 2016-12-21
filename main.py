#!/usr/bin/python

from Directory import *
from Logger import *

Logger.logToStdOut()

dir = Directory("test")
dir.fingerPrint()
