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
import logging
import attrdict 

from datetime import datetime
from easysnmp import Session
from textwrap import dedent
from collections import OrderedDict  

# Create a log file
log_file=logging.getLogger(__name__)

# Configure log file to output to stdout too
log_file.addHandler(logging.StreamHandler(sys.stdout))

testbed_data=attrdict.AttrDict()


def testbed_init(testbed_file):

    log_file.info('')
    log_file.info('')
    log_file.info('')
    log_file.info('')
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
    
    # Create ixia object
    log_file.info('Build Ixia')
    testbed_data.ixia_100g    = ixia.IxNetx(**yaml_data['ixia'])

    log_file.info('Build Nodes, IOMs, MDAs, Ports & Services')
    for tb_node in yaml_data['nodes'].keys() :
        cpm_obj=node.Node(**yaml_data['nodes'][tb_node])
        testbed_data[tb_node] = cpm_obj



def main(testcase_name='',testsuite_name='vzw_5g_ring_dev',csv='false',testbed_file='vzw_5g_100g.yaml'):

    set_up_result       = True 
    phase_1_result      = 'PASS'
    phase_2_result      = 'PASS'
    phase_3_result      = 'PASS'
    phase_4_result      = 'PASS'
    test_result         = 'PASS'
    test_path           = '/automation/python/tests/'
    testbed_file        = test_path+testbed_file
    standby_wait        = 240
    port_wait           = 120
    dd_ep               = True
    drill_down_names    = []
    test_result_list    = [] 
    test_result_dict    = {} 

    # Initialize the testbed
    testbed_init(testbed_file)

    # Create a dict from testbed_data of ONLY testbed_nodes
    # i.e. strip out ixia, etc.
    testbed_nodes = {}
    for key, value in testbed_data.iteritems():
       if isinstance(value, node.Node): 
           testbed_nodes[key] = value 

    start_time = datetime.now()

    # Give the nodes user friendly names 
    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    ring_1 = testbed_data['hub_1']
    ring_2 = testbed_data['hub_2']
    ring_3 = testbed_data['hub_3']
    ring_4 = testbed_data['hub_4']
    ring_5 = testbed_data['hub_5']
    ring_6 = testbed_data['hub_6']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    ixia_100g = testbed_data.ixia_100g

    testplan = {}

    # Dictionary of expected loss in ms per IPv6 traffic class
    tc_dict  = {}
    tc_dict_no_drop      = {'0':0,    '32':0,    '64':0,    '96':0,    '128':0,    '184':0,    '224':0} 
    tc_dict_be_drop      = {'0':200,  '32':0,    '64':0,    '96':0,    '128':0,    '184':0,    '224':0} 
    tc_dict_be_lbe_drop  = {'0':200,  '32':200,  '64':0,    '96':0,    '128':0,    '184':0,    '224':0} 
    tc_dict_all_drop     = {'0':1800, '32':1800, '64':1800, '96':1800, '128':1800, '184':1800, '224':1800} 
    tc_dict_drop_x       = {'0':35,   '32':1,    '64':1,    '96':1,    '128':1,    '184':1,    '224':1} 

    # Tests to set up suite topology
    testplan['ring_set_up']        = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'RING' }
    testplan['hub_offload_set_up'] = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'CRAN_OFF'}

    # Teardown 
    testplan['teardown']                  = {'ixia_pat' : 'na', 'action' : 'suite_teardown', 'topology' : 'CRAN_NO_OFF'}

    # CRAN Ring
    testplan['ring_sanity']                    = {'ixia_pat' : 'ar-', 'action' : 'sanity', 'topology' : 'RING' , 'tc_dict':tc_dict_no_drop }

    testplan['ring_reboot_mls_1_standby_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'reboot_mls_1_standby_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_mls_2_standby_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'reboot_mls_2_standby_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_ring_1_standby_cpm'] = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_1_standby_cpm',     'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_ring_2_standby_cpm'] = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_2_standby_cpm',     'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_ring_3_standby_cpm'] = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_3_standby_cpm',     'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_ring_4_standby_cpm'] = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_4_standby_cpm',     'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_ring_5_standby_cpm'] = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_5_standby_cpm',     'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_reboot_ring_6_standby_cpm'] = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_6_standby_cpm',     'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}

    testplan['ring_switch_mls_1_active_cpm']   = {'ixia_pat' : 'ar-', 'action' : 'switch_mls_1_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_mls_2_active_cpm']   = {'ixia_pat' : 'ar-', 'action' : 'switch_mls_2_active_cpm',       'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_ring_1_active_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'switch_ring_1_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_ring_2_active_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'switch_ring_2_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_ring_3_active_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'switch_ring_3_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_ring_4_active_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'switch_ring_4_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_ring_5_active_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'switch_ring_5_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}
    testplan['ring_switch_ring_6_active_cpm']  = {'ixia_pat' : 'ar-', 'action' : 'switch_ring_6_active_cpm',      'topology' : 'RING' , 'tc_dict':tc_dict_no_drop}

    testplan['ring_fail_ring_1_to_mls_1_lag']  = {'ixia_pat' : 'ar-', 'action' : 'fail_ring_1_to_mls_1_lag',      'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_ring_2_to_ring_1_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_ring_2_to_ring_1_lag',     'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_ring_3_to_ring_2_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_ring_3_to_ring_2_lag',     'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_ring_4_to_ring_3_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_ring_4_to_ring_3_lag',     'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_ring_5_to_ring_4_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_ring_5_to_ring_4_lag',     'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_ring_6_to_ring_5_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_ring_6_to_ring_5_lag',     'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_ring_6_to_mls_2_lag'] = {'ixia_pat' : 'ar-', 'action'  : 'fail_ring_6_to_mls_2_lag', 'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}

    testplan['ring_fail_1_member_ring_1_to_mls_1_lag']  = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_1_to_mls_1_lag',  'topology' : 'RING' , 'tc_dict':tc_dict_be_lbe_drop}
    testplan['ring_fail_1_member_ring_2_to_ring_1_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_2_to_ring_1_lag', 'topology' : 'RING' , 'tc_dict':tc_dict_be_lbe_drop}
    testplan['ring_fail_1_member_ring_3_to_ring_2_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_3_to_ring_2_lag', 'topology' : 'RING' , 'tc_dict':tc_dict_be_lbe_drop}
    testplan['ring_fail_1_member_ring_4_to_ring_3_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_4_to_ring_3_lag', 'topology' : 'RING' , 'tc_dict':tc_dict_be_lbe_drop}
    testplan['ring_fail_1_member_ring_5_to_ring_4_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_5_to_ring_4_lag', 'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_fail_1_member_ring_6_to_ring_5_lag'] = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_6_to_ring_5_lag', 'topology' : 'RING' , 'tc_dict':tc_dict_be_lbe_drop}
    testplan['ring_fail_1_member_ring_6_to_mls_2_lag']  = {'ixia_pat' : 'ar-', 'action' : 'fail_1_member_ring_6_to_mls_2_lag',  'topology' : 'RING' , 'tc_dict':tc_dict_be_lbe_drop}

    testplan['ring_reboot_ring_1']  = {'ixia_pat' : 'ar-', 'action' : 'reboot_ring_1',  'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}

    testplan['ring_isolate_ring_1']  = {'ixia_pat' : 'ar-', 'action' : 'isolate_ring_1',  'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}
    testplan['ring_isolate_ring_2']  = {'ixia_pat' : 'ar-', 'action' : 'isolate_ring_2',  'topology' : 'RING' , 'tc_dict':tc_dict_all_drop}

    # Compare passed in testname to full list of possible testcases 
    if testcase_name not in testplan:
        print "\nERROR: Unsupported test case of %s"%(testcase_name)
        print "ERROR: run with -h to get list of supported test cases"
        sys.exit()

    # Read in testplan for specific testcase
    ixia_pattern = testplan[testcase_name]['ixia_pat']
    action       = testplan[testcase_name]['action']
    #threshold    = testplan[testcase_name]['threshold']

    if 'topology' not in testplan[testcase_name]:  
        print "No topology specified in testplan.  Assume CRAN via offload"
        topology = 'CRAN_OFF' 
    else:
        topology = testplan[testcase_name]['topology']
        print "Testbed topology specified in testplan to be %s" %(topology)

    if 'tc_dict' not in testplan[testcase_name]:
        tc_dict = tc_dict_no_drop 
    else:
        tc_dict = testplan[testcase_name]['tc_dict']

    log_file.info('Check all nodes for hw errors')
    for error_node in testbed_nodes.values():
        error_node.check_for_hw_errors()
            
    mls_1_chassis_type       = mls_1.get_chassis_type()
    mls_1_cpm_active_sw_ver  = mls_1.get_active_cpm_sw_version()

    mls_2_chassis_type       = mls_2.get_chassis_type()
    mls_2_cpm_active_sw_ver  = mls_2.get_active_cpm_sw_version()

    off_1_chassis_type       = off_1.get_chassis_type()
    off_1_cpm_active_sw_ver  = off_1.get_active_cpm_sw_version()

    off_2_chassis_type       = off_1.get_chassis_type()
    off_2_cpm_active_sw_ver  = off_1.get_active_cpm_sw_version()

    ring_1_chassis_type       = ring_1.get_chassis_type()
    ring_1_cpm_active_sw_ver  = ring_1.get_active_cpm_sw_version()

    ring_2_chassis_type       = ring_2.get_chassis_type()
    ring_2_cpm_active_sw_ver  = ring_2.get_active_cpm_sw_version()

    ring_3_chassis_type       = ring_3.get_chassis_type()
    ring_3_cpm_active_sw_ver  = ring_3.get_active_cpm_sw_version()

    ring_4_chassis_type       = ring_4.get_chassis_type()
    ring_4_cpm_active_sw_ver  = ring_4.get_active_cpm_sw_version()

    ring_5_chassis_type       = ring_5.get_chassis_type()
    ring_5_cpm_active_sw_ver  = ring_5.get_active_cpm_sw_version()

    ring_6_chassis_type       = ring_6.get_chassis_type()
    ring_6_cpm_active_sw_ver  = ring_6.get_active_cpm_sw_version()

    wbx_89_chassis_type       = wbx_89.get_chassis_type()
    wbx_89_cpm_active_sw_ver  = wbx_89.get_active_cpm_sw_version()

    wbx_98_chassis_type       = wbx_98.get_chassis_type()
    wbx_98_cpm_active_sw_ver  = wbx_98.get_active_cpm_sw_version()

    if action == 'suite_set_up':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Switch to %s topology" %(topology))
        log_file.info("--------------------------------------------------")
        log_file.info("")
    
        no_shutdown_all_log_98(testbed_nodes)
        #shutdown_all_log_98(testbed_nodes)
        set_mode_ring(testbed_nodes)
        if not check_mode_ring(testbed_nodes):
            set_up_result = False 

        if set_up_result:
           log_file.info('Suite set up OK')
           mod_set_up_result = 'PASS' 
        else:
           log_file.error('Suite set up FAILED')
           mod_set_up_result = 'FAIL' 

        test_result_list = [] 
        test_result_list.append(mod_set_up_result)
        test_result_dict = {} 

        return test_result_list
    
    if action == 'suite_teardown':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Suite teardown - return to %s topology" %(topology))
        log_file.info("--------------------------------------------------")
        log_file.info("")
        set_mode_hub_no_offload(mls_1, mls_2, off_1, off_2, ring_1, ring_2)
        set_all_port_ether_stats_itvl(testbed_nodes,300)
        no_shutdown_all_log_98(testbed_nodes)

        log_file.info('Save the testbed configs')
        mls_1.admin_save()
        mls_2.admin_save()
        off_1.admin_save()
        off_2.admin_save()
        ring_1.admin_save()
        ring_2.admin_save()

        test_result_list = [] 
        test_result_list.append('PASS')
        test_result_dict = {} 
        return test_result_list

    # Set the ixia pattern based on the test
    ixia_100g.set_traffic(pattern=ixia_pattern, commit=True)

    log_file.info("--------------------------------------------------")
    log_file.info("Testbed Name ...................... %s" %(testbed_data.name))
    log_file.info("Testbed Topology: ................. %s" %(topology))
    log_file.info("")
    log_file.info("Test Suite Name ................... %s" %(testsuite_name))
    log_file.info("Test Case Name .................... %s" %(testcase_name))
    log_file.info("")
    log_file.info("Test Case Details:")
    log_file.info("------------------")
    log_file.info("")
    log_file.info("Perform Action: ................... %s" %(action))
    log_file.info("")
    log_file.info("MLS 1 chassis type ................ %s" %(mls_1_chassis_type))
    log_file.info("MLS 1 Active CPM software version . %s" %(mls_1_cpm_active_sw_ver))
    log_file.info("MLS 2 chassis type ................ %s" %(mls_2_chassis_type))
    log_file.info("MLS 2 Active CPM software version . %s" %(mls_2_cpm_active_sw_ver))
    log_file.info(" ")
    log_file.info("OFF 1 chassis type ................ %s" %(off_1_chassis_type))
    log_file.info("OFF 1 Active CPM software version . %s" %(off_1_cpm_active_sw_ver))
    log_file.info("OFF 2 chassis type ................ %s" %(off_2_chassis_type))
    log_file.info("OFF 2 Active CPM software version . %s" %(off_2_cpm_active_sw_ver))
    log_file.info(" ")
    log_file.info("RING 1 chassis type ................ %s" %(ring_1_chassis_type))
    log_file.info("RING 1 Active CPM software version . %s" %(ring_1_cpm_active_sw_ver))
    log_file.info("RING 2 chassis type ................ %s" %(ring_2_chassis_type))
    log_file.info("RING 2 Active CPM software version . %s" %(ring_2_cpm_active_sw_ver))
    log_file.info(" ")
    log_file.info("RING 3 chassis type ................ %s" %(ring_3_chassis_type))
    log_file.info("RING 3 Active CPM software version . %s" %(ring_3_cpm_active_sw_ver))
    log_file.info("RING 4 chassis type ................ %s" %(ring_4_chassis_type))
    log_file.info("RING 4 Active CPM software version . %s" %(ring_4_cpm_active_sw_ver))
    log_file.info(" ")
    log_file.info("RING 5 chassis type ................ %s" %(ring_5_chassis_type))
    log_file.info("RING 5 Active CPM software version . %s" %(ring_5_cpm_active_sw_ver))
    log_file.info("RING 6 chassis type ................ %s" %(ring_6_chassis_type))
    log_file.info("RING 6 Active CPM software version . %s" %(ring_6_cpm_active_sw_ver))
    log_file.info(" ")

    log_file.info("WBX 89 chassis type ................ %s" %(wbx_89_chassis_type))
    log_file.info("WBX 89 Active CPM software version . %s" %(wbx_89_cpm_active_sw_ver))
    log_file.info("WBX 98 chassis type ................ %s" %(wbx_98_chassis_type))
    log_file.info("WBX 98 Active CPM software version . %s" %(wbx_98_cpm_active_sw_ver))
    log_file.info(" ")
    log_file.info("Take Ixia CSV Snapshot ............ %s" %(csv))
    log_file.info("")
    log_file.info("--------------------------------------------------")

    #show_topo(testbed_nodes,topology)

    edn_wait  = 10
    edn_count = 26

    if not check_edn_ready(edn_count,edn_wait):
        set_up_result = False 

    if not (wait_all_default_routes(testbed_nodes,60)):
        set_up_result = False 

    
    if set_up_result:

        log_file.info("Set up successful")
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 1: Pre failure Traffic Check") 
        log_file.info("")
        log_file.info("Start Ixia Traffic Streams ")
        log_file.info("--------------------------------------------------")
        log_file.info("")

        ixia_100g.start_traffic()
        ixia_100g.clear_stats()
        utils.countdown(30)
        show_ring(testbed_nodes)
        ixia_100g.stop_traffic()

        log_file.info("")
        log_file.info("Get stats for all traffic items")
        log_file.info("--------------------------------------------------")
        ixia_100g.set_stats()
        log_file.info("")

        for traffic_item in ixia_100g.traffic_names:
            if ixia_100g.get_stats(traffic_item,'delta') > 0:
                log_file.error("Phase 1: Traffic item %s Loss > 0" %(traffic_item))
                log_file.error("Phase 1: Traffic item %s Fail" %(traffic_item))
                log_file.error("")
                phase_1_result = 'FAIL'
            else:
                log_file.info("Phase 1: Traffic item %s Loss = 0" %(traffic_item))
                log_file.info("Phase 1: Traffic item %s Pass" %(traffic_item))
                log_file.info("")

        if phase_1_result == 'FAIL':
            log_file.error("")
            log_file.error("--------------------------------------------------")
            log_file.error("Phase 1: Fail") 
            log_file.error("--------------------------------------------------")
        else:
            log_file.info("")
            log_file.info("--------------------------------------------------")
            log_file.info("Phase 1: Pass") 
            log_file.info("--------------------------------------------------")


        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 2: Test Case  ................. %s" %(testcase_name))              
        log_file.info("--------------------------------------------------")
        log_file.info("")

        ixia_100g.start_traffic()
        ixia_100g.clear_stats()
        utils.countdown(10)

        if action == 'reboot_mls_1_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info(" ** Reboot Standby CPM on MLS 1")
            log_file.info("-------------------------------")
            if mls_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 1")
                phase_2_result == 'FAIL'


        elif action == 'reboot_mls_2_standby_cpm':
            log_file.info("------------------------------")
            log_file.info("** Reboot Standby CPM on MLS 2")
            log_file.info("------------------------------")
            if mls_2.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 2")
                phase_2_result == 'FAIL'


        elif action == 'reboot_ring_1_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Reboot Standby CPM on RING 1")
            log_file.info("-------------------------------")
            if ring_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on RING 1")
                phase_2_result == 'FAIL'

        elif action == 'reboot_ring_2_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Reboot Standby CPM on RING 2")
            log_file.info("-------------------------------")
            if ring_2.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on RING 2")
                phase_2_result == 'FAIL'

        elif action == 'reboot_ring_3_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Reboot Standby CPM on RING 3")
            log_file.info("-------------------------------")
            if ring_3.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on RING 3")
                phase_2_result == 'FAIL'

        elif action == 'reboot_ring_4_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Reboot Standby CPM on RING 4")
            log_file.info("-------------------------------")
            if ring_4.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on RING 4")
                phase_2_result == 'FAIL'

        elif action == 'reboot_ring_5_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Reboot Standby CPM on RING 5")
            log_file.info("-------------------------------")
            if ring_5.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on RING 5")
                phase_2_result == 'FAIL'

        elif action == 'reboot_ring_6_standby_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Reboot Standby CPM on RING 6")
            log_file.info("-------------------------------")
            if ring_6.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on RING 6")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_1_active_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Switch Active CPM on RING 1")
            log_file.info("-------------------------------")
            if ring_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch Active CPM on RING 1")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_2_active_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Switch Active CPM on RING 2")
            log_file.info("-------------------------------")
            if ring_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch Active CPM on RING 2")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_3_active_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Switch Active CPM on RING 3")
            log_file.info("-------------------------------")
            if ring_3.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch Active CPM on RING 3")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_4_active_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Switch Active CPM on RING 4")
            log_file.info("-------------------------------")
            if ring_4.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch Active CPM on RING 4")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_5_active_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Switch Active CPM on RING 5")
            log_file.info("-------------------------------")
            if ring_5.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch Active CPM on RING 5")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_6_active_cpm':
            log_file.info("-------------------------------")
            log_file.info("** Switch Active CPM on RING 6")
            log_file.info("-------------------------------")
            if ring_6.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch Active CPM on RING 6")
                phase_2_result == 'FAIL'


        elif action == 'fail_ring_1_to_mls_1_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 1 to MLS 1 Lag")
            log_file.info("-------------------------------")
            ring_1.to_mls_1.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)

        elif action == 'fail_ring_2_to_ring_1_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 2 to RING 1 Lag")
            log_file.info("-------------------------------")
            ring_2.to_ring_1.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)

        elif action == 'fail_ring_3_to_ring_2_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 3 to RING 2 Lag")
            log_file.info("-------------------------------")
            ring_3.to_ring_2.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)

        elif action == 'fail_ring_4_to_ring_3_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 4 to RING 3 Lag")
            log_file.info("-------------------------------")
            ring_4.to_ring_3.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)
        elif action == 'fail_ring_5_to_ring_4_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 5 to RING 4 Lag")
            log_file.info("-------------------------------")
            ring_5.to_ring_4.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)
        elif action == 'fail_ring_6_to_ring_5_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 6 to RING 5 Lag")
            log_file.info("-------------------------------")
            ring_6.to_ring_5.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)
        elif action == 'fail_ring_6_to_mls_2_lag':
            log_file.info("-------------------------------")
            log_file.info("** Fail RING 6 to MLS 2 Lag")
            log_file.info("-------------------------------")
            ring_6.to_mls_2.set_port_info('admin','down') 
            utils.countdown(30)
            show_ring(testbed_nodes)

        elif action == 'fail_1_member_ring_1_to_mls_1_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 1 to MLS1 1 Lag")
            ring_1.to_mls_1.shutdown_one_lag_member()
            utils.countdown(10)

        elif action == 'fail_1_member_ring_2_to_ring_1_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 2 to RING 1 Lag")
            ring_2.to_ring_1.shutdown_one_lag_member()
            utils.countdown(10)

        elif action == 'fail_1_member_ring_3_to_ring_2_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 3 to RING 2 Lag")
            ring_3.to_ring_2.shutdown_one_lag_member()
            utils.countdown(10)

        elif action == 'fail_1_member_ring_4_to_ring_3_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 4 to RING 3 Lag")
            ring_4.to_ring_3.shutdown_one_lag_member()
            utils.countdown(10)

        elif action == 'fail_1_member_ring_5_to_ring_4_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 5 to RING 4 Lag")
            ring_5.to_ring_4.shutdown_one_lag_member()
            utils.countdown(10)

        elif action == 'fail_1_member_ring_6_to_ring_5_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 6 to RING 5 Lag")
            ring_6.to_ring_5.shutdown_one_lag_member()
            utils.countdown(10)

        elif action == 'fail_1_member_ring_6_to_mls_2_lag':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in RING 6 to MLS 2 Lag")
            ring_6.to_mls_2.shutdown_one_lag_member()
            utils.countdown(10)



        elif action == 'switch_mls_1_active_cpm':
            log_file.info("-----------------------------")
            log_file.info("** Switch Active CPM on MLS 1")
            log_file.info("-----------------------------")
            if mls_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 1")
                phase_2_result == 'FAIL'


        elif action == 'switch_mls_2_active_cpm':
            log_file.info("-----------------------------")
            log_file.info("** Switch Active CPM on MLS 2")
            log_file.info("-----------------------------")
            if mls_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 1")
                phase_2_result == 'FAIL'


        elif action == 'switch_ring_1_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on RING 1")
            log_file.info("------------------------------")
            if ring_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on RING 1")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_2_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on RING 2")
            log_file.info("------------------------------")
            if ring_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on RING 2")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_3_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on RING 3")
            log_file.info("------------------------------")
            if ring_3.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on RING 3")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_4_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on RING 4")
            log_file.info("------------------------------")
            if ring_4.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on RING 4")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_5_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on RING 5")
            log_file.info("------------------------------")
            if ring_5.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on RING 5")
                phase_2_result == 'FAIL'

        elif action == 'switch_ring_6_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on RING 6")
            log_file.info("------------------------------")
            if ring_6.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on RING 6")
                phase_2_result == 'FAIL'

        elif action == 'shut_one_inter_mls_port':
            log_file.info("------------------------------")
            log_file.info("** Shutdown one inter MLS port")
            log_file.info("------------------------------")
            mls_1.shutdown_one_lag_member()
            utils.countdown(10)
            ixia_100g.clear_stats()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)


        elif action == 'shut_one_inter_mls_port_reboot_mls_1_standby_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown one inter MLS port")
            mls_1.shutdown_one_lag_member()
            utils.countdown(10)
            ixia_100g.clear_stats()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

            log_file.info("** Reboot Standby CPM on MLS 1")
            log_file.info("------------------------------")
            if mls_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 1")
                phase_2_result == 'FAIL'


        elif action == 'shut_one_inter_mls_port_reboot_mls_2_standby_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown one inter MLS port")
            mls_1.shutdown_one_lag_member()
            utils.countdown(10)
            ixia_100g.clear_stats()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

            log_file.info("** Reboot Standby CPM on MLS 2")
            log_file.info("------------------------------")
            if mls_2.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 2")
                phase_2_result == 'FAIL'

        elif action == 'shut_one_inter_mls_port_switch_mls_1_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown one inter MLS port")
            mls_1.shutdown_one_lag_member()
            utils.countdown(10)
            ixia_100g.clear_stats()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

            log_file.info("** Switch Active CPM on MLS 1")
            log_file.info("-----------------------------")
            if mls_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 1")
                phase_2_result == 'FAIL'


        elif action == 'shut_one_inter_mls_port_switch_mls_2_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown one inter MLS port")
            mls_1.shutdown_one_lag_member()
            utils.countdown(10)
            ixia_100g.clear_stats()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

            log_file.info("** Switch Active CPM on MLS 2")
            log_file.info("-----------------------------")
            if mls_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 2")
                phase_2_result == 'FAIL'

        elif action == 'isolate_ring_1':
            log_file.info("------------------------------")
            log_file.info("** Isolate HUB 1")
            ring_1.to_mls_1.set_port_info('admin','down') 
            ring_1.to_ring_2.set_port_info('admin','down') 

        elif action == 'isolate_ring_2':
            log_file.info("------------------------------")
            log_file.info("** Isolate HUB 2")
            ring_2.to_ring_3.set_port_info('admin','down') 
            ring_2.to_ring_3.set_port_info('admin','down') 

        elif action == 'reboot_ring_1':
            log_file.info("------------------------------")
            log_file.info("** Reboot Ring 1")
            ring_1.sr_reboot() 
            if ring_1.wait_for_valid_standby_cpm(300) != 'OK':
               phase_2_result == 'FAIL'

        elif action == 'reboot_ring_2':
            log_file.info("------------------------------")
            log_file.info("** Reboot Ring 2")
            ring_2.sr_reboot() 

        elif action == 'reboot_node_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Reboot MLS 1")
            mls_1.sr_reboot() 

        elif action == 'reboot_node_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Reboot MLS 2")
            mls_2.sr_reboot() 

        elif action == 'reboot_node_off_1':
            log_file.info("------------------------------")
            log_file.info("** Reboot Offload 1")
            off_1.sr_reboot() 

        elif action == 'reboot_node_off_2':
            log_file.info("------------------------------")
            log_file.info("** Reboot Offload 2")
            off_2.sr_reboot() 

        elif action == 'sanity':
            log_file.info("------------------------------")
            log_file.info("** Sanity test. No fail action")
            log_file.info("------------------------------")
        else:
            log_file.info("-----------------------------")
            log_file.info("** Undefined test case action")
            log_file.info("-----------------------------")
            log_file.info("")
            log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
            ixia_100g.stop_traffic()
            return 'FAIL'

        utils.countdown(20)
        show_ring(testbed_nodes)

        log_file.info("")
        log_file.info("-------------------------------------------------------------------")
        log_file.info("Phase 3: Look at port util, stop Ixia, collect & Analyze Ixia Stats")
        log_file.info("-------------------------------------------------------------------")
        log_file.info("")

        if 'reboot_node' not in action:
            #mls_status(mls_1,mls_2)
            #wbx_status_to_offload(wbx_89,wbx_98)
            print ""

            if topology == 'CRAN_OFF':
                print ""
                #offload_status_to_hubs(off_1,off_2)
                #hub_status_with_offload(hub_1, hub_2)
            elif topology == 'CRAN_NO_OFF':
                #hub_status_no_offload(hub_1, hub_2)
                print ""
            #wbx_status_to_hub(wbx_89,wbx_98)

        # Stop Ixia stream
        log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
        ixia_100g.stop_traffic()
        log_file.info("")
        log_file.info("Get stats for all traffic items")
        log_file.info("--------------------------------------------------")
        ixia_100g.set_stats()
        log_file.info("")

        drill_down_names = []

        #Allan
        kpidict=OrderedDict()
        kpidict['KPIs'] = list()
        kpi_ms = '.'.join([testcase_name,'loss_ms'])
        kpi_avg_latency = '.'.join([testcase_name,'avg_latency'])
        kpidict['KPIs'].append(kpi_ms)
        kpidict['KPIs'].append(kpi_avg_latency)

        for traffic_item in ixia_100g.traffic_names:
            key          = action + '-' + traffic_item 
            loss_ms      = ixia_100g.get_stats(traffic_item,'loss_ms')
            avg_latency  = ixia_100g.get_stats(traffic_item,'Store-Forward Avg Latency (ns)')
            #pdb.set_trace()
            kpidict['.'.join([kpi_ms,traffic_item])] = loss_ms
            kpidict['.'.join([kpi_avg_latency,traffic_item])] = avg_latency
            if loss_ms > 0:
                log_file.info("Phase 3: Traffic item %s Loss Detected" %(traffic_item))
                phase_3_result = 'DRILL'
                drill_down_names.append(traffic_item)
            else:
                log_file.info("Phase 3: Traffic item %s No Loss Detected" %(traffic_item))

            #Allan - is this needed?
            test_result_dict[key] = loss_ms 

        if phase_3_result == 'PASS':
            log_file.info("")
            log_file.info("--------------------------------------------------")
            log_file.info("Phase 3: Pass") 
            log_file.info("--------------------------------------------------")
        else:
            log_file.info("")
            log_file.info("--------------------------------------------------------------")
            log_file.info("Phase 3 Drill Down per IPv6 traffic class stats on streams with loss")
            log_file.info("--------------------------------------------------------------")

            for drill_down_name in drill_down_names:
                dd_opt = 'Drill down per IPv6 :Traffic Class'
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt=dd_opt)
                drill_down_name_2 = drill_down_name + '/' + dd_opt

                if dd_opt in ixia_100g.ddopts:
                    tc_list = ixia_100g.user_stats[drill_down_name_2].keys()
                    tc_list.remove('columnCaptions')

                    for tc in tc_list:
                        #Allan
                        if action == 'fail_ring_1_to_mls_1_lag': 
                            dd_ep = False
                            loss = ixia_100g.get_user_def_drill_stats(drill_down_name,tc,'loss%',ddopt=dd_opt) 
                            tc_dict_x = {'0':35,'32':1,'64':1,'96':1,'128':1,'184':1,'224':1} 
                            if (loss > tc_dict_x[tc]):
                                log_file.error("TC %s loss of %s percent is above threshold of %s percent" %(tc,loss,tc_dict_x[tc]))
                                phase_3_result = 'FAIL'
                            else:
                                log_file.info("TC %s loss of %s percent is below threshold of %s percent" %(tc,loss,tc_dict_x[tc]))
                        elif action == 'fail_ring_6_to_mls_2_lag':
                            dd_ep = False
                            loss = ixia_100g.get_user_def_drill_stats(drill_down_name,tc,'loss%',ddopt=dd_opt) 
                            tc_dict_y = {'0':13,'32':1,'64':1,'96':1,'128':1,'184':1,'224':1} 
                            if (loss > tc_dict_y[tc]):
                                log_file.error("TC %s loss of %s percent is above threshold of %s percent" %(tc,loss,tc_dict_y[tc]))
                                phase_3_result = 'FAIL'
                            else:
                                log_file.error("TC %s loss of %s percent is below threshold of %s percent" %(tc,loss,tc_dict_y[tc]))
                        else:
                            loss = ixia_100g.get_user_def_drill_stats(drill_down_name,tc,'loss_ms',ddopt=dd_opt) 
                            if (loss > tc_dict[tc]):
                                log_file.error("TC %s loss of %s ms is above threshold of %s ms" %(tc,loss,tc_dict[tc]))
                                phase_3_result = 'FAIL'
                            else:
                                log_file.info("TC %s loss of %s ms is below threshold of %s ms" %(tc,loss,tc_dict[tc]))
                else:
                    log_file.info("Traffic stream does not have %s drill down" %(dd_opt))
                    log_file.info("Assume Best Effort")
                    tc = '0'
                    loss = (ixia_100g.get_stats(traffic_item,'loss_ms') > tc_dict[tc])
                    if (loss > tc_dict[tc]):
                        log_file.error("Best Effort loss of %s ms above threshold of %s ms" %(loss,tc_dict[tc]))
                        phase_3_result = 'FAIL'
                    else:
                        log_file.info("Best Effort loss of %s ms below threshold of %s ms" %(loss,tc_dict[tc]))

            if dd_ep:
                log_file.info("--------------------------------------------------------------")
                log_file.info("Drill Down per source / destination pair for error streams")
                log_file.info("--------------------------------------------------------------")
                for drill_down_name in drill_down_names:
                    log_file.info("")
                    # Polling ixia too quickly gives result for last poll
                    time.sleep(10)


                    ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                    if 'EDN' in drill_down_name:
                        loss_threshold_ms = 5000 
                    else:
                        loss_threshold_ms = 3000 
                    if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                        phase_3_result = 'FAIL'
                    else:
                        log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            if phase_3_result == 'FAIL':
                log_file.error("")
                log_file.error("--------------------------------------------------")
                log_file.error("Phase 3: Fail") 
                log_file.error("--------------------------------------------------")
            else:
                log_file.info("")
                log_file.info("--------------------------------------------------")
                log_file.info("Phase 3: Pass") 
                log_file.info("--------------------------------------------------")

        log_file.info("")
        log_file.info("")

        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 4: Recover Failure")
        log_file.info("--------------------------------------------------")
        log_file.info("")

        if mls_1.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on MLS 1")

        if mls_2.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on MLS 2")

        if ring_1.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on Ring 1")

        if ring_2.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on Ring 2")

        if ring_3.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on Ring 3")

        if ring_4.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on Ring 4")

        if ring_5.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on Ring 5")

        if ring_6.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result = 'FAIL'
        else:
            log_file.info("Valid standby on Ring 6")


        set_mode_ring(testbed_nodes)

        if not check_mode_ring(testbed_nodes):
            phase_4_result = 'FAIL'

        if not wait_all_default_routes(testbed_nodes, 120):
            phase_4_result = 'FAIL'

    else:
        log_file.error("Test set up failed")
        test_result = 'FAIL'

    end_time = datetime.now()
    test_dur = end_time - start_time
    test_dur_sec = test_dur.total_seconds()

    if phase_1_result == 'FAIL':
        log_file.info("ALLOW RING PHASE 1 FAILS FOR NOW UNTIL FCS ERROR FIXED!!!!!")
        #test_result = 'FAIL'

    if phase_2_result == 'FAIL':
        test_result = 'FAIL'

    if phase_3_result == 'FAIL':
        test_result = 'FAIL'

    if phase_4_result == 'FAIL':
        test_result = 'FAIL'

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("Test Name %s " %(action))
    log_file.info("End time: %s" %str(end_time))
    log_file.info("")
    log_file.info("")
    log_file.info("Duration: %s seconds" %(str(test_dur_sec)))
    if test_result == 'PASS':
        log_file.info("Result = %s " %(test_result))
    else:
        log_file.error("Result = %s " %(test_result))
    log_file.info("--------------------------------------------------")
    log_file.info("")

    if (csv == 'true'):
        log_file.info("")
        log_file.info("Take CSV snapshot")
        log_file.info("")
        ixia.take_stats_snapshot(ixNet,'Flow Statistics', 'C:\\ixiaStats')

    test_result_list.append(test_result)
    test_result_list.append(kpidict)

    #key = testplan[action]['node'] + '_' + 'loss'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'loss%') 
    #key = testplan[action]['node'] + '_' + 'min_latency'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'min_latency') 

    #key = testplan[action]['node'] + '_' + 'max_latency'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'max_latency') 

    #key = testplan[action]['node'] + '_' + 'avg_latency'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'avg_latency') 

    # close ssh connections
    for nx in testbed_nodes.keys():
        testbed_nodes[nx].close()

    return test_result_list


def check_edn_ready(edn_routes, wait_min):

    count       = 0
    edn_results = {} 

    log_file.info('Wait up to %s MINUTES for EDN to be ready' %(wait_min))

    while count <= wait_min:
        edn_check = True 
        edn_results['mls_1_up']   = testbed_data['mls_1'].send_cli_command('show router 4 interface | match SRa8-Hub1 | match "Down/Up" | count ', see_return=True)
        edn_results['mls_1_down'] = testbed_data['mls_1'].send_cli_command('show router 4 interface | match SRa8-Hub2 | match "Down/Up" | count ', see_return=True)

        edn_results['mls_2_up']   = testbed_data['mls_2'].send_cli_command('show router 4 interface | match SRa8-Hub2 | match "Down/Up" | count ', see_return=True)
        edn_results['mls_2_down'] = testbed_data['mls_2'].send_cli_command('show router 4 interface | match SRa8-Hub1 | match "Down/Up" | count ', see_return=True)

        for key, value in edn_results.iteritems():
            val_1 = value[1].split('Count')
            val_2 = val_1[1].split('lines')
            val_3 = val_2[0]
            val_4 = val_3.replace(' ', '')
            val_5 = val_4.replace(':','')
            edn_results[key] = int(val_5)

        log_file.info("MLS 1 VPRN 4 : # of up OAM interfaces to 5G-SRa8-Hub1   = %s | expecting %s " %(edn_results['mls_1_up'],edn_routes))
        log_file.info("MLS 1 VPRN 4 : # of down OAM interfaces to 5G-SRa8-Hub2 = %s | expecting 0 "  %(edn_results['mls_1_down']))
        log_file.info("MLS 2 VPRN 4 : # of up OAM interfaces to 5G-SRa8-Hub2   = %s | expecting %s " %(edn_results['mls_2_up'],edn_routes))
        log_file.info("MLS 2 VPRN 4 : # of down OAM interfaces to 5G-SRa8-Hub1 = %s | expecting 0 "  %(edn_results['mls_2_down']))

        if edn_results['mls_1_up'] != edn_routes :
            edn_check = False 
        if edn_results['mls_2_down'] != 0:
            edn_check = False 
        if edn_results['mls_2_up'] != edn_routes :
            edn_check = False 
        if edn_results['mls_2_down'] != 0:
            edn_check = False 

        if edn_check:
            log_file.info('EDN ready')
            return edn_check 
        else:
            log_file.info('EDN not ready ... wait 60s before trying again')
            count +=1
            time.sleep(60)

    log_file.error('EDN not ready')
    return False 


def mls_status(mls_1,mls_2):

    #log_file.info("--------------------------------------------------")
    #log_file.info("MLS 1 Switch fabric status " )
    #log_file.info("--------------------------------------------------")
    #mls_1.send_cli_command("show system switch-fabric")
    #log_file.info("")
    #log_file.info("")

    #log_file.info("--------------------------------------------------")
    #log_file.info("MLS 1 port utilization")
    #log_file.info("--------------------------------------------------")
    #mls_1.print_cli_port_util("6/1/1")
    #mls_1.print_cli_port_util("6/2/1")
    #mls_1.print_cli_port_util("7/2/1")
    #mls_1.print_cli_port_util("7/1/1")

    log_file.info("--------------------------------------------------")
    log_file.info("MLS 1 lag utilization")
    log_file.info("--------------------------------------------------")
    mls_1.print_cli_lag_util("lag-21")
    mls_1.print_cli_lag_util("lag-1")
    mls_1.print_cli_lag_util("lag-183")
    log_file.info("")
    log_file.info("")

    #log_file.info("--------------------------------------------------")
    #log_file.info("MLS 2 Switch fabric status" )
    #log_file.info("--------------------------------------------------")
    #mls_2.send_cli_command("show system switch-fabric")
    #log_file.info("")
    #log_file.info("")

    #log_file.info("--------------------------------------------------")
    #log_file.info("MLS 2 port utilization" )
    #log_file.info("--------------------------------------------------")
    #mls_2.print_cli_port_util("6/1/1")
    #mls_2.print_cli_port_util("6/2/1")
    #mls_2.print_cli_port_util("7/2/1")
    #mls_2.print_cli_port_util("7/1/1")
    log_file.info("----------------:----------------------------------")
    log_file.info("MLS 2 lag utilization")
    log_file.info("--------------------------------------------------")
    mls_2.print_cli_lag_util("lag-22")
    mls_2.print_cli_lag_util("lag-1")
    mls_2.print_cli_lag_util("lag-183")
    log_file.info("")
    log_file.info("")


def offload_status_to_hubs(off_1,off_2):

    log_file.info("--------------------------------------------------")
    log_file.info("Offload 1 port utilization")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    off_1.print_cli_lag_util("lag-39")

    log_file.info("--------------------------------------------------")
    log_file.info("Offload 2 port utilization" )
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    off_2.print_cli_lag_util("lag-129")


def hub_status_with_offload(hub_1,hub_2):

    log_file.info("--------------------------------------------------")
    log_file.info("Hub 1 port utilization")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    hub_1.print_cli_lag_util("lag-1")
    hub_1.print_cli_lag_util("lag-2")

    log_file.info("--------------------------------------------------")
    log_file.info("Hub 2 port utilization" )
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    hub_2.print_cli_lag_util("lag-14")
    hub_2.print_cli_lag_util("lag-9")
    hub_2.print_cli_lag_util("lag-2")


def hub_status_no_offload(hub_1,hub_2):

    log_file.info("--------------------------------------------------")
    log_file.info("Hub 1 port utilization")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    hub_1.print_cli_lag_util("lag-14")
    hub_1.print_cli_lag_util("lag-5")
    hub_1.print_cli_lag_util("lag-2")

    log_file.info("--------------------------------------------------")
    log_file.info("Hub 2 port utilization" )
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    hub_2.print_cli_lag_util("lag-8")
    hub_2.print_cli_lag_util("lag-2")


def wbx_status_to_offload(wbx_89,wbx_98):

    log_file.info("--------------------------------------------------")
    log_file.info("WBX89 to Offload 1 port utilization")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    wbx_89.print_cli_lag_util("lag-1")
    wbx_89.print_cli_lag_util("lag-2")
    wbx_89.print_cli_lag_util("lag-3")
    wbx_89.print_cli_lag_util("lag-4")
    wbx_89.print_cli_lag_util("lag-5")

    log_file.info("--------------------------------------------------")
    log_file.info("WBX98 to Offload 2 port utilization" )
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    wbx_98.print_cli_lag_util("lag-1")
    wbx_98.print_cli_lag_util("lag-2")
    wbx_98.print_cli_lag_util("lag-3")
    wbx_98.print_cli_lag_util("lag-4")
    wbx_98.print_cli_lag_util("lag-5")


def wbx_status_to_hub(wbx_89,wbx_98):

    log_file.info("--------------------------------------------------")
    log_file.info("WBX89 to Hub 1 port utilization")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    wbx_89.print_cli_lag_util("lag-14")

    log_file.info("--------------------------------------------------")
    log_file.info("WBX98 to Hub 2 port utilization")
    log_file.info("--------------------------------------------------")
    log_file.info("")
    log_file.info("")
    wbx_98.print_cli_lag_util("lag-14")



def set_mode_ring(testbed_nodes):

    mls_1 = testbed_nodes['mls_1']
    mls_2 = testbed_nodes['mls_2']

    off_1 = testbed_nodes['off_1']
    off_2 = testbed_nodes['off_2']

    ring_1 = testbed_nodes['hub_1']
    ring_2 = testbed_nodes['hub_2']
    ring_3 = testbed_nodes['hub_3']
    ring_4 = testbed_nodes['hub_4']
    ring_5 = testbed_nodes['hub_5']
    ring_6 = testbed_nodes['hub_6']

    log_file.info('Put testbed in Mode: Ring')

    mls_1.to_crs.no_shutdown(snmp=True)
    mls_1.to_crs.no_shutdown_all_lag_members()
    mls_1.to_crs.set_ether_stats_interval(30)

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()
    mls_1.to_off_1.set_ether_stats_interval(30)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()
    mls_1.to_mls_2.set_ether_stats_interval(30)

    mls_1.to_ring_1.no_shutdown(snmp=True)
    mls_1.to_ring_1.no_shutdown_all_lag_members()
    mls_1.to_ring_1.set_ether_stats_interval(30)

    mls_2.to_crs.no_shutdown(snmp=True)
    mls_2.to_crs.set_ether_stats_interval(30)

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()
    mls_2.to_off_2.set_ether_stats_interval(30)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()
    mls_2.to_mls_1.set_ether_stats_interval(30)

    mls_2.to_ring_2.shutdown(snmp=True)

    mls_2.to_ring_6.no_shutdown(snmp=True)
    mls_2.to_ring_6.no_shutdown_all_lag_members()

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()
    off_1.to_mls_1.set_ether_stats_interval(30)

    off_1.to_ring_1.shutdown(snmp=True)

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()
    off_2.to_mls_2.set_ether_stats_interval(30)

    off_2.to_ring_2.shutdown(snmp=True)

    ring_1.to_off_1.shutdown(snmp=True)

    ring_1.to_mls_1.no_shutdown(snmp=True)
    ring_1.to_mls_1.no_shutdown_all_lag_members()
    ring_1.to_mls_1.set_ether_stats_interval(30)

    ring_1.to_ring_2.no_shutdown(snmp=True)
    ring_1.to_ring_2.no_shutdown_all_lag_members()
    ring_1.to_ring_2.set_ether_stats_interval(30)

    ring_2.to_off_2.shutdown(snmp=True)
    ring_2.to_mls_2.shutdown(snmp=True)

    ring_2.to_ring_1.no_shutdown(snmp=True)
    ring_2.to_ring_1.no_shutdown_all_lag_members()
    ring_2.to_ring_1.set_ether_stats_interval(30)

    ring_2.to_ring_3.no_shutdown(snmp=True)
    ring_2.to_ring_3.no_shutdown_all_lag_members()
    ring_2.to_ring_3.set_ether_stats_interval(30)

    ring_3.to_ring_2.no_shutdown(snmp=True)
    ring_3.to_ring_2.no_shutdown_all_lag_members()
    ring_3.to_ring_2.set_ether_stats_interval(30)


    ring_3.to_ring_4.no_shutdown(snmp=True)
    ring_3.to_ring_4.no_shutdown_all_lag_members()
    ring_3.to_ring_4.set_ether_stats_interval(30)
   
    ring_4.to_ring_3.no_shutdown(snmp=True)
    ring_4.to_ring_3.no_shutdown_all_lag_members()
    ring_4.to_ring_3.set_ether_stats_interval(30)

    ring_4.to_ring_5.no_shutdown(snmp=True)
    ring_4.to_ring_5.no_shutdown_all_lag_members()
    ring_4.to_ring_5.set_ether_stats_interval(30)

    ring_5.to_ring_4.no_shutdown(snmp=True)
    ring_5.to_ring_4.no_shutdown_all_lag_members()
    ring_5.to_ring_4.set_ether_stats_interval(30)

    ring_5.to_ring_6.no_shutdown(snmp=True)
    ring_5.to_ring_6.no_shutdown_all_lag_members()
    ring_5.to_ring_6.set_ether_stats_interval(30)

    ring_6.to_ring_5.no_shutdown(snmp=True)
    ring_6.to_ring_5.no_shutdown_all_lag_members()
    ring_6.to_ring_5.set_ether_stats_interval(30)


    ring_6.to_mls_2.no_shutdown(snmp=True)
    ring_6.to_mls_2.no_shutdown_all_lag_members()
    ring_6.to_mls_2.set_ether_stats_interval(30)


def check_mode_ring(testbed_nodes):

    result = True 

    mls_1 = testbed_nodes['mls_1']
    mls_2 = testbed_nodes['mls_2']

    off_1 = testbed_nodes['off_1']
    off_2 = testbed_nodes['off_2']

    ring_1 = testbed_nodes['hub_1']
    ring_2 = testbed_nodes['hub_2']
    ring_3 = testbed_nodes['hub_3']
    ring_4 = testbed_nodes['hub_4']
    ring_5 = testbed_nodes['hub_5']
    ring_6 = testbed_nodes['hub_6']


    log_file.info('Check testbed is in Mode: Ring')
     
    if (mls_1.to_crs.wait_port_oper_up(120) != 'OK'):
        result = False

    if (mls_1.to_off_1.wait_port_oper_up(120) != 'OK'):
        result = False

    if (mls_1.to_mls_2.wait_port_oper_up(120) != 'OK'):
        result = False

    if (mls_1.to_ring_1.wait_port_oper_up(120) != 'OK'):
        result = False

    if not mls_1.to_crs.wait_all_lag_members_oper_up(120):
        result = False

    if not mls_1.to_off_1.wait_all_lag_members_oper_up(120):
        result = False

    if not mls_1.to_mls_2.wait_all_lag_members_oper_up(120):
        result = False

    if not mls_1.to_ring_1.wait_all_lag_members_oper_up(120):
        result = False

    if (mls_2.to_crs.wait_port_oper_up(120) != 'OK'):
        result = False

    if (mls_2.to_off_2.wait_port_oper_up(120) != 'OK'):
        result = False

    if (mls_2.to_mls_1.wait_port_oper_up(120) != 'OK'):
        result = False

    if (mls_2.to_ring_2.wait_port_oper_down(10) != 'OK'):
        result = False

    if (mls_2.to_ring_6.wait_port_oper_up(120) != 'OK'):
        result = False

    if not mls_2.to_crs.wait_all_lag_members_oper_up(120):
        result = False

    if not mls_2.to_off_2.wait_all_lag_members_oper_up(120):
        result = False

    if not mls_2.to_mls_1.wait_all_lag_members_oper_up(120):
        result = False

    if not mls_2.to_ring_6.wait_all_lag_members_oper_up(120):
        result = False

    if (off_1.to_mls_1.wait_port_oper_up(120) != 'OK'):
        result = False

    if (off_1.to_ring_1.wait_port_oper_down(10) != 'OK'):
        result = False

    if not off_1.to_mls_1.wait_all_lag_members_oper_up(120):
        result = False

    if (off_2.to_mls_2.wait_port_oper_up(120) != 'OK'):
        result = False

    if (off_2.to_ring_2.wait_port_oper_down(10) != 'OK'):
        result = False

    if not off_2.to_mls_2.wait_all_lag_members_oper_up(120):
        result = False

    if (ring_1.to_off_1.wait_port_oper_down(10) != 'OK'):
        result = False

    if (ring_1.to_mls_1.wait_port_oper_up(120) != 'OK'):
        result = False

    if (ring_1.to_ring_2.wait_port_oper_up(120) != 'OK'):
        result = False

    if not ring_1.to_mls_1.wait_all_lag_members_oper_up(120):
        result = False

    if not ring_1.to_ring_2.wait_all_lag_members_oper_up(120):
        result = False

    if (ring_2.to_off_2.wait_port_oper_down(10) != 'OK'):
        result = False

    if (ring_2.to_mls_2.wait_port_oper_down(10) != 'OK'):
        result = False

    if (ring_2.to_ring_3.wait_port_oper_up(120) != 'OK'):
        result = False

    if not ring_2.to_ring_3.wait_all_lag_members_oper_up(120):
        result = False

    if (ring_3.to_ring_2.wait_port_oper_up(120) != 'OK'):
        result = False

    if (ring_3.to_ring_4.wait_port_oper_up(120) != 'OK'):
        result = False

    if not ring_3.to_ring_2.wait_all_lag_members_oper_up(120):
        result = False

    if not ring_3.to_ring_4.wait_all_lag_members_oper_up(120):
        result = False

    if (ring_4.to_ring_3.wait_port_oper_up(120) != 'OK'):
        result = False

    if (ring_4.to_ring_5.wait_port_oper_up(120) != 'OK'):
        result = False

    if not ring_4.to_ring_3.wait_all_lag_members_oper_up(120):
        result = False

    if not ring_4.to_ring_5.wait_all_lag_members_oper_up(120):
        result = False

    if (ring_5.to_ring_4.wait_port_oper_up(120) != 'OK'):
        result = False

    if (ring_5.to_ring_6.wait_port_oper_up(120) != 'OK'):
        result = False

    if not ring_5.to_ring_4.wait_all_lag_members_oper_up(120):
        result = False

    if not ring_5.to_ring_6.wait_all_lag_members_oper_up(120):
        result = False

    if (ring_6.to_ring_5.wait_port_oper_up(120) != 'OK'):
        result = False

    if (ring_6.to_mls_2.wait_port_oper_up(120) != 'OK'):
        result = False

    if not ring_6.to_ring_5.wait_all_lag_members_oper_up(120):
        result = False

    if not ring_6.to_mls_2.wait_all_lag_members_oper_up(120):
        result = False

    return result


def set_mode_hub_with_offload(mls_1, mls_2, off_1, off_2, ring_1, ring_2):


    log_file.info('Put testbed in Mode: CRAN Hub with Offload')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_ring_1.shutdown(snmp=True)

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_ring_2.shutdown(snmp=True)

    mls_2.to_ring_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_ring_1.no_shutdown(snmp=True)
    off_1.to_ring_1.no_shutdown_all_lag_members()

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_ring_2.no_shutdown(snmp=True)
    off_2.to_ring_2.no_shutdown_all_lag_members()

    ring_1.to_off_1.no_shutdown(snmp=True)
    ring_1.to_off_1.no_shutdown_all_lag_members()

    ring_1.to_mls_1.shutdown(snmp=True)
    ring_1.to_ring_2.no_shutdown(snmp=True)

    ring_2.to_off_2.no_shutdown(snmp=True)
    ring_2.to_mls_2.shutdown(snmp=True)
    ring_2.to_ring_3.shutdown(snmp=True)
    ring_2.to_ring_1.no_shutdown(snmp=True)


def show_ring(testbed_nodes):


    m1m2_t = testbed_nodes['mls_1'].to_mls_2.get_util_perc('tx')
    m1m2_r = testbed_nodes['mls_1'].to_mls_2.get_util_perc('rx')

    m2m1_t = testbed_nodes['mls_2'].to_mls_1.get_util_perc('tx')
    m2m1_r = testbed_nodes['mls_2'].to_mls_1.get_util_perc('rx')

    m2r6_t = testbed_nodes['mls_2'].to_ring_6.get_util_perc('tx')
    m2r6_r = testbed_nodes['mls_2'].to_ring_6.get_util_perc('rx')

    m1r1_t = testbed_nodes['mls_1'].to_ring_1.get_util_perc('tx')
    m1r1_r = testbed_nodes['mls_1'].to_ring_1.get_util_perc('rx')

    r1m1_t = testbed_nodes['hub_1'].to_mls_1.get_util_perc('tx')
    r1m1_r = testbed_nodes['hub_1'].to_mls_1.get_util_perc('rx')

    r1r2_t = testbed_nodes['hub_1'].to_ring_2.get_util_perc('tx')
    r1r2_r = testbed_nodes['hub_1'].to_ring_2.get_util_perc('rx')

    r2r1_t = testbed_nodes['hub_2'].to_ring_1.get_util_perc('tx')
    r2r1_r = testbed_nodes['hub_2'].to_ring_1.get_util_perc('rx')

    r2r3_t = testbed_nodes['hub_2'].to_ring_3.get_util_perc('tx')
    r2r3_r = testbed_nodes['hub_2'].to_ring_3.get_util_perc('rx')

    r3r2_t = testbed_nodes['hub_3'].to_ring_2.get_util_perc('tx')
    r3r2_r = testbed_nodes['hub_3'].to_ring_2.get_util_perc('rx')

    r3r4_t = testbed_nodes['hub_3'].to_ring_4.get_util_perc('tx')
    r3r4_r = testbed_nodes['hub_3'].to_ring_4.get_util_perc('rx')

    r4r3_t = testbed_nodes['hub_4'].to_ring_3.get_util_perc('tx')
    r4r3_r = testbed_nodes['hub_4'].to_ring_3.get_util_perc('rx')

    r4r5_t = testbed_nodes['hub_4'].to_ring_5.get_util_perc('tx')
    r4r5_r = testbed_nodes['hub_4'].to_ring_5.get_util_perc('rx')

    r5r4_t = testbed_nodes['hub_5'].to_ring_4.get_util_perc('tx')
    r5r4_r = testbed_nodes['hub_5'].to_ring_4.get_util_perc('rx')

    r5r6_t = testbed_nodes['hub_5'].to_ring_6.get_util_perc('tx')
    r5r6_r = testbed_nodes['hub_5'].to_ring_6.get_util_perc('rx')

    r6r5_t = testbed_nodes['hub_6'].to_ring_5.get_util_perc('tx')
    r6r5_r = testbed_nodes['hub_6'].to_ring_5.get_util_perc('rx')

    r6m2_t = testbed_nodes['hub_6'].to_mls_2.get_util_perc('tx')
    r6m2_r = testbed_nodes['hub_6'].to_mls_2.get_util_perc('rx')

    log_file.info("")
    log_file.info("                 +------+        +------+              ")
    log_file.info("                 |      | Tx  Rx |      |              ")
    log_file.info("                 |      | %s  %s   |      |              "%(m1m2_t, m2m1_r))
    log_file.info("        +--------+ MLS1 +--------+ MLS2 +--------+     ")
    log_file.info("        |        |      | %s  %s   |      |        |     "%(m1m2_r, m2m1_t))
    log_file.info("        |        |      | Rx  Tx |      |        |     ")
    log_file.info("        |        +------+        +------+        |     ")
    log_file.info("        |                                        |     ")
    log_file.info("     Rx | Tx                                  Rx | Tx  ")
    log_file.info("     %s   %s                                  %s   %s  "%(m1r1_r,m1r1_t,m2r6_r,m2r6_t))
    log_file.info("        |                                        |     ")
    log_file.info("        |                                        |     ")
    log_file.info("     Tx | Rx                                  Tx | Rx  ")
    log_file.info("     %s   %s                                  %s   %s  "%(r1m1_t,r1m1_r,r6m2_t,r6m2_r))
    log_file.info("        |                                        |     ")
    log_file.info("    +---+---+                                +---+---+ ")
    log_file.info("    |       |                                |       | ")
    log_file.info("    | RING1 |                                | RING6 | ")
    log_file.info("    |       |                                |       | ")
    log_file.info("    |       |                                |       | ")
    log_file.info("    +---+---+                                +---+---+ ")
    log_file.info("        |                                        |     ")
    log_file.info("     Rx | Tx                                  Rx | Tx  ")
    log_file.info("     %s | %s                                  %s | %s  "%(r1r2_r,r1r2_t,r6r5_r,r6r5_t))
    log_file.info("        |                                        |     ")
    log_file.info("     Tx | Rx                                  Tx | Rx  ")
    log_file.info("     %s | %s                                  %s | %s  "%(r2r1_t,r2r1_r,r5r6_t,r5r6_r))
    log_file.info("        |                                        |     ")
    log_file.info("    +---+---+                                +---+---+ ")
    log_file.info("    |       |                                |       | ")
    log_file.info("    | RING2 |                                | RING5 | ")
    log_file.info("    |       |                                |       | ")
    log_file.info("    |       |                                |       | ")
    log_file.info("    +---+---+                                +---+---+ ")
    log_file.info("        |                                        |     ")
    log_file.info("     Rx | Tx                                  Rx | Tx  ")
    log_file.info("     %s  | %s                                    %s | %s  "%(r2r3_r,r2r3_t,r5r4_r,r5r4_t))
    log_file.info("        |                                        |     ")
    log_file.info("     Tx | Rx                                  Tx | Rx  ")
    log_file.info("     %s  | %s                                    %s | %s  "%(r3r2_t,r3r2_r,r4r5_t,r4r5_r))
    log_file.info("        |                                        |     ")
    log_file.info("        |        +------+        +------+        |     ")
    log_file.info("        |        |      | Tx  Rx |      |        |     ")
    log_file.info("        |        |      | %s  %s   |      |        |     "%(r3r4_t, r4r3_r))
    log_file.info("        +--------+ RING +--------+ RING +--------+     ")
    log_file.info("                 |  3   | %s  %s   |  4   |              "%(r3r4_r, r4r3_t))
    log_file.info("                 |      | Rx  Tx  |      |              ")
    log_file.info("                 +------+        +------+              ")
    log_file.info("")
    log_file.info("")

    
def wait_all_default_routes (testbed_nodes, wait):

    # Ugly, will change.
    count = 0
    default_route = {}
    default_route['hub_1'] = 'ToSR163'
    default_route['hub_2'] = 'To-Hub-1'
    default_route['hub_3'] = 'To-Hub-2'
    default_route['hub_4'] = 'To-Hub-5'
    default_route['hub_5'] = 'To-Hub-6'
    default_route['hub_6'] = 'ToSR164'
    default_route['mls_1'] = '2001:4888:2015:6101:162:1:0:1'
    default_route['mls_2'] = '2001:4888:2015:6102:162:2:0:1'

    log_file.info("Wait up to %s seconds for all default routes to be correct" %(count))
    while count <= wait:
        default_result = True 
        for key, value in default_route.iteritems():
            res, cli_return = testbed_nodes[key].send_cli_command('show router route-table ipv6 ::/0',see_return=True)
            if value not in cli_return:
                default_result = False 
            else:
                default_result = True 
        if default_result == True:
            log_file.info("All default routes correct after %s seconds" %(count))
            break
        else:
            count +=1
            time.sleep(1)
    return default_result


def set_mode_hub_no_offload(mls_1, mls_2, off_1, off_2, ring_1, ring_2):

    log_file.info('Put testbed in Mode: CRAN Hub no Offload')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_ring_1.no_shutdown(snmp=True)
    mls_1.to_ring_1.no_shutdown_all_lag_members()

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_ring_2.no_shutdown(snmp=True)
    mls_2.to_ring_2.no_shutdown_all_lag_members()

    mls_2.to_ring_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_ring_1.shutdown(snmp=True)

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_ring_2.shutdown(snmp=True)

    ring_1.to_off_1.shutdown(snmp=True)

    ring_1.to_mls_1.no_shutdown(snmp=True)
    ring_1.to_mls_1.no_shutdown_all_lag_members()

    ring_1.to_ring_2.no_shutdown(snmp=True)
    ring_1.to_ring_2.no_shutdown_all_lag_members()

    ring_2.to_ring_1.no_shutdown(snmp=True)
    ring_2.to_ring_1.no_shutdown_all_lag_members()

    ring_2.to_off_2.shutdown(snmp=True)

    ring_2.to_mls_2.no_shutdown(snmp=True)
    ring_2.to_mls_2.no_shutdown_all_lag_members()

    ring_2.to_ring_3.shutdown(snmp=True)

    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1" no shutdown')
    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1-IPv6" no shutdown')

    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2" no shutdown')
    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2-IPv6" no shutdown')



def set_all_port_ether_stats_itvl(testbed_nodes,itvl=300):

    log_file.info("Set util-stats-interval on all testbed ports to %s seconds" %(itvl))
    for nx in sorted(testbed_nodes.keys()):
        if 'wbx_' not in nx:
            my_node = testbed_nodes[nx]
            for px in my_node.port_dict.keys():
                my_port = my_node.port_dict[px]
                if isinstance(my_port, node.Port):
                    my_port.set_ether_stats_interval(itvl)


def shutdown_all_log_98(testbed_nodes):
    log_file.info("Shutdown log 98 on all testbed nodes to keep the NSP alarm log quiet")
    for nx in testbed_nodes.keys():
        testbed_nodes[nx].shutdown_log_98()


def no_shutdown_all_log_98(testbed_nodes):
    log_file.info("No shutdown log 98 on all testbed nodes")
    for nx in testbed_nodes.keys():
        testbed_nodes[nx].no_shutdown_log_98()



if (__name__ == '__main__'):

    # Get all user input command options
    try:
        optlist, args = getopt.getopt(sys.argv[1:],"t:s:c:h")
    except getopt.GetoptError as err:
        print "\nERROR: %s" %(err)
        sys.exit(0)

    test_params=dict()
    test_params['testcase_name'] = ''

    # Parse input options and validate format
    for opt,val in optlist:
        if opt == "-s":
            # test suite
            test_params['testsuite_name'] = val
        elif opt == "-t":
            # test case
            test_params['testcase_name'] = val
        elif opt == "-c":
            # enable csv stat logging
            test_params['csv'] = val
        else: 
            print "option: %s a is not implemented yet!!"%(opt,val)
            sys.exit() 
    # Check for mandatory arguements
    if test_params['testcase_name'] == '':
        print "\nERROR: Option -t (testcase_name) is mandatory"
        sys.exit()

    main(**test_params)
