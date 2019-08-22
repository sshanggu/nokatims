#!/usr/bin/python

##################################################################################################
###
### Created by: Allan Phoenix
###
### Last Update: 2017-12-13
###
### Description:
###
### Stats functions:
###
###
### Version control: 
### 
### v1: 
###        - Creation.

import sys
import time

def get_stats_rate (snap_1, snap_2, time):

    delta = int(snap_2) - int(snap_1)
    rate  = delta / time

    return rate

def check_rate(measured, expected, duration=0):

    result = 'PASS'

    windows   = duration / 10

    if expected == 0:
        wiggle = 100
    else:
        wiggle = expected / windows

    max_expected = expected + wiggle
    min_expected = expected - wiggle

    #print "MEASURED = ", measured
    #print "DEGUG: "
    #print "DEGUG: Expected rate = %s" %(expected)
    #print "DEGUG: Over %s seconds = " %(duration)
    #print "DEGUG: Or %s SR stat windows = " %(windows)
    #print "DEGUG: "
    #print "DEGUG: An extra poll means a rate of ", maxExpected
    #print "DEGUG: A missed poll means a rate of ", minExpected

    if measured >= min_expected and measured <= max_expected:
        result = 'PASS'
    else:
        result = 'FAIL'

    return result
