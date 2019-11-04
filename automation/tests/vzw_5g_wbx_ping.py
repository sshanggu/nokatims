#!/usr/bin/python
from __future__ import division
import node
import service
import stats
import utils
import web
import ixia 
import sys
import getopt
import yaml
import pdb
import time
import attrdict 
#from datetime import datetime
from easysnmp import Session
from textwrap import dedent

import matplotlib.pyplot as plt
from StringIO import StringIO
import datetime as dt
import time

# Create a log file
log_file=utils.get_logger(__name__)

testbed_data=attrdict.AttrDict()

def testbed_init(testbed_file):

    log_file.info('Initalize Testbed')
    global testbed_data
    if testbed_data:
        log_file.info('Testbed already initialized')
        return

    # Read in the testbed yaml file into yaml_data dictionary
    with open(testbed_file, 'r') as f: 
        yaml_data=yaml.load(f)

    testbed_data.name = yaml_data['topology']['name']

    # Read through the yaml_data dictionary and build CPM and port objects
    # Create a dictionary of testbed node/CPM objects to speed up node/port checking
    # later on 
    
    log_file.info('Build Nodes, IOMs, MDAs, Ports and Services ...')
    for tb_node in yaml_data['nodes'].keys() :
        cpm_obj=node.Node(**yaml_data['nodes'][tb_node])
        testbed_data[tb_node] = cpm_obj


def main(testcase_name='',testsuite_name='vzw_5g_wbx_ping',csv='false',testbed_file='vzw_5g_wbx_ping.yaml'):

    test_result         = 'PASS'
    test_path           = '/automation/python/tests/'
    testbed_file        = test_path+testbed_file
    loop                = 1
    max_loops           = 10
    num_pings           = 1000
    total_pings         = 0
    test_result_list    = [] 
    test_result_dict    = {} 

    wbx_89_x_use = [] 
    wbx_89_y_use = [] 

    # Initialize the testbed
    testbed_init(testbed_file)

    # Create a dict from testbed_data of ONLY testbed_nodes
    # i.e. strip out ixia, etc.
    testbed_nodes = {}
    for key, value in testbed_data.iteritems():
       if isinstance(value, node.Node): 
           testbed_nodes[key] = value 


    # Give the nodes user friendly names 
    wbx_89 = testbed_data['wbx_89']

    # Define tests
    testplan = {}
    testplan['ping_1'] = {'action' : 'ping_1'}

    # Compare passed in testname to full list of possible testca 
    if testcase_name not in testplan:
        print "\nERROR: Unsupported test case of %s"%(testcase_name)
        print "ERROR: run with -h to get list of supported test cases"
        sys.exit()

    if testplan[testcase_name]['action'] == 'ping_1':

        log_file.info("----------------------------------")
        log_file.info("Ping IPv6 MGT address of both WBXs")
        log_file.info("1000 pings per loop")
        log_file.info("2000 byte packet size")
        log_file.info("200ms interval" )
        log_file.info("----------------------------------")

        i_wbx_89_tot = wbx_89.get_mem_current_total()
        i_wbx_89_use = wbx_89.get_mem_total_in_use()
        i_wbx_89_avl = wbx_89.get_mem_available()

        log_file.info("")
        log_file.info("")
        log_file.info("Initial : WBX Pools" )
        log_file.info("")
        log_file.info("---------")
        log_file.info("WBX 89: Total ......... %s " %(i_wbx_89_tot))
        log_file.info("WBX 89: In Use ........ %s " %(i_wbx_89_use))
        log_file.info("WBX 89: Available ..... %s " %(i_wbx_89_avl))
        log_file.info("---------")
        log_file.info("")

        day_num = dt.datetime.now().day
        hour_num = dt.datetime.now().hour
        min_num = dt.datetime.now().minute
        print hour_num
        while hour_num != 13:
            log_file.info("## Ping WBX IPv6 MGT")
            log_file.info("## ")
            wbx_89.ping6(count=num_pings,size=2000,gap=0.2)
            total_pings = total_pings + num_pings

            wbx_89_tot = wbx_89.get_mem_current_total()
            wbx_89_use = wbx_89.get_mem_total_in_use()
            wbx_89_avl = wbx_89.get_mem_available()

            d_wbx_89_tot = int(i_wbx_89_tot) - int(wbx_89_tot)
            d_wbx_89_use = int(wbx_89_use) - int(i_wbx_89_use)
            d_wbx_89_avl = int(i_wbx_89_avl) - int(wbx_89_avl)

            wbx_89_x_use.append(total_pings) 
            wbx_89_y_use.append(wbx_89_use)

            log_file.info("")
            log_file.info("")
            log_file.info("Loop %s : WBX Pools" %(loop))
            log_file.info("")
            log_file.info("---------")
            log_file.info("WBX 89: Total ......... %s " %(wbx_89_tot))
            log_file.info("WBX 89: In Use ........ %s " %(wbx_89_use))
            log_file.info("WBX 89: Available ..... %s " %(wbx_89_avl))
            log_file.info("")
            log_file.info("WBX 89: In Use Delta .. %s" %(d_wbx_89_use))
            log_file.info("---------")
            log_file.info("")
            wbx_89.cliexe('/show system memory-pools')

            loop += 1
            min_num = dt.datetime.now().minute
            day_num = dt.datetime.now().day
            hour_num = dt.datetime.now().hour
            print "day = %s" %(day_num)
            print "hour = %s" %(hour_num)


        log_file.info("Total Pings = %s" %(total_pings))
        log_file.info("")

        plt.suptitle('WBX 89 In Use Pools', fontsize=14, fontweight='bold')
        plt.plot(wbx_89_x_use,wbx_89_y_use)
        img = StringIO()
        plt.savefig('wbx_89.png')
         
        test_result_list.append(test_result)
        test_result_list.append(test_result_dict)

    return test_result_list



if (__name__ == '__main__'):


    main()
