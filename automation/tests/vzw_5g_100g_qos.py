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

# Create a log file
log_file=logging.getLogger(__name__)

# Configure log file to output to stdout too
log_file.addHandler(logging.StreamHandler(sys.stdout))

testbed_data=attrdict.AttrDict()
topology = 'none'


def testbed_init(testbed_file):

    log_file.info('Initalize Testbed')
    global testbed_data

    if testbed_data:
        log_file.info('Testbed already initialized')
        return

    testbed_data = node.Testbed(testbed_file)


def configure_topology(set_topology):

    global topology
    setup_result = True 

    #Allan 
    return True
    log_file.info('Switch testbed topology to %s' %(set_topology))

    if set_topology == topology:
       log_file.info('Testbed topology already %s' %(set_topology))
       return

    if set_topology == 'qos_cran_no_off':
        #topology = 'qos_cran_no_off'
        topology = 'bogus'
        set_mode_qos_hub_no_offload(testbed_data)
        if not check_mode_qos_hub_no_offload(testbed_data):
            setup_result =  False
    elif set_topology == 'qos_cran_with_off':
        topology = 'qos_cran_off'
    else:
        log_file.error('Invalid topology of %s defined' %(set_topology))

    return setup_result

def diff_dictionaries(dict1, dict2):
    diff_dictionary = {}

    for key in dict1:
        if key in dict2:
            new_value = dict2[key] - dict1[key]
        else:
            new_value = dict1[key]

        diff_dictionary[key] = new_value

    for key in dict2:
        if key not in diff_dictionary:
            diff_dictionary[key] = dict2[key]

    return diff_dictionary

def qos_1(q_port,ixia_pattern):

    ixia_100g = testbed_data.ixia_100g

    log_file.info('qos 1')

    # Set the ixia pattern based on the test
    ixia_100g.set_traffic(pattern=ixia_pattern, commit=True)

    log_file.info("Start Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
    ixia_100g.start_traffic()

    ixia_100g.clear_stats()
    utils.countdown(30)

    log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
    ixia_100g.stop_traffic()

    log_file.info("")
    log_file.info("Get Ixia Stats")
    log_file.info("--------------")
    ixia_100g.set_stats()
    log_file.info("")

    for traffic_item in ixia_100g.traffic_names:
        ixia_100g.get_stats(traffic_item,'loss%')
        dd_opt = 'Drill down per IPv6 :Traffic Class'
        drill_down_name = traffic_item + '/' + dd_opt
        ixia_100g.set_user_def_drill_stats(target_name=traffic_item,ddopt=dd_opt)
        tc_list = ixia_100g.user_stats[drill_down_name].keys()
        tc_list.remove('columnCaptions')
        for tc in tc_list:
            loss = ixia_100g.get_user_def_drill_stats(traffic_item,tc,'loss_ms',ddopt=dd_opt) 
            if tc != '0':
                if loss > 0:
                    log_file.error("Traffic Class %s has a loss of %s - expecting 0" %(tc, loss))
                else:
                    log_file.info("Traffic Class %s has a loss of %s  - expecting 0" %(tc, loss))
            else:
                log_file.info("Traffic Class %s has a loss of %s" %(tc, loss))

    q_dict = {}
    if isinstance(q_port, node.Lag):
        for key,value in q_port.port_dict.iteritems():
            q_dict[key] = value.get_network_egress_dropped()
    else:
        q_dict = q_port.get_network_egress_dropped()
        
    log_file.info("")


    if isinstance(q_port, node.Lag):
        for key in sorted(q_port.port_dict.keys()):
            for k2 in q_dict[key].keys():
                v2 = q_dict[key][k2]
                log_file.info("Port %s : queue %s dropped = %s" %(key,k2,v2))

def qos_2(q_port,ixia_pattern):

    q_dict_1 = {}
    ixia_100g = testbed_data.ixia_100g

    # Set the ixia pattern based on the test
    #ixia_100g.set_traffic(pattern=ixia_pattern, commit=True)

    log_file.info("Start Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
    #ixia_100g.start_traffic()

    #ixia_100g.clear_stats()

    log_file.info("Look at egress queue usage on node %s port %s" %(q_port.node.sysname,q_port.port))
    log_file.info("")
    log_file.info("Poll #1")
    if isinstance(q_port, node.Lag):
        for key,value in q_port.port_dict.iteritems():
            q_dict_1[key] = value.get_network_egress_forwarded()
    else:
        q_dict_1 = q_port.get_network_egress_forwarded()
        
    if isinstance(q_port, node.Lag):
        for key in sorted(q_port.port_dict.keys()):
            for k2 in q_dict_1[key].keys():
                v2 = q_dict_1[key][k2]
                log_file.info("Port %s : Egress queue %s forwarded = %s" %(key,k2,v2))
            log_file.info("")
    else:
        for key in sorted(q_dict_1.keys()):
            v2 = q_dict_1[key]
            log_file.info("Port %s : Egress queue %s forwarded = %s" %(q_port.port,key,v2))

    log_file.info("")
    log_file.info("Wait 30s and poll again")
    log_file.info("")

    time.sleep(30)
    log_file.info("Poll #2")

    log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
    #ixia_100g.stop_traffic()
    log_file.info("")

    q_dict_2 = {}
    if isinstance(q_port, node.Lag):
        for key,value in q_port.port_dict.iteritems():
            q_dict_2[key] = value.get_network_egress_forwarded()
    else:
        q_dict_2 = q_port.get_network_egress_forwarded()

    if isinstance(q_port, node.Lag):
        for key in sorted(q_port.port_dict.keys()):
            for k2 in q_dict_2[key].keys():
                v2 = q_dict_2[key][k2]
                log_file.info("Port %s : Egress queue %s forwarded = %s" %(key,k2,v2))
            log_file.info("")
    else:
        for key in sorted(q_dict_2.keys()):
            v2 = q_dict_2[key]
            log_file.info("Port %s : Egress queue %s forwarded = %s" %(q_port.port,key,v2))


    log_file.info("")
    log_file.info("Egress queue deltas on node %s port %s" %(q_port.node.sysname,q_port.port))
    if isinstance(q_port, node.Lag):
        for key in sorted(q_port.port_dict.keys()):
            delta_dict = diff_dictionaries(q_dict_1[key], q_dict_2[key])
            log_file.info("Port %s : " %(key))
            for key in sorted(delta_dict.keys()):
                delta_val = delta_dict[key]
                log_file.info("Egress queue %s delta = %s" %(key,delta_val))
            log_file.info("")
    else:
        delta_dict = diff_dictionaries(q_dict_1, q_dict_2)

        for key in sorted(delta_dict.keys()):
            delta_val = delta_dict[key]
            log_file.info("Port %s : Egress queue %s delta = %s" %(q_port.port,key,delta_val))


def main(testcase_name='',testsuite_name='vzw_5g_qos_dev',csv='false',testbed_file='vzw_5g_100g.yaml'):

    hub_site_stat       = {}
    hub_site_stat_final = {}
    port_result         = 'PASS'
    test_result         = 'PASS'
    test_path           = '/automation/python/tests/'
    testbed_file        = test_path+testbed_file
    standby_wait        = 240
    port_wait           = 120

    set_topology = 'qos_cran_no_off'
    ixia_pattern = 'Auto-Qos-North-1'
    threshold = 0

    start_time = datetime.now()

    # Initialize the testbed
    testbed_init(testbed_file)

    # Give the nodes user friendly names 
    mls_1 = testbed_data.mls_1
    mls_2 = testbed_data.mls_2

    off_1 = testbed_data.off_1
    off_2 = testbed_data.off_2

    hub_1 = testbed_data.hub_1
    hub_2 = testbed_data.hub_2

    wbx_89 = testbed_data.wbx_89
    wbx_98 = testbed_data.wbx_98

    ixia_100g = testbed_data.ixia_100g

    log_file.info('Check all nodes for hw errors')
    for error_node in testbed_data.node_dict.values():
        error_node.check_for_hw_errors()
            

    if configure_topology(set_topology):

        if testcase_name == 'wbx_north_port_to_lag_congestion':
            qos_1(wbx_89.to_hub_1,ixia_pattern)
        if testcase_name == 'wbx_south_lag_to_port_egress_queues':
            qos_2(wbx_89.to_ixia,'ac-')
        if testcase_name == 'wbx_north_port_to_lag_egress_queues':
            #qos_2(wbx_89.to_hub_1,'ac-')
            qos_2(wbx_89.test,'ac-')


        log_file.info("")
        log_file.info("Look for any errors in log-99")
        log_file.info("-----------------------------")
        #log_99 = wbx_89.send_cli_command('show log log-id 99')
        #log_file.info(log_99)

        end_time = datetime.now()
        test_dur = end_time - start_time
        test_dur_sec = test_dur.total_seconds()


        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("")
        log_file.info("Test Name %s " %(testcase_name))
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

    test_result_list = [] 
    test_result_list.append(test_result)
    test_result_dict = {} 
    #key = testplan[action]['node'] + '_' + 'loss'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'loss%') 
    #key = testplan[action]['node'] + '_' + 'min_latency'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'min_latency') 

    #key = testplan[action]['node'] + '_' + 'max_latency'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'max_latency') 

    #key = testplan[action]['node'] + '_' + 'avg_latency'
    #test_result_dict[key] = ixia_100g.get_stats(ixs[0],'avg_latency') 

    test_result_list.append(test_result_dict)
    return test_result_list






def set_mode_qos_hub_no_offload(testbed_nodes):

    log_file.info('Put testbed in Mode: CRAN Hub no Offload')

    testbed_nodes.mls_1.to_crs.no_shutdown(snmp=True)

    testbed_nodes.mls_1.to_mls_2.no_shutdown(snmp=True)
    testbed_nodes.mls_1.to_mls_2.no_shutdown_all_lag_members()

    testbed_nodes.mls_1.to_off_1.no_shutdown(snmp=True)
    testbed_nodes.mls_1.to_off_1.no_shutdown_all_lag_members()

    testbed_nodes.mls_1.to_hub_1.no_shutdown(snmp=True)
    testbed_nodes.mls_1.to_hub_1.no_shutdown_all_lag_members()

    testbed_nodes.mls_2.to_crs.no_shutdown(snmp=True)

    testbed_nodes.mls_2.to_mls_1.no_shutdown(snmp=True)
    testbed_nodes.mls_2.to_mls_1.no_shutdown_all_lag_members()

    testbed_nodes.mls_2.to_off_2.no_shutdown(snmp=True)
    testbed_nodes.mls_2.to_off_2.no_shutdown_all_lag_members()

    testbed_nodes.mls_2.to_hub_2.no_shutdown(snmp=True)
    testbed_nodes.mls_2.to_hub_2.no_shutdown_all_lag_members()

    testbed_nodes.mls_2.to_hub_6.shutdown(snmp=True)

    testbed_nodes.off_1.to_mls_1.no_shutdown(snmp=True)
    testbed_nodes.off_1.to_mls_1.no_shutdown_all_lag_members()

    testbed_nodes.off_1.to_hub_1.shutdown(snmp=True)

    testbed_nodes.off_2.to_mls_2.no_shutdown(snmp=True)
    testbed_nodes.off_2.to_mls_2.no_shutdown_all_lag_members()

    testbed_nodes.off_2.to_hub_2.shutdown(snmp=True)

    testbed_nodes.hub_1.to_off_1.shutdown(snmp=True)

    testbed_nodes.hub_1.to_mls_1.no_shutdown(snmp=True)
    testbed_nodes.hub_1.to_mls_1.no_shutdown_all_lag_members()

    testbed_nodes.hub_1.to_hub_2.no_shutdown(snmp=True)
    testbed_nodes.hub_1.to_hub_2.no_shutdown_all_lag_members()

    testbed_nodes.hub_2.to_hub_1.no_shutdown(snmp=True)
    testbed_nodes.hub_2.to_hub_1.no_shutdown_all_lag_members()

    testbed_nodes.hub_2.to_off_2.shutdown(snmp=True)

    testbed_nodes.hub_2.to_mls_2.no_shutdown(snmp=True)
    testbed_nodes.hub_2.to_mls_2.no_shutdown_all_lag_members()

    testbed_nodes.hub_2.to_hub_3.shutdown(snmp=True)


def check_mode_qos_hub_no_offload(testbed_nodes):

    result = True 

    if not testbed_nodes.mls_1.to_crs.wait_port_oper_up_ex(120):
        result == False 
    if not testbed_nodes.mls_1.to_off_1.wait_port_oper_up_ex(120):
        result == False 
    if not testbed_nodes.mls_1.to_mls_2.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.mls_1.to_hub_1.wait_port_oper_up(120):
        result == False 

    if not testbed_nodes.mls_2.to_crs.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.mls_2.to_off_2.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.mls_2.to_mls_1.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.mls_2.to_hub_2.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.mls_2.to_hub_6.wait_port_oper_down(10):
        result == False 

    if not testbed_nodes.off_1.to_mls_1.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.off_1.to_hub_1.wait_port_oper_down(10):
        result == False 

    if not testbed_nodes.off_2.to_mls_2.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.off_2.to_hub_2.wait_port_oper_down(10):
        result == False 

    if not testbed_nodes.hub_1.to_off_1.wait_port_oper_down(10):
        result == False 
    if not testbed_nodes.hub_1.to_mls_1.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.hub_1.to_hub_2.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.hub_2.to_off_2.wait_port_oper_down(10):
        result == False 
    if not testbed_nodes.hub_2.to_mls_2.wait_port_oper_up(120):
        result == False 
    if not testbed_nodes.hub_2.to_hub_3.wait_port_oper_down(10):
        result == False 
    if not testbed_nodes.hub_2.to_hub_1.wait_port_oper_up(120):
        result == False 

    return result

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
