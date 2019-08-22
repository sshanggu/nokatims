#!/usr/bin/env python

###################################
##
# Example test
##
##
# Allan update
##
# 11/1/18 - Git check in test

import os
import node
import time
import service
import stats
import utils
import web
import ixia
import sys
import getopt
import random
import yaml
import logging
from datetime import datetime
from easysnmp import Session
from textwrap import dedent
from collections import OrderedDict

mylog = logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler())


def main(testcase_name='',
         traffic_item='IPV6_Hub5',
         cvs_stats='false',
         testbed_file='tb1.yaml',
         testsuite_name='example'):

    mylog.info("testcase= %s" % testcase_name)
    mylog.info("traffic_item= %s" % traffic_item)
    mylog.info("cvs_stats= %s" % cvs_stats)
    mylog.info("testbed_file= %s" % testbed_file)
    mylog.info("testsuite_name= %s" % testsuite_name)

    test_result = ['PASS']

    # read in testbed data file
    with open(os.path.join(os.path.dirname(__file__), testbed_file), 'r') as f:
        tbdata = yaml.load(f)

    # IP ADDRESS OF LAB IXIA CHASSIS
    ixia_chassis = tbdata['ixia_chassis']

    # IP ADDRESS OF LAB IXIA PC
    ixia_pc = tbdata['ixia_pc']
    node_1_ip = tbdata['node_1']['mgmt_ip']
    node_1_i1 = tbdata['node_1']['iom']
    node_1_m1 = tbdata['node_1']['mda']
    node_1_p1 = tbdata['node_1']['port_1']['id']
    saps = tbdata['node_1']['saps']
    sap_1 = node_1_ip+':'+saps[0]+':'+node_1_p1+':'+saps[0]
    sap_2 = node_1_ip+':'+saps[1]+':'+node_1_p1+':'+saps[1]

    # import pdb; pdb.set_trace()
    tc = testcase_name
    kpidict = OrderedDict()
    kpidict['KPIs'] = list()
    lkeys = ['stream1', 'streamA', 'stream2', 'stream3', 'streamB', 'tmpX12']
    if tc == 'test-1':
        mylog.info("run test-111111 logic ......")

        kpi = '.'.join([tc, 'tx'])  # 1st kpi
        kpidict['KPIs'].append(kpi)
        ltx = [random.random() for i in range(len(lkeys))]
        for k, v in zip(lkeys, ltx):
            kpidict['.'.join([kpi, k])] = v

        kpi = '.'.join([tc, 'rx'])  # 2nd kpi
        kpidict['KPIs'].append(kpi)
        lrx = [random.random() for i in range(len(lkeys))]
        for k, v in zip(lkeys, lrx):
            kpidict['.'.join([kpi, k])] = v

        test_result.append(kpidict)

    elif tc == 'test-2':
        mylog.info("run test-222222 logic ......")
        # mylog.info("wait for 80 seconds ......")
        # time.sleep(80)

        kpi = '.'.join([tc, 'rx'])  # 1st kpi
        kpidict['KPIs'].append(kpi)
        lrx = [random.random() for i in range(len(lkeys))]
        for k, v in zip(lkeys, lrx):
            kpidict['.'.join([kpi, k])] = v

        kpi = '.'.join([tc, 'loss'])  # 2nd kpi
        kpidict['KPIs'].append(kpi)
        lloss = [random.random() for i in range(len(lkeys))]
        for k, v in zip(lkeys, lloss):
            kpidict['.'.join([kpi, k])] = v

        test_result.append(kpidict)

    elif tc == 'test-3':
        mylog.info("run test-333333 logic ......")
        test_result.append(kpi)
    else:
        mylog.info("run test-444444 logic ......")
        test_result = ['FAIL']
        test_result.append('TX: 9,868,687, RX: 9,868,632')

    return test_result


if (__name__ == '__main__'):

    # Get all user input command options
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "t:i:c:h")
    except getopt.GetoptError as err:
        print("\nERROR: %s" % (err))
        sys.exit(0)

    testprm = dict()
    # Parse input options and validate format
    for opt, val in optlist:
        if opt == "-t":
            # test_case
            testprm['test_case'] = val
        elif opt == "-i":
            # ixia traffic stream
            testprm['traffic_item'] = val
        elif opt == "-h":
            # Help output
            usage()
            sys.exit()
        elif opt == "-c":
            # enable csv stat logging
            testprm['csv_stats'] = val
        else:
            print("option: %s a is not implemented yet!!" % (opt, val))
            sys.exit()

    main(**testprm)
