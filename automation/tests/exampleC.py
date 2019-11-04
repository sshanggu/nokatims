#!/usr/bin/env python3
##############################################################################
#
# ExampleC test suite
#   Tests return KPI dictionary for regression to diagram
#
#
#
#
# 2019/10/30 -- sshanggu rewrote
#
##############################################################################

import os
import time
import utils
import ixia
import sys
import getopt
import random
import node as nodelib
from datetime import datetime
from easysnmp import Session
from textwrap import dedent
from collections import OrderedDict

mylog = utils.get_logger(__name__)
tb = None


def kpi_demo_1(tc_name):
    result = ['PASS']  # result is a list

    kpidict = OrderedDict()
    kpidict['KPIs'] = list()  # init as empty list

    # kpi_name should be 'tc_name.kpi_name'. in this case
    # tc_name='kpi_demo_1' and kpi_name are 'tx' & 'rx'
    kpi1 = '.'.join([tc_name, 'tx'])  # kpi1 = 'kpi_demo_1.tx'
    kpi2 = '.'.join([tc_name, 'rx'])  # kpi2 = 'kpi_demo_2.rx'

    kpidict['KPIs'].append(kpi1)
    kpidict['KPIs'].append(kpi2)
    # now we have two kpi_names in kpidict
    # kpidict['KPIs']=['kpi_demo_1.tx', 'kpi_demo_1.rx']

    # each kpi_name may have multiple actual ixia data streams
    # here we set up examle stream names and random data
    lstrms = ['streamA', 'streamB', 'streamC', 'streamD', 'streamE']
    lrands = [random.random() for i in range(len(lstrms))]
    for k, v in zip(lstrms, lrands):
        kpidict['.'.join([kpi1, k])] = v
        kpidict['.'.join([kpi2, k])] = v

    # now kpidict looks like:
    # kpidict['KPIs']=['kpi_demo_1.tx', 'kpi_demo_1.rx']
    # kpidict['kpi_demo_1.tx.streamA']=0.1765527465253881
    # kpidict['kpi_demo_1.rx.streamA']=0.1765527465253881
    # kpidict['kpi_demo_1.tx.streamB']=0.7410514463087737
    # kpidict['kpi_demo_1.rx.streamB']=0.7410514463087737
    # kpidict['kpi_demo_1.tx.streamC']=0.7467162353471369
    # kpidict['kpi_demo_1.rx.streamC']=0.7467162353471369
    # kpidict['kpi_demo_1.tx.streamD']=0.5611944638798385
    # kpidict['kpi_demo_1.rx.streamD']=0.5611944638798385
    # kpidict['kpi_demo_1.tx.streamE']=0.1742471165521735
    # kpidict['kpi_demo_1.rx.streamE']=0.1742471165521735

    # log kpidict
    utils.framelog('kpidict in this run')
    for k in kpidict:
        mylog.info('kpidict[%s]=%s' % (k, kpidict[k]))

    result.append(kpidict)
    # result = ['PASS', kpidict]

    return result


def main(testcase_name='kpi_demo_1',
         testbed_file='tb1.yaml',
         testsuite_name='exampleC'):

    global tb
    if not tb:
        tb = nodelib.Testbed(testbed_file)

    return globals()[testcase_name](testcase_name)
