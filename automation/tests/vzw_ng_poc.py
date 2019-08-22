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
    testbed_data.ixia_poc    = ixia.IxNetx(**yaml_data['ixia'])

    log_file.info('Build Nodes, IOMs, MDAs, Ports and Services ...')
    for tb_node in yaml_data['nodes'].keys() :
        cpm_obj=node.Node(**yaml_data['nodes'][tb_node])
        testbed_data[tb_node] = cpm_obj


def main(testcase_name='',testsuite_name='vzw_5g_poc',csv='false',testbed_file='vzw_5g_poc.yaml'):

    hub_site_stat       = {}
    hub_site_stat_final = {}
    test_result         = 'PASS'
    set_up_result       = 'PASS'
    phase_1_result      = 'PASS'
    phase_2_result      = 'PASS'
    phase_3_result      = 'PASS'
    phase_4_result      = 'PASS'
    test_path           = '/automation/python/tests/'
    testbed_file        = test_path+testbed_file
    standby_wait        = 240
    port_wait           = 120
    drill_down_names    = []
    test_result_list    = [] 
    test_result_dict    = {} 

    # Initialize the base testbed
    testbed_init(testbed_file)

    # Create a dict from testbed_data of ONLY testbed_nodes
    # i.e. strip out ixia, etc.
    testbed_nodes = {}
    for key, value in testbed_data.iteritems():
       if isinstance(value, node.Node): 
           testbed_nodes[key] = value 

    start_time = datetime.now()

    # Give the nodes user friendly names 
    
    el_1 = testbed_data['el_1']
    el_2 = testbed_data['el_2']

    spine_1 = testbed_data['spine_1']
    spine_2 = testbed_data['spine_2']

    al_1 = testbed_data['el_1']
    al_2 = testbed_data['el_2']

    hub_1 = testbed_data['el_1']
    hub_2 = testbed_data['el_2']

    ixia_poc = testbed_data.ixia_poc

    testplan = {}

    # Tests to set up suite topology
    testplan['5g_poc_set_up']    = {'ixia_pat' : '5G-POC', 'action' : 'suite_set_up', 'topology' : 'NG_POC'}
    testplan['sanity']           = {'ixia_pat' : '5G-POC', 'action' : 'sanity', 'topology' : 'NG_POC'}

    # Teardown 
    testplan['teardown']         = {'ixia_pat' : '5G-POC', 'action' : 'suite_teardown', 'topology' : 'NG_POC'}


    # Compare passed in testname to full list of possible testcases 
    if testcase_name not in testplan:
        print "\nERROR: Unsupported test case of %s"%(testcase_name)
        print "ERROR: run with -h to get list of supported test cases"
        sys.exit()

    # Read in testplan for specific testcase
    ixia_pattern = testplan[testcase_name]['ixia_pat']
    action       = testplan[testcase_name]['action']

    if 'topology' not in testplan[testcase_name]:  
        print "No topology specified in testplan.  Assume NG POC"
        topology = 'NG_POC' 
    else:
        topology = testplan[testcase_name]['topology']
        print "Testbed topology specified in testplan to be %s" %(topology)

    if 'tc_dict' not in testplan[testcase_name]:
        tc_dict = {}
    else:
        tc_dict = testplan[testcase_name]['tc_dict']

    log_file.info('Check all nodes for hw errors')
    for error_node in testbed_nodes.values():
        error_node.check_for_hw_errors()
            
    el_1_chassis_type          = el_1.get_chassis_type()
    el_1_cpm_active_sw_ver     = el_1.get_active_cpm_sw_version()

    el_2_chassis_type          = el_2.get_chassis_type()
    el_2_cpm_active_sw_ver     = el_2.get_active_cpm_sw_version()

    spine_1_chassis_type       = spine_1.get_chassis_type()
    spine_1_cpm_active_sw_ver  = spine_1.get_active_cpm_sw_version()

    spine_2_chassis_type       = spine_2.get_chassis_type()
    spine_2_cpm_active_sw_ver  = spine_2.get_active_cpm_sw_version()

    al_1_chassis_type          = al_1.get_chassis_type()
    al_1_cpm_active_sw_ver     = al_1.get_active_cpm_sw_version()

    al_2_chassis_type          = al_2.get_chassis_type()
    al_2_cpm_active_sw_ver     = al_2.get_active_cpm_sw_version()

    hub_1_chassis_type         = hub_1.get_chassis_type()
    hub_1_cpm_active_sw_ver    = hub_1.get_active_cpm_sw_version()

    hub_2_chassis_type         = hub_2.get_chassis_type()
    hub_2_cpm_active_sw_ver    = hub_2.get_active_cpm_sw_version()


    if action == 'suite_set_up':

        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Switch to %s topology" %(topology))
        log_file.info("--------------------------------------------------")
        log_file.info("")
    
        if topology == 'NG_POC':
           log_file.info('NG POC topology selected')
           log_file.info('TODO: Put in set up proc')
        else:
            log_file.error("Invalid topology defined")
            set_up_result == 'FAIL'

        if set_up_result == 'PASS':
           clear_all_port_stats(testbed_nodes)
           set_all_port_ether_stats_itvl(testbed_nodes,30)
           log_file.info('Suite set up OK, save the testbed configs')

           el_1.admin_save()
           el_2.admin_save()
           spine_1.admin_save()
           spine_2.admin_save()
           al_1.admin_save()
           al_2.admin_save()
           hub_1.admin_save()
           hub_2.admin_save()

        else:
           log_file.error('Suite set up FAILED')

        test_result_list = [] 
        test_result_list.append(set_up_result)
        test_result_dict = {} 
        return test_result_list
    
    if action == 'suite_teardown':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Suite teardown - return to %s topology" %(topology))
        log_file.info("--------------------------------------------------")
        log_file.info("")
        set_mode_hub_no_offload()
        #set_all_port_ether_stats_itvl(testbed_nodes,300)
        #no_shutdown_all_log_98(testbed_nodes)
        if not check_mode_hub_no_offload(): teardown_result = 'FAIL'
        else:
            teardown_result = 'PASS'

        log_file.info('Save the testbed configs')
        mls_1.admin_save()
        mls_2.admin_save()
        off_1.admin_save()
        off_2.admin_save()
        hub_1.admin_save()
        hub_2.admin_save()

        test_result_list = [] 
        test_result_list.append(teardown_result)
        test_result_dict = {} 
        return test_result_list

    # Set the ixia pattern based on the test
    ixia_poc.set_traffic(pattern=ixia_pattern, commit=True)

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
    log_file.info("Exit Leaf 1 chassis type ................ %s" %(el_1_chassis_type))
    log_file.info("Exit Leaf 1 Active CPM software version . %s" %(el_1_cpm_active_sw_ver))
    log_file.info("Exit Leaf 2 chassis type ................ %s" %(el_2_chassis_type))
    log_file.info("Exit Leaf 2 Active CPM software version . %s" %(el_2_cpm_active_sw_ver))
    log_file.info(" ")

    if set_up_result != 'FAIL':

        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 1: Pre failure Traffic Check") 
        log_file.info("")
        log_file.info("Start Ixia Traffic Streams ")
        log_file.info("--------------------------------------------------")
        log_file.info("")

        ixia_poc.start_traffic()
        ixia_poc.clear_stats()
        utils.countdown(10)

        ixia_poc.stop_traffic()

        log_file.info("")
        log_file.info("Get stats for all traffic items")
        log_file.info("--------------------------------------------------")
        ixia_poc.set_stats()

        for traffic_item in ixia_poc.traffic_names:
            if ixia_poc.get_stats(traffic_item,'rx') > ixia_poc.get_stats(traffic_item,'tx'):
                log_file.error("Phase 1: Traffic item %s Rx > Tx !" %(traffic_item))
                log_file.error("Phase 1: Traffic item %s Fail" %(traffic_item))
                log_file.error("")
                phase_1_result = 'FAIL'
            else:
                if ixia_poc.get_stats(traffic_item,'loss%') > 0:
                    log_file.error("Phase 1: Traffic item %s Loss > 0%%" %(traffic_item))
                    log_file.error("Phase 1: Traffic item %s Fail" %(traffic_item))
                    log_file.error("")
                    phase_1_result = 'FAIL'
                else:
                    log_file.info("Phase 1: Traffic item %s Loss = 0%%" %(traffic_item))
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

        ixia_poc.start_traffic()
        ixia_poc.clear_stats()
        utils.countdown(10)

        #log_file.info("Clear log-99 on all testbed nodes")
        #mls_1.clear_log_99()
        #mls_2.clear_log_99()
        #off_1.clear_log_99()
        #off_2.clear_log_99()
        #hub_1.clear_log_99()
        #hub_2.clear_log_99()

        if action == 'sanity':
            log_file.info("------------------------------")
            log_file.info("** Sanity test. No fail action")
            log_file.info("------------------------------")

        else:
            log_file.info("-----------------------------")
            log_file.info("** Undefined test case action")
            log_file.info("-----------------------------")
            log_file.info("")
            log_file.info("Stop Ixia Traffic Stream %s" %(ixia_poc.traffic_names))
            ixia_poc.stop_traffic()
            return 'FAIL'

        utils.countdown(20)

        log_file.info("")
        log_file.info("-------------------------------------------------------------------")
        log_file.info("Phase 3: Look at port util, stop Ixia, collect & Analyze Ixia Stats")
        log_file.info("-------------------------------------------------------------------")
        log_file.info("")

        # Stop Ixia stream
        log_file.info("Stop Ixia Traffic Stream %s" %(ixia_poc.traffic_names))
        ixia_poc.stop_traffic()
        log_file.info("")
        log_file.info("Get stats for all traffic items")
        log_file.info("--------------------------------------------------")
        ixia_poc.set_stats()
        log_file.info("")

        #Allan
        kpidict=OrderedDict()
        kpidict['KPIs'] = list()
        kpi = '.'.join([testcase_name,'loss_ms'])
        kpidict['KPIs'].append(kpi)

        # Empty list.  May still be populated by earlier action
        drill_down_names = []
        for traffic_item in ixia_poc.traffic_names:
            key = action + '-' + traffic_item 
            #loss_ms = ixia_poc.get_stats(traffic_item,'loss_ms')
            #kpidict['.'.join([kpi,traffic_item])] = loss_ms
            if ixia_poc.get_stats(traffic_item,'rx') > ixia_poc.get_stats(traffic_item,'tx'):
                log_file.error("Phase 3: Traffic item %s Rx > Tx !" %(traffic_item))
                phase_3_result = 'FAIL'
            else:
                loss_ms = ixia_poc.get_stats(traffic_item,'loss_ms')
                kpidict['.'.join([kpi,traffic_item])] = loss_ms
                if loss_ms > 0:
                    log_file.info("Phase 3: Traffic item %s Loss Detected" %(traffic_item))
                    phase_3_result = 'DRILL'
                    drill_down_names.append(traffic_item)
                else:
                    log_file.info("Phase 3: Traffic item %s No Loss Detected" %(traffic_item))

            test_result_dict[key] = loss_ms 

        if phase_3_result == 'PASS':
            log_file.info("")
            log_file.info("--------------------------------------------------")
            log_file.info("Phase 3: Pass") 
            log_file.info("--------------------------------------------------")
        else:
            log_file.info("")
            log_file.info("--------------------------------------------------------------")
            log_file.info("Drill Down per source / destination pair for error streams")
            log_file.info("--------------------------------------------------------------")
            for drill_down_name in drill_down_names:
                log_file.info("")
                # Polling ixia too quickly gives result from last poll
                time.sleep(10)
                ixia_poc.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 5000 
                else:
                    loss_threshold_ms = 3000 
                if not (ixia_poc.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
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
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 4: Recover Failure")
        log_file.info("--------------------------------------------------")
        log_file.info("")

        if topology == 'NG_POC':
            log_file.info("Return to defaults here")

    end_time = datetime.now()
    test_dur = end_time - start_time
    test_dur_sec = test_dur.total_seconds()

    if set_up_result == 'FAIL':
        test_result = 'FAIL'
    if phase_1_result == 'FAIL':
        test_result = 'FAIL'
    if phase_2_result == 'FAIL':
        test_result = 'FAIL'
    if phase_3_result == 'FAIL':
        test_result = 'FAIL'
    if phase_4_result == 'FAIL':
        test_result = 'FAIL'

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
    #test_result_list.append(test_result_dict)
    #Allan
    #if topology != 'NG_CRAN_NO_OFF':
        #test_result_list.append(kpidict)

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
    return edn_check 


def check_sr1_edn_ready(edn_routes, wait_min):

    count       = 0
    edn_results = {} 

    log_file.info('Wait up to %s MINUTES for EDN to be ready' %(wait_min))

    testbed_data['mls_1'].send_cli_command('/clear router 4 vrrp interface "SR1-CRAN-Hubs-BBU-OAM" ', see_return=True)

    while count <= wait_min:
        edn_check = True 
        edn_results['mls_1_down'] = testbed_data['mls_1'].send_cli_command('show router 4 interface | match SR1-CRAN-Hub | match "Down/Down" | count ', see_return=True)

        edn_results['mls_2_up']   = testbed_data['mls_2'].send_cli_command('show router 4 interface | match SR1-CRAN-Hub | match "Down/Up" | count ', see_return=True)

        for key, value in edn_results.iteritems():
            val_1 = value[1].split('Count')
            val_2 = val_1[1].split('lines')
            val_3 = val_2[0]
            val_4 = val_3.replace(' ', '')
            val_5 = val_4.replace(':','')
            edn_results[key] = int(val_5)

        log_file.info("MLS 1 VPRN 4 : # of down SR1-CRAN-Hubs-BBU-OAM interfaces  = %s | expecting %s "  %(edn_results['mls_1_down'],edn_routes))
        log_file.info("MLS 2 VPRN 4 : # of up SR1-CRAN-Hubs-BBU-OAM interfaces    = %s | expecting %s " %(edn_results['mls_2_up'],edn_routes))

        #if edn_results['mls_1_down'] != edn_routes:
        if edn_results['mls_1_down'] != 2:
            edn_check = False 
        if edn_results['mls_2_up'] != edn_routes :
            edn_check = False 

        if edn_check:
            log_file.info('SR1 EDN ready')
            return edn_check
        else:
            log_file.info('SR1 EDN not ready ... wait 60s before trying again')
            count +=1
            time.sleep(60)

    log_file.error('EDN not ready')
    return edn_check 
def check_all_ports_oper_up (testbed_nodes):

    port_result             = 'OK'

    for nx in testbed_nodes.keys():
        for px in testbed_nodes[nx].port_dict.keys() :
            port_oper_status  = testbed_nodes[nx].port_dict[px].get_port_info('oper', verbose='FALSE')
            if port_oper_status == 'down':
                log_file.error("Node %s Port %s is oper down" %(nx,px))
                port_result   = 'ERROR'
            else:
                log_file.info("Node %s Port %s is oper up" %(nx,px))

    return port_result


def wait_all_ports_oper_up (testbed_nodes,wait):

    port_result             = 'OK'
    count = 0

    log_file.info("Wait up to %s seconds for all testbed ports to come oper up" %(wait))
    while count <= wait:
        port_result = 'OK'
        for nx in testbed_nodes.keys():
            for px in testbed_nodes[nx].port_dict.keys() :
                port_oper_status  = testbed_nodes[nx].port_dict[px].get_port_info('oper', verbose='FALSE')
                if port_oper_status == 'down':
                    port_result   = 'ERROR'
        if port_result == 'OK':
            log_file.info("All Port Oper Up After %s seconds" %(count))
            break
        else:
            count +=1
            time.sleep(1)



def bring_all_ports_admin_up (testbed_nodes):

    port_result = 'OK'
    lag_result  = 'OK'
    result      = 'OK'

    for nx in testbed_nodes.keys():
        for px in testbed_nodes[nx].port_dict.keys() :
            if (testbed_nodes[nx].port_dict[px].set_port_info('admin', 'up')) == 'ERROR':
                port_result = 'ERROR'
               
            if 'lag' in testbed_nodes[nx].port_dict[px].port:
                lag_port_list = testbed_nodes[nx].port_dict[px].port_dict
                for lag_port in lag_port_list:
                    if (testbed_nodes[nx].port_dict[px].port_dict[lag_port].set_port_info('admin', 'up') == 'ERROR'):
                        lag_result = 'ERROR'

    if port_result == 'ERROR' or lag_result == 'ERROR':
        result = 'ERROR'

    return result


def clear_all_port_stats(testbed_nodes):

    log_file.info("Clear stats on all testbed ports")
    for nx in testbed_nodes.keys():
        for px in testbed_nodes[nx].port_dict.keys() :
            if 'lag' in testbed_nodes[nx].port_dict[px].port:
                lag_port_list = testbed_nodes[nx].port_dict[px].port_dict
                for lag_port in lag_port_list:
                    #log_file.info("Clear stats on node %s port %s" %(nx,px))
                    testbed_nodes[nx].port_dict[px].port_dict[lag_port].clear_stats()
            else:
                testbed_nodes[nx].port_dict[px].clear_stats()
                #log_file.info("Clear stats on node %s port %s" %(nx,px))


def shutdown_all_log_98(testbed_nodes):
    log_file.info("Shutdown log 98 on all testbed nodes to keep the NSP alarm log quiet")
    for nx in testbed_nodes.keys():
        testbed_nodes[nx].shutdown_log_98()

def no_shutdown_all_log_98(testbed_nodes):
    log_file.info("No shutdown log 98 on all testbed nodes")
    for nx in testbed_nodes.keys():
        testbed_nodes[nx].no_shutdown_log_98()


def show_all_port_util(testbed_nodes):

    log_file.info("---------------------------------------------------------------------------------------")
    log_file.info("Node       Port Name                      Port       In Lag     Speed (Gbps)  Tx%    Rx%")
    log_file.info("---------------------------------------------------------------------------------------")

    log_fmt = '{:<10} {:<30} {:<10} {:<10} {:<13} {:<6} {:<6}'
    for nx in sorted(testbed_nodes.keys()):
        if 'wbx_' not in nx:
            log_file.info("")
            my_node = testbed_nodes[nx]
            for px in sorted(my_node.port_dict.keys()):
                if '_lag_port_' not in px:
                    my_port = my_node.port_dict[px]
                    if isinstance(my_port, node.Lag):
                        na = 'N/A'
                        my_lag = my_port.port
                        t_test = my_port.get_util_perc('tx')
                        r_test = my_port.get_util_perc('rx')
                        speed = (float(my_port.get_port_speed_bps()/1000000000))
                        log_file.info(log_fmt.format(nx, my_port.name, my_port.port,na,speed,t_test,r_test))
                        lag_port_list = my_port.port_dict
                        for lag_port in lag_port_list:
                            t_test = my_port.port_dict[lag_port].get_util_perc('tx')
                            r_test = my_port.port_dict[lag_port].get_util_perc('rx')
                            speed = (float(my_port.port_dict[lag_port].get_port_speed_bps()/1000000000))
                            log_file.info(log_fmt.format(nx,my_port.port_dict[lag_port].name, my_port.port_dict[lag_port].port,my_lag,speed,t_test,r_test))
                        log_file.info("")
                    else:
                        print "it's a port"
            

def set_all_port_ether_stats_itvl(testbed_nodes,itvl=300):

    log_file.info("Set util-stats-interval on all testbed ports to %s seconds" %(itvl))
    for nx in sorted(testbed_nodes.keys()):
        if 'wbx_' not in nx:
            my_node = testbed_nodes[nx]
            for px in my_node.port_dict.keys():
                my_port = my_node.port_dict[px]
                if isinstance(my_port, node.Port):
                    my_port.set_ether_stats_interval(itvl)

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



def force_traffic_through_mls(mls_1,mls_2,force,testbed_nodes,topology):

    if force == 'to_mls_1':
        log_file.info("Force Traffic through MLS 1")
        log_file.info("Shutdown MLS 2 port to CRS")
        mls_2.to_crs.set_port_info('admin','down')
        log_file.info("Shutdown MLS 1 port to MLS 2")
        mls_1.to_mls_2.set_port_info('admin','down')
        utils.countdown(10)
        show_topo(testbed_nodes,topology = topology)
    elif force == 'to_mls_2':
        log_file.info("Force Traffic through MLS 2")
        log_file.info("Shutdown MLS 1 port to CRS")
        mls_1.to_crs.set_port_info('admin','down')
        log_file.info("Shutdown MLS 2 port to MLS 1")
        mls_2.to_mls_1.set_port_info('admin','down')
        utils.countdown(10)
        show_topo(testbed_nodes,topology = topology)
    elif force == 'none':
        log_file.info("No MLS force")
    else:
        log_file.error("Invalid Force Option in <force_traffic_through_mls>")


def restore_mls_ports(mls_1,mls_2):

    mls_2.to_crs.set_port_info('admin','up')
    mls_1.to_mls_2.set_port_info('admin','up')
    mls_1.to_crs.set_port_info('admin','up')
    mls_2.to_mls_1.set_port_info('admin','up')


def set_mode_mls_bg(mls_1, mls_2, off_1, off_2, hub_1, hub_2):


    log_file.info('Put testbed in Mode: MLS + BG traffic')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_hub_1.shutdown(snmp=True)

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_hub_2.shutdown(snmp=True)
    mls_2.to_hub_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_hub_1.shutdown(snmp=True)

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_hub_2.shutdown(snmp=True)

    hub_1.iom_to_mls_1.no_shutdown()
    hub_1.mda_to_mls_1.no_shutdown()
    hub_1.to_off_1.shutdown(snmp=True)
    hub_1.to_mls_1.shutdown(snmp=True)
    hub_1.to_hub_2.shutdown(snmp=True)

    hub_2.to_off_2.shutdown(snmp=True)
    hub_2.to_mls_2.shutdown(snmp=True)
    hub_2.to_hub_3.shutdown(snmp=True)

    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1" no shutdown')
    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1-IPv6" no shutdown')

    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2" no shutdown')
    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2-IPv6" no shutdown')

    mls_1.ran_vprn.shutdown()
    mls_2.ran_vprn.shutdown()
   
def check_mode_mls_bg(mls_1, mls_2, off_1, off_2, hub_1, hub_2):

    result = 'OK'

    log_file.info('Check testbed is in Mode: MLS + BG traffic')
     
    if (mls_1.to_crs.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (mls_1.to_off_1.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (mls_1.to_mls_2.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (mls_1.to_hub_1.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'

    if (mls_2.to_crs.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (mls_2.to_off_2.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (mls_2.to_mls_1.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (mls_2.to_hub_2.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'
    if (mls_2.to_hub_6.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'

    if (off_1.to_mls_1.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (off_1.to_hub_1.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'

    if (off_2.to_mls_2.wait_port_oper_up(120) != 'OK'):
        result == 'ERROR'
    if (off_2.to_hub_2.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'

    if (hub_1.to_off_1.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'
    if (hub_1.to_mls_1.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'
    if (hub_1.to_hub_2.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'

    if (hub_2.to_off_2.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'
    if (hub_2.to_mls_2.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'
    if (hub_2.to_hub_3.wait_port_oper_down(10) != 'OK'):
        result == 'ERROR'

    return result


def set_mode_hub_with_offload():


    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    log_file.info('Put testbed in Mode: CRAN Hub with Offload')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_hub_1.shutdown(snmp=True)

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_hub_2.shutdown(snmp=True)

    mls_2.to_hub_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_hub_1.no_shutdown(snmp=True)
    off_1.to_hub_1.no_shutdown_all_lag_members()

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_hub_2.no_shutdown(snmp=True)
    off_2.to_hub_2.no_shutdown_all_lag_members()

    hub_1.iom_to_mls_1.no_shutdown()
    hub_1.mda_to_mls_1.no_shutdown()
    hub_1.to_off_1.no_shutdown(snmp=True)
    hub_1.to_off_1.no_shutdown_all_lag_members()

    hub_1.to_mls_1.shutdown(snmp=True)
    hub_1.to_hub_2.no_shutdown(snmp=True)
    hub_1.to_hub_2.no_shutdown_all_lag_members()

    hub_2.to_off_2.no_shutdown(snmp=True)
    hub_2.to_off_2.no_shutdown_all_lag_members()
    hub_2.to_mls_2.shutdown(snmp=True)
    hub_2.to_hub_3.shutdown(snmp=True)
    hub_2.to_hub_1.no_shutdown(snmp=True)
    hub_2.to_hub_1.no_shutdown_all_lag_members()

    off_1.off_vpls.no_shutdown()
    off_2.off_vpls.no_shutdown()

    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1" no shutdown')
    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1-IPv6" no shutdown')

    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2" no shutdown')
    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2-IPv6" no shutdown')

    mls_1.ran_vprn.shutdown()
    mls_2.ran_vprn.shutdown()


def check_mode_hub_with_offload():

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    result = True

    log_file.info('Check testbed is in Mode: CRAN Hub with Offload')

    if not mls_1.to_crs.wait_port_oper_up_ex(120): result = False
    if not mls_1.to_off_1.wait_port_oper_up_ex(120): result = False
    if not mls_1.to_mls_2.wait_port_oper_up_ex(120): result = False
    if not mls_1.to_hub_1.wait_port_oper_down_ex(10): result = False

    if not mls_2.to_crs.wait_port_oper_up_ex(120): result = False
    if not mls_2.to_off_2.wait_port_oper_up_ex(120): result = False
    if not mls_2.to_mls_1.wait_port_oper_up_ex(120): result = False
    if not mls_2.to_hub_2.wait_port_oper_down_ex(10): result = False
    if not mls_2.to_hub_6.wait_port_oper_down_ex(10): result = False

    if not off_1.to_mls_1.wait_port_oper_up_ex(120): result = False
    if not off_1.to_hub_1.wait_port_oper_up_ex(120): result = False

    if not off_2.to_mls_2.wait_port_oper_up_ex(120): result = False
    if not off_2.to_hub_2.wait_port_oper_up_ex(120): result = False

    if not hub_1.to_off_1.wait_port_oper_up_ex(120): result = False
    if not hub_1.to_mls_1.wait_port_oper_down_ex(10): result = False
    if not hub_1.to_hub_2.wait_port_oper_up_ex(120): result = False

    if not hub_2.to_hub_1.wait_port_oper_up_ex(120): result = False
    if not hub_2.to_off_2.wait_port_oper_up_ex(120): result = False
    if not hub_2.to_mls_2.wait_port_oper_down_ex(10): result = False
    if not hub_2.to_hub_3.wait_port_oper_down_ex(10): result = False

    if not mls_1.to_crs.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_off_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_crs.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_off_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not off_1.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not off_1.to_hub_1.wait_all_lag_members_oper_up(120): result = False
    if not off_2.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not off_2.to_hub_2.wait_all_lag_members_oper_up(120): result = False
    if not hub_1.to_off_1.wait_all_lag_members_oper_up(120): result = False
    if not hub_2.to_off_2.wait_all_lag_members_oper_up(120): result = False
    if not hub_1.to_hub_2.wait_all_lag_members_oper_up(120): result = False


    return result

def set_mode_hub_no_offload():

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']


    log_file.info('Put testbed in Mode: CRAN Hub no Offload')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_hub_1.no_shutdown(snmp=True)
    mls_1.to_hub_1.no_shutdown_all_lag_members()

    mls_1.to_sr1_hub_1_10.shutdown(snmp=True)
    mls_1.to_sr1_hub_1_10.shutdown_all_lag_members()

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_hub_2.no_shutdown(snmp=True)
    mls_2.to_hub_2.no_shutdown_all_lag_members()

    mls_2.to_sr1_hub_2_10.shutdown(snmp=True)
    mls_2.to_sr1_hub_2_10.shutdown_all_lag_members()

    mls_2.to_hub_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_hub_1.shutdown(snmp=True)

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_hub_2.shutdown(snmp=True)

    hub_1.to_off_1.shutdown(snmp=True)

    hub_1.iom_to_mls_1.no_shutdown()
    hub_1.mda_to_mls_1.no_shutdown()
    hub_1.to_mls_1.no_shutdown(snmp=True)
    hub_1.to_mls_1.no_shutdown_all_lag_members()

    hub_1.to_hub_2.no_shutdown(snmp=True)
    hub_1.to_hub_2.no_shutdown_all_lag_members()

    hub_2.to_hub_1.no_shutdown(snmp=True)
    hub_2.to_hub_1.no_shutdown_all_lag_members()

    hub_2.to_off_2.shutdown(snmp=True)

    hub_2.to_mls_2.no_shutdown(snmp=True)
    hub_2.to_mls_2.no_shutdown_all_lag_members()

    hub_2.to_hub_3.shutdown(snmp=True)

    off_1.off_vpls.no_shutdown()
    off_2.off_vpls.no_shutdown()

    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1" no shutdown')
    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1-IPv6" no shutdown')

    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2" no shutdown')
    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2-IPv6" no shutdown')


    mls_1.ran_vprn.shutdown()
    mls_2.ran_vprn.shutdown()

    wbx_89.to_sr1_hub_1_10.shutdown(snmp=True)
    wbx_89.to_sr1_hub_1_10.shutdown_all_lag_members()
    wbx_89.to_sr1_hub_2_10.shutdown(snmp=True)
    wbx_89.to_sr1_hub_2_10.shutdown_all_lag_members()

    wbx_89.to_hub_1.no_shutdown(snmp=True)
    wbx_89.to_hub_1.no_shutdown_all_lag_members()

    wbx_98.to_hub_2.no_shutdown(snmp=True)
    wbx_98.to_hub_2.no_shutdown_all_lag_members()


def check_mode_hub_no_offload():

    result = True 

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    if not mls_1.to_crs.wait_port_oper_up_ex(120):   result = False 
    if not mls_1.to_off_1.wait_port_oper_up_ex(120): result = False
    if not mls_1.to_mls_2.wait_port_oper_up_ex(120): result = False
    if not mls_1.to_hub_1.wait_port_oper_up_ex(120): result = False

    if not mls_2.to_crs.wait_port_oper_up_ex(120):    result = False
    if not mls_2.to_off_2.wait_port_oper_up_ex(120):  result = False
    if not mls_2.to_mls_1.wait_port_oper_up_ex(120):  result = False
    if not mls_2.to_hub_2.wait_port_oper_up_ex(120):  result = False
    if not mls_2.to_hub_6.wait_port_oper_down_ex(10): result = False

    if not off_1.to_mls_1.wait_port_oper_up_ex(120):   result = False
    if not off_1.to_hub_1.wait_port_oper_down_ex(10): result = False

    if not off_2.to_mls_2.wait_port_oper_up_ex(120):   result = False
    if not off_2.to_hub_2.wait_port_oper_down_ex(10): result = False

    if not hub_1.to_off_1.wait_port_oper_down_ex(10): result = False
    if not hub_1.to_mls_1.wait_port_oper_up_ex(120): result = False
    if not hub_1.to_hub_2.wait_port_oper_up_ex(120): result = False

    if not hub_2.to_off_2.wait_port_oper_down(10): result = False
    if not hub_2.to_mls_2.wait_port_oper_up(120): result = False
    if not hub_2.to_hub_3.wait_port_oper_down(10): result = False
    if not hub_2.to_hub_1.wait_port_oper_up(120): result = False

    if not mls_1.to_crs.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_off_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_hub_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_crs.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_off_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_hub_2.wait_all_lag_members_oper_up(120): result = False
    if not off_1.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not off_2.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not hub_1.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not hub_1.to_hub_2.wait_all_lag_members_oper_up(120): result = False
    if not hub_2.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not hub_2.to_hub_1.wait_all_lag_members_oper_up(120): result = False

    return result


def set_mode_ng_hub_no_offload():

    el_1 = testbed_data['el_1']
    el_2 = testbed_data['el_2']

    wbx_spine_1 = testbed_data['wbx_spine_2']
    wbx_spine_2 = testbed_data['wbx_spine_2']

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    sr1_hub_1 = testbed_data['sr1_hub_1']
    sr1_hub_2 = testbed_data['sr1_hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    log_file.info('Put testbed in Mode: Next Gen CRAN Hub no Offload')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_hub_1.no_shutdown(snmp=True)
    mls_1.to_hub_1.no_shutdown_all_lag_members()

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_hub_2.no_shutdown(snmp=True)
    mls_2.to_hub_2.no_shutdown_all_lag_members()

    mls_2.to_hub_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_hub_1.shutdown(snmp=True)

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_hub_2.shutdown(snmp=True)

    hub_1.to_off_1.shutdown(snmp=True)

    hub_1.iom_to_mls_1.no_shutdown()
    hub_1.mda_to_mls_1.no_shutdown()
    hub_1.to_mls_1.no_shutdown(snmp=True)
    hub_1.to_mls_1.no_shutdown_all_lag_members()

    hub_1.to_hub_2.no_shutdown(snmp=True)
    hub_1.to_hub_2.no_shutdown_all_lag_members()

    hub_2.to_hub_1.no_shutdown(snmp=True)
    hub_2.to_hub_1.no_shutdown_all_lag_members()

    hub_2.to_off_2.shutdown(snmp=True)

    hub_2.to_mls_2.no_shutdown(snmp=True)
    hub_2.to_mls_2.no_shutdown_all_lag_members()

    hub_2.to_hub_3.shutdown(snmp=True)

    off_1.off_vpls.no_shutdown()
    off_2.off_vpls.no_shutdown()

    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1" shutdown')
    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1-IPv6" shutdown')

    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2" shutdown')
    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2-IPv6" shutdown')

    # NG node specific
    el_1.to_crs.no_shutdown(snmp=True)
    el_1.to_el_2.no_shutdown(snmp=True)
    el_1.to_wbx_spine_1.no_shutdown(snmp=True)
    el_1.to_wbx_spine_2.no_shutdown(snmp=True)
    el_1.ran_vprn.no_shutdown()

    el_2.to_crs.no_shutdown(snmp=True)
    el_2.to_el_1.no_shutdown(snmp=True)
    el_2.to_wbx_spine_1.no_shutdown(snmp=True)
    el_2.to_wbx_spine_2.no_shutdown(snmp=True)
    el_2.ran_vprn.no_shutdown()

    wbx_spine_1.to_el_1.no_shutdown(snmp=True)
    wbx_spine_1.to_el_2.no_shutdown(snmp=True)
    wbx_spine_1.to_mls_1.no_shutdown(snmp=True)
    wbx_spine_1.to_mls_2.no_shutdown(snmp=True)

    wbx_spine_2.to_el_1.no_shutdown(snmp=True)
    wbx_spine_2.to_el_2.no_shutdown(snmp=True)
    wbx_spine_2.to_mls_1.no_shutdown(snmp=True)
    wbx_spine_2.to_mls_2.no_shutdown(snmp=True)

    mls_1.to_wbx_spine_1.no_shutdown(snmp=True)
    mls_1.to_wbx_spine_2.no_shutdown(snmp=True)
    mls_1.ran_vprn.no_shutdown()

    mls_2.to_wbx_spine_1.no_shutdown(snmp=True)
    mls_2.to_wbx_spine_2.no_shutdown(snmp=True)
    mls_2.ran_vprn.no_shutdown()


def check_mode_ng_hub_no_offload():

    el_1 = testbed_data['el_1']
    el_2 = testbed_data['el_2']

    wbx_spine_1 = testbed_data['wbx_spine_2']
    wbx_spine_2 = testbed_data['wbx_spine_2']

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    sr1_hub_1 = testbed_data['sr1_hub_1']
    sr1_hub_2 = testbed_data['sr1_hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    result = True 

    #NG 
    if not (el_1.to_crs.wait_port_oper_up_ex(120)): result  = False 
    if not (el_1.to_el_2.wait_port_oper_up_ex(120)): result = False 
    if not (el_1.to_wbx_spine_1.wait_port_oper_up_ex(120)): result = False 

    if not (el_2.to_crs.wait_port_oper_up_ex(120)): result = False 
    if not (el_2.to_el_1.wait_port_oper_up_ex(120)): result = False 
    if not (el_2.to_wbx_spine_1.wait_port_oper_up_ex(120)): result = False 

    if not (wbx_spine_1.to_el_1.wait_port_oper_up_ex(120)): result = False 
    if not (wbx_spine_1.to_el_2.wait_port_oper_up_ex(120)): result = False 
    if not (wbx_spine_1.to_mls_1.wait_port_oper_up_ex(120)): result = False 
    if not (wbx_spine_1.to_mls_2.wait_port_oper_up_ex(120)): result = False 

    if not (wbx_spine_2.to_el_1.wait_port_oper_up_ex(120)): result = False 
    if not (wbx_spine_2.to_el_2.wait_port_oper_up_ex(120)): result = False 
    if not (wbx_spine_2.to_mls_1.wait_port_oper_up_ex(120)): result = False 
    if not (wbx_spine_2.to_mls_2.wait_port_oper_up_ex(120)): result = False 

    if not (mls_1.to_wbx_spine_1.wait_port_oper_up_ex(120)): result = False 
    if not (mls_2.to_wbx_spine_1.wait_port_oper_up_ex(120)): result = False 

    if not (mls_1.to_crs.wait_port_oper_up_ex(120)): result   = False 
    if not (mls_1.to_off_1.wait_port_oper_up_ex(120)): result = False 
    if not (mls_1.to_mls_2.wait_port_oper_up_ex(120)): result = False
    if not (mls_1.to_hub_1.wait_port_oper_up_ex(120)): result = False

    if not (mls_2.to_crs.wait_port_oper_up_ex(120)): result    = False
    if not (mls_2.to_off_2.wait_port_oper_up_ex(120)): result  = False
    if not (mls_2.to_mls_1.wait_port_oper_up_ex(120)): result  = False
    if not (mls_2.to_hub_2.wait_port_oper_up_ex(120)): result  = False
    if not (mls_2.to_hub_6.wait_port_oper_down_ex(10)): result = False

    if not (off_1.to_mls_1.wait_port_oper_up_ex(120)): result  = False
    if not (off_1.to_hub_1.wait_port_oper_down_ex(10)): result = False

    if not (off_2.to_mls_2.wait_port_oper_up_ex(120)): result  = False
    if not (off_2.to_hub_2.wait_port_oper_down_ex(10)): result = False

    if not (hub_1.to_off_1.wait_port_oper_down_ex(10)): result = False
    if not (hub_1.to_mls_1.wait_port_oper_up_ex(120)): result  = False
    if not (hub_1.to_hub_2.wait_port_oper_up_ex(120)): result  = False

    if not (hub_2.to_off_2.wait_port_oper_down_ex(10)): result = False
    if not (hub_2.to_mls_2.wait_port_oper_up_ex(120)): result  = False
    if not (hub_2.to_hub_3.wait_port_oper_down_ex(10)): result = False
    if not (hub_2.to_hub_1.wait_port_oper_up_ex(120)): result  = False

    if not mls_1.to_crs.wait_all_lag_members_oper_up(120): result   = False
    if not mls_1.to_off_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_hub_1.wait_all_lag_members_oper_up(120): result = False

    if not mls_2.to_crs.wait_all_lag_members_oper_up(120): result   = False
    if not mls_2.to_off_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_hub_2.wait_all_lag_members_oper_up(120): result = False

    if not off_1.to_mls_1.wait_all_lag_members_oper_up(120): result = False

    if not off_2.to_mls_2.wait_all_lag_members_oper_up(120): result = False

    if not hub_1.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not hub_1.to_hub_2.wait_all_lag_members_oper_up(120): result = False

    if not hub_2.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not hub_2.to_hub_1.wait_all_lag_members_oper_up(120): result = False

    return result

def set_mode_sr1_hub_no_offload():

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    sr1_hub_1 = testbed_data['sr1_hub_1']
    sr1_hub_2 = testbed_data['sr1_hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    log_file.info('Put testbed in Mode: SR1 CRAN Hub no Offload')

    mls_1.to_crs.no_shutdown(snmp=True)

    mls_1.to_mls_2.no_shutdown(snmp=True)
    mls_1.to_mls_2.no_shutdown_all_lag_members()

    mls_1.to_off_1.no_shutdown(snmp=True)
    mls_1.to_off_1.no_shutdown_all_lag_members()

    mls_1.to_hub_1.shutdown(snmp=True)
    mls_1.to_hub_1.shutdown_all_lag_members()

    mls_1.to_sr1_hub_1_10.no_shutdown(snmp=True)
    mls_1.to_sr1_hub_1_10.no_shutdown_all_lag_members()

    mls_2.to_crs.no_shutdown(snmp=True)

    mls_2.to_mls_1.no_shutdown(snmp=True)
    mls_2.to_mls_1.no_shutdown_all_lag_members()

    mls_2.to_off_2.no_shutdown(snmp=True)
    mls_2.to_off_2.no_shutdown_all_lag_members()

    mls_2.to_hub_2.shutdown(snmp=True)
    mls_2.to_hub_2.shutdown_all_lag_members()

    #Allan
    mls_2.to_sr1_hub_2_10.no_shutdown(snmp=True)
    mls_2.to_sr1_hub_2_10.no_shutdown_all_lag_members()

    mls_2.to_hub_6.shutdown(snmp=True)

    off_1.to_mls_1.no_shutdown(snmp=True)
    off_1.to_mls_1.no_shutdown_all_lag_members()

    off_1.to_hub_1.shutdown(snmp=True)

    off_2.to_mls_2.no_shutdown(snmp=True)
    off_2.to_mls_2.no_shutdown_all_lag_members()

    off_2.to_hub_2.shutdown(snmp=True)

    hub_1.to_off_1.shutdown(snmp=True)

    hub_1.iom_to_mls_1.no_shutdown()
    hub_1.mda_to_mls_1.no_shutdown()

    hub_1.to_mls_1.shutdown(snmp=True)
    hub_1.to_mls_1.shutdown_all_lag_members()

    sr1_hub_1.to_mls_1_10.no_shutdown(snmp=True)
    sr1_hub_1.to_mls_1_10.no_shutdown_all_lag_members()

    hub_1.to_hub_2.shutdown(snmp=True)
    hub_1.to_hub_2.shutdown_all_lag_members()

    hub_2.to_hub_1.shutdown(snmp=True)
    hub_2.to_hub_1.shutdown_all_lag_members()

    sr1_hub_1.to_sr1_hub_2_10.no_shutdown(snmp=True)
    sr1_hub_1.to_sr1_hub_2_10.no_shutdown_all_lag_members()

    sr1_hub_2.to_sr1_hub_1_10.no_shutdown(snmp=True)
    sr1_hub_2.to_sr1_hub_1_10.no_shutdown_all_lag_members()

    hub_2.to_off_2.shutdown(snmp=True)

    hub_2.to_mls_2.shutdown(snmp=True)
    hub_2.to_mls_2.shutdown_all_lag_members()

    sr1_hub_2.to_mls_2_10.no_shutdown(snmp=True)
    sr1_hub_2.to_mls_2_10.no_shutdown_all_lag_members()

    hub_2.to_hub_3.shutdown(snmp=True)

    off_1.off_vpls.no_shutdown()
    off_2.off_vpls.no_shutdown()

    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1" no shutdown')
    mls_1.send_cli_command('/configure service ies 20 interface "MLS1-to-CRS-1-IPv6" no shutdown')

    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2" no shutdown')
    mls_2.send_cli_command('/configure service ies 20 interface "MLS2-to-CRS-2-IPv6" no shutdown')


    mls_1.ran_vprn.shutdown()
    mls_2.ran_vprn.shutdown()

    wbx_89.to_sr1_hub_1_10.no_shutdown(snmp=True)
    wbx_89.to_sr1_hub_1_10.no_shutdown_all_lag_members()
    wbx_89.to_sr1_hub_2_10.no_shutdown(snmp=True)
    wbx_89.to_sr1_hub_2_10.no_shutdown_all_lag_members()

    wbx_89.to_hub_1.shutdown(snmp=True)
    wbx_89.to_hub_1.shutdown_all_lag_members()

    wbx_98.to_hub_2.shutdown(snmp=True)
    wbx_98.to_hub_2.shutdown_all_lag_members()


def check_mode_sr1_hub_no_offload():

    result = True

    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    sr1_hub_1 = testbed_data['sr1_hub_1']
    sr1_hub_2 = testbed_data['sr1_hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    if not mls_1.to_crs.wait_port_oper_up_ex(120):            result = False 
    if not mls_1.to_off_1.wait_port_oper_up_ex(120):          result = False 
    if not mls_1.to_mls_2.wait_port_oper_up_ex(120):          result = False
    if not mls_1.to_hub_1.wait_port_oper_down_ex(120):        result = False
    if not mls_1.to_sr1_hub_1_10.wait_port_oper_up_ex(120):   result = False
    if not mls_1.to_sr1_hub_1_100.wait_port_oper_down_ex(10): result = False

    if not mls_2.to_crs.wait_port_oper_up_ex(120):            result = False 
    if not mls_2.to_off_2.wait_port_oper_up_ex(120):          result = False 
    if not mls_2.to_mls_1.wait_port_oper_up_ex(120):          result = False
    if not mls_2.to_hub_2.wait_port_oper_down_ex(120):        result = False
    if not mls_2.to_hub_6.wait_port_oper_down_ex(120):        result = False
    if not mls_2.to_sr1_hub_2_10.wait_port_oper_up_ex(120):   result = False
    if not mls_2.to_sr1_hub_2_100.wait_port_oper_down_ex(10): result = False


    if not off_1.to_mls_1.wait_port_oper_up_ex(120):  result = False
    if not off_1.to_hub_1.wait_port_oper_down_ex(10): result = False

    if not off_2.to_mls_2.wait_port_oper_up_ex(120):  result = False
    if not off_2.to_hub_2.wait_port_oper_down_ex(10): result = False


    if not hub_1.to_off_1.wait_port_oper_down_ex(10):  result = False
    if not hub_1.to_mls_1.wait_port_oper_down_ex(120): result = False
    if not hub_1.to_hub_2.wait_port_oper_down_ex(120): result = False

    if not sr1_hub_1.to_mls_1_10.wait_port_oper_up_ex(120): result = False
    if not sr1_hub_1.to_sr1_hub_2_10.wait_port_oper_up_ex(120): result = False

    if not hub_2.to_off_2.wait_port_oper_down_ex(10): result = False
    if not hub_2.to_mls_2.wait_port_oper_down_ex(10):  result = False
    if not hub_2.to_hub_3.wait_port_oper_down_ex(10): result = False
    if not hub_2.to_hub_1.wait_port_oper_down_ex(120):  result = False

    if not mls_1.to_crs.wait_all_lag_members_oper_up(120):   result = False
    if not mls_1.to_off_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_mls_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_1.to_sr1_hub_1_10.wait_all_lag_members_oper_up(120): result = False

    if not mls_2.to_crs.wait_all_lag_members_oper_up(120):   result = False
    if not mls_2.to_off_2.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not mls_2.to_sr1_hub_2_10.wait_all_lag_members_oper_up(120): result = False

    if not off_1.to_mls_1.wait_all_lag_members_oper_up(120): result = False
    if not off_2.to_mls_2.wait_all_lag_members_oper_up(120): result = False

    if not sr1_hub_1.to_mls_1_10.wait_all_lag_members_oper_up(120): result = False
    if not sr1_hub_1.to_sr1_hub_2_10.wait_all_lag_members_oper_up(120): result = False
    if not sr1_hub_2.to_mls_2_10.wait_all_lag_members_oper_up(120): result = False
    if not sr1_hub_2.to_sr1_hub_1_10.wait_all_lag_members_oper_up(120): result = False

    if not wbx_89.to_sr1_hub_1_10.wait_port_oper_up_ex(120):  result = False
    if not wbx_89.to_sr1_hub_1_10.wait_all_lag_members_oper_up(120):  result = False

    if not wbx_89.to_sr1_hub_2_10.wait_port_oper_up_ex(120):  result = False
    if not wbx_89.to_sr1_hub_2_10.wait_all_lag_members_oper_up(120):  result = False

    if not wbx_89.to_hub_1.wait_port_oper_down_ex(10): result = False
    if not wbx_98.to_hub_2.wait_port_oper_down_ex(10): result = False


    return result

def check_all_admin_saves(mls_1,mls_2,hub_1,hub_2,wbx_89,wbx_98):

    save_result = True
    save_list = [mls_1,mls_2,hub_1,hub_2,wbx_89,wbx_98]

    for save_node in save_list:
        log_file.info("Checking admin save result on %s" %(save_node.ip))  
        if not (save_node.check_admin_save()):
            log_file.error("admin save result on %s is not OK" %(save_node.ip))  
            save_result = False
        else:
            log_file.info("admin save result on %s is OK" %(save_node.ip))  

    return save_result

def show_topo(testbed_nodes,topology):

    topo = {}
    topo['cm1'] = '|'
    topo['cm2'] = '|'
    topo['m1m2'] = '-'
    topo['m1o1'] = '|'
    topo['m2o2'] = '|'
    topo['m1h1'] = '-'
    topo['m2h2'] = '-'
    topo['o1l1'] = '-'
    topo['o1l2'] = '-'
    topo['o1l3'] = '-'
    topo['o1l4'] = '-'
    topo['o1l5'] = '-'
    topo['o2l1'] = '-'
    topo['o2l2'] = '-'
    topo['o2l3'] = '-'
    topo['o2l4'] = '-'
    topo['o2l5'] = '-'
    topo['o1h1'] = '|'
    topo['o2h2'] = '|'
    topo['h1h2'] = '-'
      
    for nx in testbed_nodes.keys():
        for px in testbed_nodes[nx].port_dict.keys() :
            port_oper_status  = testbed_nodes[nx].port_dict[px].get_port_info('oper', verbose=False)

            if port_oper_status == 'up' and type(testbed_nodes[nx].port_dict[px]).__name__ == 'Lag': 
                for lpx in testbed_nodes[nx].port_dict[px].port_dict.values():
                    if (lpx.get_port_info('oper', verbose=False)) == 'down':
                        port_oper_status = 'lag_up_port_down'

            if port_oper_status == 'down':
                if nx == 'mls_1':
                    if px == 'to_crs':
                        topo['cm1'] = 'X'
                    if px == 'to_off_1':
                        topo['m1o1'] = 'X'
                    if px == 'to_mls_2':
                       topo['m1m2'] = 'X'
                if nx == 'mls_2':
                    if px == 'to_crs':
                        topo['cm2'] = 'X'
                    if px == 'to_off_1':
                        topo['m2o2'] = 'X'
                if nx == 'off_1':
                    if px == 'to_bg_hub_1':
                        topo['o1l1'] = 'X'
                    if px == 'to_bg_hub_2':
                        topo['o1l2'] = 'X'
                    if px == 'to_bg_hub_3':
                        topo['o1l3'] = 'X'
                    if px == 'to_bg_hub_4':
                        topo['o1l4'] = 'X'
                    if px == 'to_bg_hub_5':
                        topo['o1l5'] = 'X'
                    if px == 'to_hub_1':
                        topo['o1h1'] = 'X'
                if nx == 'off_2':
                    if px == 'to_bg_hub_1':
                        topo['o2l1'] = 'X'
                    if px == 'to_bg_hub_2':
                        topo['o2l2'] = 'X'
                    if px == 'to_bg_hub_3':
                        topo['o2l3'] = 'X'
                    if px == 'to_bg_hub_4':
                        topo['o2l4'] = 'X'
                    if px == 'to_bg_hub_5':
                        topo['o2l5'] = 'X'
                    if px == 'to_hub_2':
                       topo['o2h2'] = 'X'
                if nx == 'hub_1':
                   if px == 'to_mls_1':
                       topo['m1h1'] = 'X'
                   if px == 'to_hub_2':
                       topo['h1h2'] = 'X'
                if nx == 'hub_2':
                   if px == 'to_mls_2':
                       topo['m2h2'] = 'X'
                   if px == 'to_hub_1':
                       topo['h1h2'] = 'X' 
            elif port_oper_status == 'lag_up_port_down':
                if nx == 'mls_1':
                    if px == 'to_crs':
                        topo['cm1'] = '#'
                    if px == 'to_off_1':
                        topo['m1o1'] = '#'
                    if px == 'to_mls_2':
                        topo['m1m2'] = '#'
                if nx == 'mls_2':
                    if px == 'to_crs':
                        topo['cm2'] = '#'
                    if px == 'to_off_1':
                        topo['m2o2'] = '#'
                if nx == 'off_1':
                    if px == 'to_bg_hub_1':
                        topo['o1l1'] = '#'
                    if px == 'to_bg_hub_2':
                        topo['o1l2'] = '#'
                    if px == 'to_bg_hub_3':
                        topo['o1l3'] = '#'
                    if px == 'to_bg_hub_4':
                        topo['o1l4'] = '#'
                    if px == 'to_bg_hub_5':
                        topo['o1l5'] = '#'
                    if px == 'to_hub_1':
                        topo['o1h1'] = '#'
                if nx == 'off_2':
                    if px == 'to_bg_hub_1':
                        topo['o2l1'] = '#'
                    if px == 'to_bg_hub_2':
                        topo['o2l2'] = '#'
                    if px == 'to_bg_hub_3':
                        topo['o2l3'] = '#'
                    if px == 'to_bg_hub_4':
                        topo['o2l4'] = '#'
                    if px == 'to_bg_hub_5':
                        topo['o2l5'] = '#'
                    if px == 'to_hub_2':
                       topo['o2h2'] = '#'
                if nx == 'hub_1':
                    if px == 'to_mls_1':
                        topo['m1h1'] = '#'
                    if px == 'to_hub_2':
                        topo['h1h2'] = '#'
                if nx == 'hub_2':
                    if px == 'to_mls_2':
                        topo['m2h2'] = '#'
                    if px == 'to_hub_1':
                        topo['h1h2'] = '#'
    if topology == 'MLS':
        log_file.info("")
        log_file.info("")
        log_file.info("Testbed toplogy")
        log_file.info("---------------")
        log_file.info("")
        log_file.info("Key:")
        log_file.info("----")
        log_file.info("X = port|lag is oper down")
        log_file.info("# = lag is oper up but not all member ports are")
        log_file.info("")
        log_file.info("")
        log_file.info("MLS Only Topology")
        log_file.info("----------------------")
        log_file.info("")
        log_file.info("                           Ixia                                ")
        log_file.info("                             |                                 ")
        log_file.info("                      +------+------+                          ")
        log_file.info("                      |             |                          ")
        log_file.info("                      |     CRS     |                          ")
        log_file.info("                      |             |                          ")
        log_file.info("                      +-+---------+-+                          ")
        log_file.info("                        |         |                            ")
        log_file.info("                        %s         %s                          " %(topo['cm1'],topo['cm2']))
        log_file.info("                        |         |                            ")
        log_file.info("                +-------+-+     +-+-------+                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |   MLS   +--%s--+   MLS   |                   " %(topo['m1m2']))
        log_file.info("                |    1    |     |    2    |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                +----+----+     +----+----+                    ")
        log_file.info("                     |               |                         ")
        log_file.info("                     %s               %s                       " %(topo['m1o1'],topo['m2o2']))
        log_file.info("                     |               |                         ")
        log_file.info("   +---+        +----+----+     +----+----+        +---+       ")
        log_file.info("   |   |        |         |     |         |        |   |       ")
        log_file.info("   | W +---%s----+         |     |         +----%s---+ W |     "%(topo['o1l1'],topo['o2l1']))
        log_file.info("   | B +---%s----+         |     |         +----%s---+ B |     "%(topo['o1l2'],topo['o2l2']))
        log_file.info("   | X +---%s----+   OFF   |     |   OFF   +----%s---+ X |     "%(topo['o1l3'],topo['o2l3']))
        log_file.info("   | 8 +---%s----+    1    |     |    2    +----%s---+ 9 |     "%(topo['o1l4'],topo['o2l4']))
        log_file.info("   | 9 +---%s----+         |     |         +----%s---+ 8 |     "%(topo['o1l5'],topo['o2l5']))
        log_file.info("   |   |        |         |     |         |        |   |       ")
        log_file.info("   +-+-+        +----+----+     +----+----+        +-+-+       ")
        log_file.info("     |                                               |         ")
        log_file.info("     |                                               |         ")
        log_file.info("     Ixia                                         Ixia         ")
    elif topology == 'CRAN_OFF':
        log_file.info("")
        log_file.info("")
        log_file.info("Testbed toplogy")
        log_file.info("---------------")
        log_file.info("")
        log_file.info("Key:")
        log_file.info("----")
        log_file.info("X = port|lag is oper down")
        log_file.info("# = lag is oper up but not all member ports are")
        log_file.info("")
        log_file.info("")
        log_file.info("CRAN Hubs via Offloads")
        log_file.info("----------------------")
        log_file.info("")
        log_file.info("                           Ixia                                ")
        log_file.info("                             |                                 ")
        log_file.info("                      +------+------+                          ")
        log_file.info("                      |             |                          ")
        log_file.info("                      |     CRS     |                          ")
        log_file.info("                      |             |                          ")
        log_file.info("                      +-+---------+-+                          ")
        log_file.info("                        |         |                            ")
        log_file.info("                        %s         %s                          " %(topo['cm1'],topo['cm2']))
        log_file.info("                        |         |                            ")
        log_file.info("                +-------+-+     +-+-------+                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |   MLS   +--%s--+   MLS   |                   " %(topo['m1m2']))
        log_file.info("                |    1    |     |    2    |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                +----+----+     +----+----+                    ")
        log_file.info("                     |               |                         ")
        log_file.info("                     %s               %s                       " %(topo['m1o1'],topo['m2o2']))
        log_file.info("                     |               |                         ")
        log_file.info("   +---+        +----+----+     +----+----+        +---+       ")
        log_file.info("   |   |        |         |     |         |        |   |       ")
        log_file.info("   | W +---%s----+         |     |         +----%s---+ W |     "%(topo['o1l1'],topo['o2l1']))
        log_file.info("   | B +---%s----+         |     |         +----%s---+ B |     "%(topo['o1l2'],topo['o2l2']))
        log_file.info("   | X +---%s----+   OFF   |     |   OFF   +----%s---+ X |     "%(topo['o1l3'],topo['o2l3']))
        log_file.info("   | 8 +---%s----+    1    |     |    2    +----%s---+ 9 |     "%(topo['o1l4'],topo['o2l4']))
        log_file.info("   | 9 +---%s----+         |     |         +----%s---+ 8 |     "%(topo['o1l5'],topo['o2l5']))
        log_file.info("   |   |        |         |     |         |        |   |       ")
        log_file.info("   +-+-+        +----+----+     +----+----+        +-+-+       ")
        log_file.info("     |               |               |               |         ")
        log_file.info("     |               |               |               |         ")
        log_file.info("     Ixia            %s               %s             Ixia      "%(topo['o1h1'],topo['o2h2']))
        log_file.info("                     |               |                          ")
        log_file.info("                     |               |                          ")
        log_file.info("                +---------+     +---------+                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |   HUB   +--%s--+   HUB   |                   "%(topo['h1h2']))
        log_file.info("                |    1    |     |    2    |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                +----+----+     +----+----+                    ")
        log_file.info("                     |               |                         ")
        log_file.info("                     |               |                         ")
        log_file.info("                     |               |                         ")
        log_file.info("                +----+----+     +----+----+                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |  WBX89  |     |  WBX98  |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                +-+-----+-+     +-+-----+-+                    ")
        log_file.info("                  |     |         |     |                      ")
        log_file.info("               Ixia     Ixia   Ixia     Ixia                   ")
        log_file.info(" ")
        log_file.info(" ")
    elif topology == 'CRAN_NO_OFF':
        log_file.info("")
        log_file.info("")
        log_file.info("Testbed toplogy")
        log_file.info("---------------")
        log_file.info("")
        log_file.info("Key:")
        log_file.info("----")
        log_file.info("X = port|lag is oper down")
        log_file.info("# = lag is oper up but not all member ports are")
        log_file.info("")
        log_file.info("")
        log_file.info("CRAN Hubs Bypass Offloads")
        log_file.info("-------------------------")
        log_file.info("")
        log_file.info("                           Ixia                                ")
        log_file.info("                             |                                 ")
        log_file.info("                      +------+------+                          ")
        log_file.info("                      |             |                          ")
        log_file.info("                      |     CRS     |                          ")
        log_file.info("                      |             |                          ")
        log_file.info("                      +-+---------+-+                          ")
        log_file.info("                        |         |                            ")
        log_file.info("                        %s         %s                          " %(topo['cm1'],topo['cm2']))
        log_file.info("                        |         |                            ")
        log_file.info("                +-------+-+     +-+-------+                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |   MLS   +--%s--+   MLS   |                   " %(topo['m1m2']))
        log_file.info(" +--------------+    1    |     |    2    +----------------+   ")
        log_file.info(" |              |         |     |         |                |   ")
        log_file.info(" |              +----+----+     +----+----+                |   ")
        log_file.info(" |                   |               |                     |   ")
        log_file.info(" |                   %s               %s                     | " %(topo['m1o1'],topo['m2o2']))
        log_file.info(" |                   |               |                     |   ")
        log_file.info(" | +---+        +----+----+     +----+----+        +---+   |   ")
        log_file.info(" | |   |        |         |     |         |        |   |   |   ")
        log_file.info(" | | W +---%s----+         |     |         +----%s---+ W |   | "%(topo['o1l1'],topo['o2l1']))
        log_file.info(" | | B +---%s----+         |     |         +----%s---+ B |   | "%(topo['o1l2'],topo['o2l2']))
        log_file.info(" | | X +---%s----+   OFF   |     |   OFF   +----%s---+ X |   | "%(topo['o1l3'],topo['o2l3']))
        log_file.info(" | | 8 +---%s----+    1    |     |    2    +----%s---+ 9 |   | "%(topo['o1l4'],topo['o2l4']))
        log_file.info(" | | 9 +---%s----+         |     |         +----%s---+ 8 |   | "%(topo['o1l5'],topo['o2l5']))
        log_file.info(" | |   |        |         |     |         |        |   |   |   ")
        log_file.info(" | +-+-+        +----+----+     +----+----+        +-+-+   |   ")
        log_file.info(" |   |                                               |     |   ")
        log_file.info(" |   |                                               |     |   ")
        log_file.info(" |   Ixia                                         Ixia     |   ")
        log_file.info(" |                                                         |   ")
        log_file.info(" |                                                         |   ")
        log_file.info(" |              +---------+     +---------+                |   ")
        log_file.info(" |              |         |     |         |                |   ")
        log_file.info(" |              |         |     |         |                |   ")
        log_file.info(" +-------%s------+   HUB   +--%s--+   HUB   +-----%s----------+   " %(topo['m1h1'],topo['h1h2'],topo['m2h2']))
        log_file.info("                |    1    |     |    2    |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                +----+----+     +----+----+                    ")
        log_file.info("                     |               |                         ")
        log_file.info("                     |               |                         ")
        log_file.info("                     |               |                         ")
        log_file.info("                +----+----+     +----+----+                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                |  WBX89  |     |  WBX98  |                    ")
        log_file.info("                |         |     |         |                    ")
        log_file.info("                +-+-----+-+     +-+-----+-+                    ")
        log_file.info("                  |     |         |     |                      ")
        log_file.info("               Ixia     Ixia   Ixia     Ixia                   ")
        log_file.info(" ")
        log_file.info(" ")
    else:
        log_file.info(" ")
        log_file.info(" No Diagram For This Topo")
        log_file.info(" ")


def ng_show_topo():

        log_file.info("                             Ixia                                    ")
        log_file.info("                               |                                     ")
        log_file.info("                  +--------------------------+                       ")
        log_file.info("                  |                          |                       ")
        log_file.info("                  |           CRS            |                       ")
        log_file.info("                  |  Tx Rx             Tx Rx |                       ")
        log_file.info("                  +--------------------------+                       ")
        log_file.info("                     |  |              |  |                          ")
        log_file.info("                     %s %s             %s %s                         " %(topo['cm1'],topo['cm2']))
        log_file.info("                     |  |              |  |                          ")
        log_file.info("                     |  |              |  |                          ")
        log_file.info("                     %s %s             %s %s                         " %(topo['cm1'],topo['cm2']))
        log_file.info("                     |  |              |  |                          ")
        log_file.info("              +------------+        +------------+                   ")
        log_file.info("              |      Rx Tx |        |  Rx Tx     |                   ")
        log_file.info("              |            |        |            |                   ")
        log_file.info("              |         Tx | %s--%s | Rx         |                   " %(topo['m1m2']))
        log_file.info("              |            |        |            |                   ")
        log_file.info("              |         Rx | %s--%s | Tx         |                   ")
        log_file.info("              |            |        |            |                   ")
        log_file.info("              +------------+        +------------+                   ")

def wait_expected_route (node, route, match, wait):

    count = 0

    node.sysname = node.get_system_name()
    log_file.info("Wait up to %s seconds for route %s to be present on node %s" %(wait,route,node.sysname))
    while count <= wait:
        default_result = 'OK'
        res, cli_return = node.send_cli_command('show router route-table ipv6 %s' %(route), see_return=True)
        if match not in cli_return:
            route_result = False 
            log_file.error("Route %s NOT present on node %s after %s seconds" %(route,node.sysname,count))
        else:
            route_result = True 
        if route_result:
            log_file.info("Route %s IS present on node %s after %s seconds" %(route,node.sysname,count))
            break
        else:
            count +=1
            time.sleep(1)

    return route_result

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
