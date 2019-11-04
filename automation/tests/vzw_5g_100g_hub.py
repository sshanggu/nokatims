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

from datetime import datetime
from easysnmp import Session
from textwrap import dedent
from collections import OrderedDict

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
    
    # Create ixia object
    log_file.info('Build Ixia')
    testbed_data.ixia_100g    = ixia.IxNetx(**yaml_data['ixia'])

    log_file.info('Build Nodes, IOMs, MDAs, Ports and Services ...')
    for tb_node in yaml_data['nodes'].keys() :
        cpm_obj=node.Node(**yaml_data['nodes'][tb_node])
        testbed_data[tb_node] = cpm_obj

def add_sr1(sr1_file):

    # Read in the testbed yaml file into yaml_data dictionary
    with open(sr1_file, 'r') as f: 
        sr1_yaml_data=yaml.load(f)

    log_file.info('Build SR1 specific nodes, IOMs, MDAs, Ports and Services ...')
    for sr1_node in sr1_yaml_data['nodes'].keys() :
        cpm_obj=node.Node(**sr1_yaml_data['nodes'][sr1_node])
        testbed_data[sr1_node] = cpm_obj

def main(testcase_name='',testsuite_name='vzw_5g_hub_dev',csv='false',testbed_file='vzw_5g_100g.yaml'):

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
    
    # Next gen nodes
    el_1 = testbed_data['el_1']
    el_2 = testbed_data['el_2']

    # For WBX bash 
    wbx_spine_2 = testbed_data['wbx_spine_2']

    # Old school nodes
    mls_1 = testbed_data['mls_1']
    mls_2 = testbed_data['mls_2']

    off_1 = testbed_data['off_1']
    off_2 = testbed_data['off_2']

    hub_1 = testbed_data['hub_1']
    hub_2 = testbed_data['hub_2']

    wbx_89 = testbed_data['wbx_89']
    wbx_98 = testbed_data['wbx_98']

    ixia_100g = testbed_data.ixia_100g

    testplan = {}

    # Dictionary of expected loss in ms per IPv6 traffic class
    tc_dict  = {}
    tc_dict_no_drop      = {'0':0,    '32':0,    '64':0,    '96':0,    '128':0,    '184':0,    '224':0} 
    tc_dict_be_drop      = {'0':200,  '32':0,    '64':0,    '96':0,    '128':0,    '184':0,    '224':0} 
    tc_dict_be_lbe_drop  = {'0':200,  '32':200,  '64':0,    '96':0,    '128':0,    '184':0,    '224':0} 
    tc_dict_all_drop     = {'0':1500, '32':1500, '64':1500, '96':1500, '128':1500, '184':1500, '224':1500} 

    # Tests to set up suite topology
    testplan['mls_with_bg_set_up']           = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'MLS'}
    testplan['hub_offload_set_up']           = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'CRAN_OFF'}
    testplan['hub_no_offload_set_up']        = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'CRAN_NO_OFF'}
    testplan['ng_hub_no_offload_set_up']     = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'NG_CRAN_NO_OFF'}
    testplan['sr1_hub_no_offload_set_up']    = {'ixia_pat' : 'na', 'action' : 'suite_set_up', 'topology' : 'SR1_CRAN_NO_OFF'}

    # Teardown 
    testplan['teardown']                  = {'ixia_pat' : 'na', 'action' : 'suite_teardown', 'topology' : 'CRAN_NO_OFF'}

    # MLS with background traffic tests, i.e. no CRAN hubs
    # BE loss expected on inter MLS lag port failures as we send > 100G per slot in these tests
    testplan['mls_with_bg_sanity']               = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'sanity', 'topology' : 'MLS', 'tc_dict' : tc_dict_no_drop}

    testplan['mls_with_bg_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'reboot_mls_1_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_with_bg_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'reboot_mls_2_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_with_bg_reboot_both_standby_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'reboot_both_standby_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}

    testplan['mls_with_bg_switch_mls_1_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'switch_mls_1_active_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_with_bg_switch_mls_2_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'switch_mls_2_active_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_with_bg_switch_both_active_cpm']   = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'switch_both_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}

    testplan['mls_with_bg_fail_mls_1_lag_to_mls_2']                          = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'fail_mls_1_lag_to_mls_2', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_with_bg_shut_inter_mls_port_one_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_reboot_mls_1_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_be_drop}
    testplan['mls_with_bg_shut_inter_mls_port_one_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_reboot_mls_2_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_with_bg_shut_inter_mls_port_one_switch_mls_1_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_switch_mls_1_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_be_drop}
    testplan['mls_with_bg_shut_inter_mls_port_one_switch_mls_2_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_switch_mls_2_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    
    #testplan['mls_with_bg_shut_inter_mls_port_one']                          = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    #testplan['mls_with_bg_shut_inter_mls_port_one_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_reboot_mls_1_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_be_drop}
    #testplan['mls_with_bg_shut_inter_mls_port_one_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_reboot_mls_2_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    #testplan['mls_with_bg_shut_inter_mls_port_one_switch_mls_1_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_switch_mls_1_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_be_drop}
    #testplan['mls_with_bg_shut_inter_mls_port_one_switch_mls_2_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_one_switch_mls_2_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    
    testplan['mls_with_bg_shut_inter_mls_port_two_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'action' : 'shut_inter_mls_port_two_reboot_mls_1_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_be_drop}

    testplan['mls_1_with_bg_switch_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'force_mls' : 'to_mls_1', 'action' : 'switch_mls_1_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_2_with_bg_switch_active_cpm']  = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'force_mls' : 'to_mls_2', 'action' : 'switch_mls_2_active_cpm',  'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_1_with_bg_reboot_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'force_mls' : 'to_mls_1', 'action' : 'reboot_mls_1_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}
    testplan['mls_2_with_bg_reboot_standby_cpm'] = {'ixia_pat' : 'af-LTE-5G-100G-BG', 'force_mls' : 'to_mls_2', 'action' : 'reboot_mls_2_standby_cpm', 'topology' : 'MLS', 'tc_dict':tc_dict_no_drop}

    # CRAN hubs NO Offload
    # No loss expected on inter MLS lag port failures as we don't send > 100G per slot in these tests
    testplan['hub_no_offload_sanity']                    = {'ixia_pat' : 'ac-', 'action' : 'sanity', 'topology' : 'CRAN_NO_OFF' ,'tc_dict':tc_dict_no_drop} 

    testplan['hub_no_offload_fail_mls_1_lag_to_crs']     = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_1_lag_to_crs', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_fail_mls_2_lag_to_crs']     = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_2_lag_to_crs', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_fail_mls_1_lag_to_mls_2']   = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_1_lag_to_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_fail_mls_1_lag_to_mls_2_1_member']   = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_fail_hub_1_lag_to_mls_1']   = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_mls_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['hub_no_offload_fail_hub_1_lag_to_mls_1_1_member']    = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_mls_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_fail_hub_2_lag_to_mls_2']   = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_2_lag_to_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_fail_hub_2_lag_to_mls_2_1_member']    = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_2_lag_to_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_fail_hub_1_lag_to_hub_2']  = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_hub_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_fail_hub_1_lag_to_hub_2_1_member']    = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_hub_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_sf_hub_1_to_mls_1']        = {'ixia_pat' : 'ac-', 'action' : 'sf_hub_1_to_mls_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_sf_hub_2_to_mls_2']        = {'ixia_pat' : 'ac-', 'action' : 'sf_hub_2_to_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_fail_hub_1_iom_to_mls_1']  = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_iom_to_mls_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_fail_hub_1_mda_to_mls_1']  = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_mda_to_mls_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'reboot_mls_1_standby_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_no_offload_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'reboot_mls_2_standby_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_no_offload_reboot_hub_1_standby_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'reboot_hub_1_standby_cpm', 'topology' : 'CRAN_NO_OFF','tc_dict':tc_dict_no_drop }
    testplan['hub_no_offload_reboot_hub_2_standby_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'reboot_hub_2_standby_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}

    testplan['hub_no_offload_switch_mls_1_active_cpm']  = {'ixia_pat' : 'ac-', 'action' : 'switch_mls_1_active_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_no_offload_switch_mls_2_active_cpm']  = {'ixia_pat' : 'ac-', 'action' : 'switch_mls_2_active_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_no_offload_switch_hub_1_active_cpm']  = {'ixia_pat' : 'ac-', 'action' : 'switch_hub_1_active_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_no_offload_switch_hub_2_active_cpm']  = {'ixia_pat' : 'ac-', 'action' : 'switch_hub_2_active_cpm', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}

    testplan['hub_no_offload_reboot_mls_1']             = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_mls_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_reboot_mls_2']             = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_reboot_hub_1']             = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_hub_1', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_reboot_hub_2']             = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_hub_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_no_offload_reboot_wbx_89']            = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_wbx_89','topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_standby_cpm', 'topology':'CRAN_NO_OFF','tc_dict':tc_dict_all_drop }
    testplan['hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_switch_mls_1_active_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_active_cpm', 'topology':'CRAN_NO_OFF','tc_dict':tc_dict_all_drop }
    testplan['hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_standby_cpm', 'topology':'CRAN_NO_OFF','tc_dict':tc_dict_all_drop }
    testplan['hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_switch_mls_2_active_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_active_cpm', 'topology':'CRAN_NO_OFF','tc_dict':tc_dict_all_drop }

    # CRAN hubs WITH Offload
    # No loss expected on inter MLS lag port failures as we don't send > 100G per slot in these tests
    testplan['hub_offload_sanity']                           = {'ixia_pat' : 'ac-', 'action' : 'sanity', 'topology' : 'CRAN_OFF' ,'tc_dict':tc_dict_no_drop} 

    testplan['hub_offload_fail_mls_1_lag_to_crs']            = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_1_lag_to_crs', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_mls_2_lag_to_crs']            = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_2_lag_to_crs', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_fail_mls_1_lag_to_mls_2']          = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_1_lag_to_mls_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_mls_1_lag_to_mls_2_1_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_fail_hub_1_lag_to_off_1']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_off_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_1_lag_to_off_1_1_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_off_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_1_lag_to_off_1_2_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_2_member_hub_1_lag_to_off_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_2_lag_to_off_2']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_2_lag_to_off_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_2_lag_to_off_2_1_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_2_lag_to_off_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_2_lag_to_off_2_2_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_2_member_hub_2_lag_to_off_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_fail_hub_1_lag_to_mls_1']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_mls_1', 'topology' : 'CRAN_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['hub_offload_fail_hub_1_lag_to_mls_1_1_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_mls_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_2_lag_to_mls_2']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_2_lag_to_mls_2', 'topology' : 'CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_2_lag_to_mls_2_1_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_2_lag_to_mls_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_1_lag_to_hub_2']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_hub_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_1_lag_to_hub_2_1_member'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_hub_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_fail_off_1_vpls']                  = {'ixia_pat' : 'ac-', 'action' : 'fail_off_1_vpls', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_off_2_vpls']                  = {'ixia_pat' : 'ac-', 'action' : 'fail_off_2_vpls', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_fail_hub_1_iom_to_mls_1']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_iom_to_mls_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_fail_hub_1_mda_to_mls_1']          = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_mda_to_mls_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_reboot_mls_1_standby_cpm']         = {'ixia_pat' : 'ac-', 'action' : 'reboot_mls_1_standby_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_offload_reboot_mls_2_standby_cpm']         = {'ixia_pat' : 'ac-', 'action' : 'reboot_mls_2_standby_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_offload_reboot_hub_1_standby_cpm']         = {'ixia_pat' : 'ac-', 'action' : 'reboot_hub_1_standby_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop }
    testplan['hub_offload_reboot_hub_2_standby_cpm']         = {'ixia_pat' : 'ac-', 'action' : 'reboot_hub_2_standby_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}

    testplan['hub_offload_switch_mls_1_active_cpm']          = {'ixia_pat' : 'ac-', 'action' : 'switch_mls_1_active_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_offload_switch_mls_2_active_cpm']          = {'ixia_pat' : 'ac-', 'action' : 'switch_mls_2_active_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_offload_switch_hub_1_active_cpm']          = {'ixia_pat' : 'ac-', 'action' : 'switch_hub_1_active_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['hub_offload_switch_hub_2_active_cpm']          = {'ixia_pat' : 'ac-', 'action' : 'switch_hub_2_active_cpm', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_no_drop}

    testplan['hub_offload_reboot_mls_1']                     = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_mls_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_reboot_mls_2']                     = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_mls_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_reboot_off_1']                     = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_off_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_reboot_off_2']                     = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_off_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_reboot_hub_1']                     = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_hub_1', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_reboot_hub_2']                     = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_hub_2', 'topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['hub_offload_reboot_wbx_89']                 = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_wbx_89','topology' : 'CRAN_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['hub_offload_fail_mls_1_lag_to_mls_2_1_member_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_standby_cpm','topology':'CRAN_OFF','tc_dict':tc_dict_all_drop }
    testplan['hub_offload_fail_mls_1_lag_to_mls_2_1_member_switch_mls_1_active_cpm']  = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_active_cpm', 'topology':'CRAN_OFF','tc_dict':tc_dict_all_drop }
    testplan['hub_offload_fail_mls_1_lag_to_mls_2_1_member_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_standby_cpm','topology':'CRAN_OFF','tc_dict':tc_dict_all_drop }
    testplan['hub_offload_fail_mls_1_lag_to_mls_2_1_member_switch_mls_2_active_cpm']  = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_active_cpm', 'topology':'CRAN_OFF','tc_dict':tc_dict_all_drop }

    # NG CRAN hubs NO Offload
    testplan['ng_hub_no_offload_sanity']                             = {'ixia_pat' : 'ac-', 'action' : 'sanity', 'topology' : 'NG_CRAN_NO_OFF' ,'tc_dict':tc_dict_no_drop} 

    testplan['ng_hub_no_offload_fail_el1_lag_to_wbx_spine_1']        = {'ixia_pat' : 'ac-', 'action' : 'fail_el_1_lag_to_wbx_spine_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_el1_lag_to_wbx_spine_2']        = {'ixia_pat' : 'ac-', 'action' : 'fail_el_1_lag_to_wbx_spine_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_el2_lag_to_wbx_spine_1']        = {'ixia_pat' : 'ac-', 'action' : 'fail_el_2_lag_to_wbx_spine_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_el2_lag_to_wbx_spine_2']        = {'ixia_pat' : 'ac-', 'action' : 'fail_el_2_lag_to_wbx_spine_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}

    testplan['ng_hub_no_offload_fail_wbx_spine_1_lag_to_mls_1']      = {'ixia_pat' : 'ac-', 'action' : 'fail_wbx_spine_1_lag_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_wbx_spine_1_lag_to_mls_2']      = {'ixia_pat' : 'ac-', 'action' : 'fail_wbx_spine_1_lag_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_wbx_spine_2_lag_to_mls_1']      = {'ixia_pat' : 'ac-', 'action' : 'fail_wbx_spine_2_lag_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_wbx_spine_2_lag_to_mls_2']      = {'ixia_pat' : 'ac-', 'action' : 'fail_wbx_spine_2_lag_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}

    testplan['ng_hub_no_offload_fail_mls_1_lag_to_mls_2']            = {'ixia_pat' : 'ac-', 'action' : 'fail_mls_1_lag_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_mls_1_lag_to_mls_2_1_member']   = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_1_lag_to_mls_1']            = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_1_lag_to_mls_1_1_member']   = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_1_lag_to_hub_2']            = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_lag_to_hub_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_1_lag_to_hub_2_1_member']   = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_1_lag_to_hub_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_2_lag_to_mls_2']            = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_2_lag_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_2_lag_to_mls_2_1_member']   = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_hub_2_lag_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['ng_hub_no_offload_sf_hub_1_to_mls_1']                  = {'ixia_pat' : 'ac-', 'action' : 'sf_hub_1_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_sf_hub_2_to_mls_2']                  = {'ixia_pat' : 'ac-', 'action' : 'sf_hub_2_to_mls_2', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['ng_hub_no_offload_fail_hub_1_iom_to_mls_1']            = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_iom_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_fail_hub_1_mda_to_mls_1']            = {'ixia_pat' : 'ac-', 'action' : 'fail_hub_1_mda_to_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    testplan['ng_hub_no_offload_reboot_mls_1_standby_cpm']           = {'ixia_pat' : 'ac-', 'action' : 'reboot_mls_1_standby_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_reboot_mls_2_standby_cpm']           = {'ixia_pat' : 'ac-', 'action' : 'reboot_mls_2_standby_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_reboot_hub_1_standby_cpm']           = {'ixia_pat' : 'ac-', 'action' : 'reboot_hub_1_standby_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_reboot_hub_2_standby_cpm']           = {'ixia_pat' : 'ac-', 'action' : 'reboot_hub_2_standby_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}

    testplan['ng_hub_no_offload_switch_mls_1_active_cpm']            = {'ixia_pat' : 'ac-', 'action' : 'switch_mls_1_active_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_switch_mls_2_active_cpm']            = {'ixia_pat' : 'ac-', 'action' : 'switch_mls_2_active_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_switch_hub_1_active_cpm']            = {'ixia_pat' : 'ac-', 'action' : 'switch_hub_1_active_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_switch_hub_2_active_cpm']            = {'ixia_pat' : 'ac-', 'action' : 'switch_hub_2_active_cpm', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    
    testplan['ng_hub_no_offload_reboot_mls_1']                       = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_reboot_hub_1']                       = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_hub_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['ng_hub_no_offload_reboot_wbx_89']                      = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_wbx_89','topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_reboot_wbx_spine_1']                 = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_wbx_spine_1','topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}
    testplan['ng_hub_no_offload_reboot_wbx_spine_2']                 = {'ixia_pat' : 'ac-', 'action' : 'reboot_node_wbx_spine_2','topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_no_drop}

    testplan['ng_hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_reboot_mls_1_standby_cpm'] = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_standby_cpm', 'topology':'NG_CRAN_NO_OFF','tc_dict':tc_dict_all_drop }
    testplan['ng_hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_switch_mls_1_active_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_active_cpm', 'topology':'NG_CRAN_NO_OFF','tc_dict':tc_dict_all_drop }
    testplan['ng_hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_reboot_mls_2_standby_cpm'] = {'ixia_pat' : 'ac-', 'action': 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_standby_cpm', 'topology':'NG_CRAN_NO_OFF','tc_dict':tc_dict_all_drop }
    testplan['ng_hub_no_offload_fail_mls_1_lag_to_mls_2_1_member_switch_mls_2_active_cpm'] = {'ixia_pat' : 'ac-', 'action' : 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_active_cpm', 'topology':'NG_CRAN_NO_OFF','tc_dict':tc_dict_all_drop }

    testplan['ng_hub_no_offload_isolate_mls_1']                     = {'ixia_pat' : 'ac-', 'action' : 'isolate_node_mls_1', 'topology' : 'NG_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    # SR1 HUBs
    testplan['sr1_hub_no_offload_sanity']                           = {'ixia_pat' : 'asr1c-', 'action' : 'sanity', 'topology' : 'SR1_CRAN_NO_OFF' ,'tc_dict':tc_dict_no_drop} 
    testplan['sr1_hub_no_offload_fail_mls_1_lag_to_crs']            = {'ixia_pat' : 'asr1c-', 'action' : 'fail_mls_1_lag_to_crs', 'topology' : 'SR1_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['sr1_hub_no_offload_fail_mls_2_lag_to_crs']            = {'ixia_pat' : 'asr1c-', 'action' : 'fail_mls_2_lag_to_crs', 'topology' : 'SR1_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}
    testplan['sr1_hub_no_offload_fail_hub_1_lag_to_mls_1']          = {'ixia_pat' : 'asr1c-', 'action' : 'fail_sr1_hub_1_lag_to_mls_1', 'topology' : 'SR1_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['sr1_hub_no_offload_fail_hub_2_lag_to_mls_2']          = {'ixia_pat' : 'asr1c-', 'action' : 'fail_sr1_hub_2_lag_to_mls_2', 'topology' : 'SR1_CRAN_NO_OFF', 'tc_dict' : tc_dict_all_drop}
    testplan['sr1_hub_no_offload_reboot_mls_1']                     = {'ixia_pat' : 'asr1c-', 'action' : 'reboot_node_mls_1', 'topology' : 'SR1_CRAN_NO_OFF', 'tc_dict':tc_dict_all_drop}

    # Compare passed in testname to full list of possible testcases 
    if testcase_name not in testplan:
        print "\nERROR: Unsupported test case of %s"%(testcase_name)
        print "ERROR: run with -h to get list of supported test cases"
        sys.exit()

    # Read in testplan for specific testcase
    ixia_pattern = testplan[testcase_name]['ixia_pat']
    action       = testplan[testcase_name]['action']

    if 'topology' not in testplan[testcase_name]:  
        print "No topology specified in testplan.  Assume CRAN via offload"
        topology = 'CRAN_OFF' 
    else:
        topology = testplan[testcase_name]['topology']
        print "Testbed topology specified in testplan to be %s" %(topology)

    if topology == 'SR1_CRAN_NO_OFF':
        log_file.info("Topology = SR1 CRAN NO OFFLOAD")

        log_file.info("Bring MLS ports to SR1s up for inband EDN access")
        mls_1.to_sr1_hub_1_10.no_shutdown(snmp=True)
        mls_1.to_sr1_hub_1_10.no_shutdown_all_lag_members()
        mls_2.to_sr1_hub_2_10.no_shutdown(snmp=True)
        mls_2.to_sr1_hub_2_10.no_shutdown_all_lag_members()

        log_file.info("Wait for MLS ports to SR1s to come up")
        mls_1.to_sr1_hub_1_10.wait_port_oper_up_ex(120)
        mls_2.to_sr1_hub_2_10.wait_port_oper_up_ex(120)

        log_file.info("Add SR1s to testbed dictionary")
        add_sr1('/automation/python/tests/vzw_5g_sr1.yaml')
        sr1_hub_1 = testbed_data['sr1_hub_1']
        sr1_hub_2 = testbed_data['sr1_hub_2']

        sr1_hub_1_chassis_type       = sr1_hub_1.get_chassis_type()
        sr1_hub_1_cpm_active_sw_ver  = sr1_hub_1.get_active_cpm_sw_version()
        sr1_hub_2_chassis_type       = sr1_hub_2.get_chassis_type()
        sr1_hub_2_cpm_active_sw_ver  = sr1_hub_2.get_active_cpm_sw_version()

        
    if 'force_mls' not in testplan[testcase_name]:
        print "No MLS force specified in testplan.  Assume none"
        force_mls = 'none'
    else:
        force_mls = testplan[testcase_name]['force_mls']

    if 'tc_dict' not in testplan[testcase_name]:
        tc_dict = {}
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

    hub_1_chassis_type       = hub_1.get_chassis_type()
    hub_1_cpm_active_sw_ver  = hub_1.get_active_cpm_sw_version()

    hub_2_chassis_type       = hub_2.get_chassis_type()
    hub_2_cpm_active_sw_ver  = hub_2.get_active_cpm_sw_version()

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

        if topology == 'MLS':
            set_mode_mls_bg(mls_1, mls_2, off_1, off_2, hub_1, hub_2)
            if (check_mode_mls_bg(mls_1, mls_2, off_1, off_2, hub_1, hub_2) != 'OK'): set_up_result = 'FAIL'
        elif topology == 'CRAN_OFF':
            set_mode_hub_with_offload()
            if not check_mode_hub_with_offload(): set_up_result = 'FAIL'
        elif topology == 'CRAN_NO_OFF':
            set_mode_hub_no_offload()
            if not check_mode_hub_no_offload(): set_up_result = 'FAIL'
        elif topology == 'NG_CRAN_NO_OFF':
            set_mode_ng_hub_no_offload()
            if not check_mode_ng_hub_no_offload(): set_up_result = 'FAIL'
        elif topology == 'SR1_CRAN_NO_OFF':
            sr1_hub_1_chassis_type       = sr1_hub_1.get_chassis_type()
            sr1_hub_1_cpm_active_sw_ver  = sr1_hub_1.get_active_cpm_sw_version()
            sr1_hub_2_chassis_type       = sr1_hub_2.get_chassis_type()
            sr1_hub_2_cpm_active_sw_ver  = sr1_hub_2.get_active_cpm_sw_version()
            set_mode_sr1_hub_no_offload()
            if not check_mode_sr1_hub_no_offload(): set_up_result = 'FAIL'

        else:
            log_file.error("Invalid topology defined")
            set_up_result == 'FAIL'

        if set_up_result == 'PASS':
           clear_all_port_stats(testbed_nodes)
           set_all_port_ether_stats_itvl(testbed_nodes,30)
           log_file.info('Suite set up OK, save the testbed configs')

           if topology == 'NG_CRAN_NO_OFF':
               el_1.admin_save()
               el_2.admin_save()
               wbx_spine_1.admin_save()
               wbx_spine_2.admin_save()

           mls_1.admin_save()
           mls_2.admin_save()
           off_1.admin_save()
           off_2.admin_save()
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
    log_file.info("Traffic Forced To MLS1 or MLS2?: .. %s" %(force_mls))
    log_file.info("")
    log_file.info("MLS 1 chassis type ................ %s" %(mls_1_chassis_type))
    log_file.info("MLS 1 Active CPM software version . %s" %(mls_1_cpm_active_sw_ver))
    log_file.info("MLS 2 chassis type ................ %s" %(mls_2_chassis_type))
    log_file.info("MLS 2 Active CPM software version . %s" %(mls_2_cpm_active_sw_ver))
    log_file.info(" ")
    if topology == 'CRAN_OFF':
        log_file.info("OFF 1 chassis type ................ %s" %(off_1_chassis_type))
        log_file.info("OFF 1 Active CPM software version . %s" %(off_1_cpm_active_sw_ver))
        log_file.info("OFF 2 chassis type ................ %s" %(off_2_chassis_type))
        log_file.info("OFF 2 Active CPM software version . %s" %(off_2_cpm_active_sw_ver))
        log_file.info(" ")
    if topology == 'CRAN_OFF' or topology == 'CRAN_NO_OFF':
        log_file.info("HUB 1 chassis type ................ %s" %(hub_1_chassis_type))
        log_file.info("HUB 1 Active CPM software version . %s" %(hub_1_cpm_active_sw_ver))
        log_file.info("HUB 2 chassis type ................ %s" %(hub_2_chassis_type))
        log_file.info("HUB 2 Active CPM software version . %s" %(hub_2_cpm_active_sw_ver))
        log_file.info(" ")
    if topology == 'SR1_CRAN_NO_OFF':
        log_file.info("SR1 HUB 1 chassis type ................ %s" %(sr1_hub_1_chassis_type))
        log_file.info("SR1 HUB 1 Active CPM software version . %s" %(sr1_hub_1_cpm_active_sw_ver))
        log_file.info("SR1 HUB 2 chassis type ................ %s" %(sr1_hub_2_chassis_type))
        log_file.info("SR1 HUB 2 Active CPM software version . %s" %(sr1_hub_2_cpm_active_sw_ver))
        log_file.info(" ")

    log_file.info("WBX 89 chassis type ................ %s" %(wbx_89_chassis_type))
    log_file.info("WBX 89 Active CPM software version . %s" %(wbx_89_cpm_active_sw_ver))
    log_file.info("WBX 98 chassis type ................ %s" %(wbx_98_chassis_type))
    log_file.info("WBX 98 Active CPM software version . %s" %(wbx_98_cpm_active_sw_ver))
    log_file.info(" ")
    log_file.info("Take Ixia CSV Snapshot ............ %s" %(csv))
    log_file.info("")
    log_file.info("--------------------------------------------------")

    show_topo(testbed_nodes,topology)

    edn_wait  = 10
    edn_count = 26

    if topology == 'CRAN_NO_OFF' or topology == 'CRAN_OFF':
        if not check_edn_ready(edn_count,edn_wait):
            set_up_result = 'FAIL'
        if not (wait_expected_route(mls_2,'2001:4888:2014:6503:50:101:1:2','129',120)):
            set_up_result = 'FAIL'
        if not (wait_expected_route(hub_1,'::/0','ToSR163-Vlan-39',120)):
            set_up_result = 'FAIL'
            log_file.error('Default route not valid')
    elif topology == 'SR1_CRAN_NO_OFF':
        if not check_sr1_edn_ready(3,edn_wait):
            set_up_result = 'FAIL'
    elif topology == 'NG_CRAN_NO_OFF':
        if not (wait_expected_route(mls_2,'2001:4888:2014:6503:50:101:1:2','129',120)):
            set_up_result = 'FAIL'
        if not (wait_expected_route(hub_1,'::/0','ToSR163-Vlan-39',120)):
            set_up_result = 'FAIL'
            log_file.error('Default route not valid')


    if set_up_result != 'FAIL':

        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 1: Pre failure Traffic Check") 
        log_file.info("")
        log_file.info("Start Ixia Traffic Streams ")
        log_file.info("--------------------------------------------------")
        log_file.info("")

        ixia_100g.start_traffic()
        ixia_100g.clear_stats()
        utils.countdown(10)

        ixia_100g.stop_traffic()

        log_file.info("")
        log_file.info("Get stats for all traffic items")
        log_file.info("--------------------------------------------------")
        ixia_100g.set_stats()

        for traffic_item in ixia_100g.traffic_names:
            if ixia_100g.get_stats(traffic_item,'rx') > ixia_100g.get_stats(traffic_item,'tx'):
                log_file.error("Phase 1: Traffic item %s Rx > Tx !" %(traffic_item))
                log_file.error("Phase 1: Traffic item %s Fail" %(traffic_item))
                log_file.error("")
                phase_1_result = 'FAIL'
            else:
                if ixia_100g.get_stats(traffic_item,'loss%') > 0:
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

        force_traffic_through_mls(mls_1,mls_2,force_mls,testbed_nodes,topology)
        ixia_100g.start_traffic()
        ixia_100g.clear_stats()
        utils.countdown(10)

        #log_file.info("Clear log-99 on all testbed nodes")
        #mls_1.clear_log_99()
        #mls_2.clear_log_99()
        #off_1.clear_log_99()
        #off_2.clear_log_99()
        #hub_1.clear_log_99()
        #hub_2.clear_log_99()

        if action == 'traf_both_mls':
            log_file.info("No failure action")


        elif action == 'reboot_mls_1_standby_cpm':

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

  
        elif action == 'reboot_both_standby_cpm':

            log_file.info("------------------------------")
            log_file.info("** Reboot Standby CPM on MLS 1")
            log_file.info("------------------------------")
            if mls_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 1")
                phase_2_result == 'FAIL'

            log_file.info("------------------------------")
            log_file.info("** Reboot Standby CPM on MLS 2")
            log_file.info("------------------------------")
            if mls_2.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 2")
                phase_2_result == 'FAIL'


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


        elif action == 'switch_both_active_cpm':

            log_file.info("-----------------------------")
            log_file.info("** Switch Active CPM on MLS 1")
            log_file.info("-----------------------------")
            if mls_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 1")
                phase_2_result == 'FAIL'

            log_file.info("-----------------------------")
            log_file.info("** Switch Active CPM on MLS 2")
            log_file.info("-----------------------------")
            if mls_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 2")
                phase_2_result == 'FAIL'


        elif action == 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_1_standby_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in MLS 1 to MLS 2")
            mls_1.to_mls_2.shutdown_one_lag_member()
            utils.countdown(10)
            show_topo(testbed_nodes,topology)
            log_file.info("Clear Ixia stats.  Only looking for any outage on CPM switch/fail")
            ixia_100g.clear_stats()
            utils.countdown(10)
            log_file.info("** Reboot Standby CPM on MLS 1")
            log_file.info("------------------------------")
            if mls_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 1")
                phase_2_result == 'FAIL'

        elif action == 'fail_1_member_mls_1_lag_to_mls_2_switch_mls_1_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in MLS 1 to MLS 2")
            mls_1.to_mls_2.shutdown_one_lag_member()
            utils.countdown(10)
            show_topo(testbed_nodes,topology)
            log_file.info("Clear Ixia stats.  Only looking for any outage on CPM switch/fail")
            ixia_100g.clear_stats()
            utils.countdown(10)
            log_file.info("** Switch Active CPM on MLS 1")
            log_file.info("-----------------------------")
            if mls_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 1")
                phase_2_result == 'FAIL'

        elif action == 'fail_1_member_mls_1_lag_to_mls_2_reboot_mls_2_standby_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in MLS 1 to MLS 2")
            mls_1.to_mls_2.shutdown_one_lag_member()
            utils.countdown(10)
            show_topo(testbed_nodes,topology)
            log_file.info("Clear Ixia stats.  Only looking for any outage on CPM switch/fail")
            ixia_100g.clear_stats()
            utils.countdown(10)
            log_file.info("** Reboot Standby CPM on MLS 2")
            log_file.info("------------------------------")
            if mls_2.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 2")
                phase_2_result == 'FAIL'

        elif action == 'fail_1_member_mls_1_lag_to_mls_2_switch_mls_2_active_cpm':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in MLS 1 to MLS 2")
            mls_1.to_mls_2.shutdown_one_lag_member()
            utils.countdown(10)
            show_topo(testbed_nodes,topology)
            log_file.info("Clear Ixia stats.  Only looking for any outage on CPM switch/fail")
            ixia_100g.clear_stats()
            utils.countdown(10)
            log_file.info("** Switch Active CPM on MLS 2")
            log_file.info("-----------------------------")
            if mls_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to switch CPM on MLS 2")
                phase_2_result == 'FAIL'



        elif action == 'shut_inter_mls_port_two_reboot_mls_1_standby_cpm':

            log_file.info("------------------------------")
            log_file.info("** Shutdown one inter MLS port")
            mls_1.send_cli_command('/configure port 6/2/1 shutdown')
            utils.countdown(10)
            show_topo(testbed_nodes,topology)
            log_file.info("Clear Ixia stats.  Only looking for any outage on CPM switch/fail")
            ixia_100g.clear_stats()
            utils.countdown(10)

            log_file.info("** Reboot Standby CPM on MLS 1")
            log_file.info("------------------------------")
            if mls_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on MLS 1")
                phase_2_result == 'FAIL'


        elif action == 'traf_hubs':
            log_file.info("No failure action")

        elif action == 'fail_mls_1_lag_to_crs':
            log_file.info("------------------------------")
            log_file.info("** Shutdown MLS 1 to CRS Lag")
            mls_1.to_crs.shutdown(snmp=True)
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_mls_2_lag_to_crs':
            log_file.info("------------------------------")
            log_file.info("** Shutdown MLS 2 to CRS Lag")
            mls_2.to_crs.shutdown(snmp=True)
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_mls_1_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown MLS 1 to MLS 2 Lag")
            mls_1.to_mls_2.shutdown(snmp=True)
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_1_member_mls_1_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in MLS 1 to MLS 2")
            mls_1.to_mls_2.shutdown_one_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_1_lag_to_off_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown HUB 1 Offload 1 Lag")
            hub_1.to_off_1.set_port_info('admin','down')
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_1_member_hub_1_lag_to_off_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in HUB 1 to Offload 1 Lag")
            hub_1.to_off_1.shutdown_one_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_2_member_hub_1_lag_to_off_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 2x Port in HUB 1 to Offload 1 Lag")
            hub_1.to_off_1.shutdown_two_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_2_lag_to_off_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown HUB 2 Offload 1 Lag")
            hub_2.to_off_2.set_port_info('admin','down')
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_1_member_hub_2_lag_to_off_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in HUB 2 to Offload 2 Lag")
            hub_2.to_off_2.shutdown_one_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_2_member_hub_2_lag_to_off_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 2x Port in HUB 2 to Offload 2 Lag")
            hub_2.to_off_2.shutdown_two_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_1_iom_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Fail Hub 1 to MLS 1 IOM")
            hub_1.iom_to_mls_1.shutdown()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_1_mda_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Fail Hub 1 to MLS 1 MDA")
            hub_1.mda_to_mls_1.shutdown()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_1_mda_to_hub_2':
            log_file.info("------------------------------")
            log_file.info("** Fail Hub 1 to Hub 2 MDA")
            hub_1.mda_to_hub_2.shutdown()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'reboot_hub_1_standby_cpm':

            log_file.info("-------------------------------")
            log_file.info(" ** Reboot Standby CPM on HUB 1")
            log_file.info("-------------------------------")
            if hub_1.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on HUB 1")
                phase_2_result == 'FAIL'

        elif action == 'reboot_hub_2_standby_cpm':

            log_file.info("------------------------------")
            log_file.info("** Reboot Standby CPM on HUB 2")
            log_file.info("------------------------------")
            if hub_2.reboot_standby_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on HUB 2")
                phase_2_result == 'FAIL'

        elif action == 'switch_hub_1_active_cpm':

            log_file.info("-------------------------------")
            log_file.info(" ** Switch Active CPM on HUB 1")
            log_file.info("-------------------------------")
            if hub_1.switch_active_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on HUB 1")
                phase_2_result == 'FAIL'

        elif action == 'switch_hub_2_active_cpm':

            log_file.info("------------------------------")
            log_file.info("** Switch Active CPM on HUB 2")
            log_file.info("------------------------------")
            if hub_2.switch_active_cpm() != 'OK':
                log_file.error("Unable to reboot Standby CPM on HUB 2")
                phase_2_result == 'FAIL'

        elif action == 'fail_el_1_lag_to_wbx_spine_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown EL 1 to WBX spine 1 Lag")
            el_1.to_wbx_spine_1.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_el_1_lag_to_wbx_spine_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown EL 1 to WBX spine 2 Lag")
            el_1.to_wbx_spine_2.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_el_2_lag_to_wbx_spine_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown EL 2 to WBX spine 1 Lag")
            el_2.to_wbx_spine_1.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_el_2_lag_to_wbx_spine_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown EL 2 to WBX spine 2 Lag")
            el_2.to_wbx_spine_2.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_wbx_spine_1_lag_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown WBX spine 1 to MLS 1 Lag")
            wbx_spine_1.to_mls_1.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_wbx_spine_1_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown WBX spine 1 to MLS 2 Lag")
            wbx_spine_1.to_mls_2.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_wbx_spine_2_lag_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown WBX spine 2 to MLS 1 Lag")
            wbx_spine_2.to_mls_1.set_port_info('admin','down')
            utils.countdown(10)

        elif action == 'fail_wbx_spine_2_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown WBX spine 1 to MLS 1 Lag")
            wbx_spine_2.to_mls_2.set_port_info('admin','down')
            utils.countdown(10)


        elif action == 'fail_hub_1_lag_to_hub_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown HUB 1 to HUB2  Lag")
            hub_1.to_hub_2.set_port_info('admin','down')
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_1_member_hub_1_lag_to_hub_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in HUB 1 to Hub 2 Lag")
            hub_1.to_hub_2.shutdown_one_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_1_member_hub_1_lag_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in HUB 1 to MLS 1 Lag")
            hub_1.to_mls_1.shutdown_one_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_1_member_hub_2_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown 1x Port in HUB 2 to MLS 2 Lag")
            hub_2.to_mls_2.shutdown_one_lag_member()
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_1_lag_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown HUB 1 MLS 1 Lag")
            hub_1.to_mls_1.set_port_info('admin','down')
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'fail_hub_2_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown HUB 1 MLS 1 Lag")
            hub_2.to_mls_2.set_port_info('admin','down')
            show_topo(testbed_nodes,topology)
            utils.countdown(10)

        elif action == 'reboot_node_hub_1':
            log_file.info("------------------------------")
            log_file.info("** Reboot HUB 1")
            hub_1.sr_reboot() 
            hub_1.close() 

            if hub_2.to_hub_1.wait_port_oper_down_ex(30):
                log_file.info("Hub2 sees port to Hub1 as oper down")
            else:
                log_file.error("Hub2 does not see port to Hub1 as oper down")
                phase_2_result = 'FAIL'

            if wbx_89.to_hub_1.wait_port_oper_down_ex(30):
                log_file.info("WBX89 sees port to Hub1 as oper down")
            else:
                log_file.error("WBX89 does not see port to Hub1 as oper down")
                phase_2_result = 'FAIL'

            # Stop Ixia
            log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
            ixia_100g.stop_traffic()
            ixia_100g.set_stats()

            log_file.info("Only look at traffic though WBX98")
            log_file.info("As traffic though Hub1/WBX89 is down")

            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-98' in traffic_item:
                    drill_down_names.append(traffic_item)

            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 5000 
                else:
                    loss_threshold_ms = 3000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            if hub_1.wait_node_up(300):
                log_file.info("Node is back up.  But wont take CLI/SNMP commands for a while.  So wait.")
                utils.countdown(60)
            else:
                log_file.error("Node did not come back up after reboot")

            log_file.info("Start traffic off WBX98 and look at recovery time when Hub1 comes back")
            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-98' in traffic_item:
                    ixia_100g.start_traffic([traffic_item])

            hub_1.wait_for_valid_standby_cpm(standby_wait)
            hub_1.to_hub_2.wait_port_oper_up(300)

            #Allan
            if not (wait_expected_route(hub_1,'::/0','ToSR163-Vlan-39',240)):
                log_file.error('Default route not valid')
                phase_2_result = 'FAIL'

            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-98' in traffic_item:
                    ixia_100g.stop_traffic([traffic_item])

            ixia_100g.set_stats()
            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 6000 
                else:
                    loss_threshold_ms = 3000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            log_file.info("Start all traffic - should all be error free")
            ixia_100g.commit()
            ixia_100g.execute('apply','/traffic')
            utils.countdown(20)
            ixia_100g.start_traffic()
            ixia_100g.clear_stats()


        elif action == 'reboot_node_hub_2':

            log_file.info("------------------------------")
            log_file.info("** Reboot HUB 2")
            hub_1.sr_reboot() 
            hub_1.close() 

            if hub_1.to_hub_2.wait_port_oper_down_ex(30):
                log_file.info("Hub1 sees port to Hub2 as oper down")
            else:
                log_file.error("Hub1 does not see port to Hub2 as oper down")
                phase_2_result = 'FAIL'

            if wbx_98.to_hub_2.wait_port_oper_down_ex(30):
                log_file.info("WBX98 sees port to Hub2 as oper down")
            else:
                log_file.error("WBX98 does not see port to Hub2 as oper down")
                phase_2_result = 'FAIL'

            # Stop Ixia
            log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
            ixia_100g.stop_traffic()
            ixia_100g.set_stats()

            log_file.info("Only look at traffic though WBX89")
            log_file.info("As traffic though Hub1/WBX98 is down")

            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-89' in traffic_item:
                    drill_down_names.append(traffic_item)

            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 5000 
                else:
                    loss_threshold_ms = 3000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            if hub_2.wait_node_up(300):
                log_file.info("Node is back up.  But wont take CLI/SNMP commands for a while.  So wait.")
                utils.countdown(60)
            else:
                log_file.error("Node did not come back up after reboot")

            log_file.info("Start traffic off WBX89 and look at recovery time when Hub2 comes back")
            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-89' in traffic_item:
                    ixia_100g.start_traffic([traffic_item])

            hub_1.wait_for_valid_standby_cpm(standby_wait)
            hub_1.to_hub_2.wait_port_oper_up(300)

            if not (wait_expected_route(hub_2,'::/0','ToSR164',240)):
                log_file.error('Default route not valid')
                phase_2_result = 'FAIL'

            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-89' in traffic_item:
                    ixia_100g.stop_traffic([traffic_item])

            ixia_100g.set_stats()
            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 6000 
                else:
                    loss_threshold_ms = 3000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            log_file.info("Start all traffic - should all be error free")
            ixia_100g.commit()
            ixia_100g.execute('apply','/traffic')
            utils.countdown(20)
            ixia_100g.start_traffic()
            ixia_100g.clear_stats()

        elif action == 'reboot_node_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Reboot MLS 1")
            mls_1.sr_reboot() 
            mls_1.close()

            if hub_1.to_mls_1.wait_port_oper_down_ex(30):
                log_file.info("Hub1 sees port to MLS1 as oper down")
            else:
                log_file.error("Hub1 does not see port to MLS1 as oper down")
                phase_2_result = 'FAIL'

            # Stop Ixia
            log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
            ixia_100g.stop_traffic()
            ixia_100g.set_stats()

            if mls_1.wait_node_up(300):
                log_file.info("Node is back up.  But wont take CLI/SNMP commands for a while.  So wait.")
                utils.countdown(60)
            else:
                log_file.error("Node did not come back up after reboot")
                phase_2_result = 'FAIL'

            for traffic_item in ixia_100g.traffic_names:
                key = action + '-' + traffic_item 
                loss_ms = ixia_100g.get_stats(traffic_item,'loss_ms')
                if loss_ms > 0:
                    log_file.info("Phase 3: Traffic item %s Loss Detected" %(traffic_item))
                    phase_3_result = 'DRILL'
                    if traffic_item != 'ac-LTE-5G-100G-BG-1':
                        drill_down_names.append(traffic_item)
                else:
                    log_file.info("Phase 3: Traffic item %s No Loss Detected" %(traffic_item))

                test_result_dict[key] = loss_ms 

            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 5000 
                else:
                    loss_threshold_ms = 3000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            for traffic_item in ixia_100g.traffic_names:
                ixia_100g.start_traffic([traffic_item])

            hub_1.wait_for_valid_standby_cpm(standby_wait)
            hub_1.to_hub_2.wait_port_oper_up(300)

            if not (wait_expected_route(hub_1,'::/0','ToSR163-Vlan-39',120)):
                log_file.error('Default route not valid')
                phase_2_result = 'FAIL'

            for traffic_item in ixia_100g.traffic_names:
                ixia_100g.stop_traffic([traffic_item])

            ixia_100g.set_stats()
            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 13000 
                else:
                    loss_threshold_ms = 13000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            ixia_100g.commit()
            ixia_100g.execute('apply','/traffic')
            utils.countdown(20)
            ixia_100g.start_traffic()
            ixia_100g.clear_stats()

        elif action == 'reboot_node_wbx_89':

            log_file.info("------------------------------")
            log_file.info("** Reboot WBX 89")
            wbx_89.sr_reboot() 

            if hub_1.to_wbx_89.wait_port_oper_down_ex(30): 
                log_file.info("Hub 1 sees port to WBX 89 go down")
            else: 
                log_file.error("Hub 1 never saw port to WBX 89 go down")
                phase_2_result = 'FAIL'

            utils.countdown(5)
            log_file.info("Only look at traffic through WBX98")
            for traffic_item in ixia_100g.traffic_names:
                if 'WBX1-98' in traffic_item:
                    drill_down_names.append(traffic_item)

            for drill_down_name in drill_down_names:
                log_file.info("")
                ixia_100g.set_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',loss_only=True)
                if 'EDN' in drill_down_name:
                    loss_threshold_ms = 5000 
                else:
                    loss_threshold_ms = 3000 

                if not (ixia_100g.check_user_def_drill_stats(target_name=drill_down_name,ddopt='Drill down per Source/Dest Endpoint Pair',check_val='loss_ms',check_thresh=loss_threshold_ms)):
                    phase_2_result = 'FAIL'
                else:
                    log_file.info("All Source / Dest endpoint loss for %s under threshold of %s ms" %(drill_down_name,loss_threshold_ms))

            if wbx_89.wait_node_up(300):
                log_file.info("Node is back up.  But wont take CLI/SNMP commands for a while.  So wait.")
                utils.countdown(60)
            else:
                log_file.error("Node did not come back up after reboot")

            if hub_1.to_wbx_89.wait_port_oper_up_ex(300):
                log_file.info("Hub 1 sees port to WBX 89 come back up")
            else:
                log_file.error("Hub 1 did not see port to WBX 89 come back up")
                phase_2_result = 'FAIL'

            au_list = wbx_89.get_service_admin_up_list()
            ou_list = wbx_89.get_service_oper_up_list()

            if au_list == ou_list:
                log_file.info("All admin up services are oper up")
            else:
                log_file.error("Not all admin up services are oper up")
                phase_2_result = 'FAIL'

            ixia_100g.start_traffic()
            ixia_100g.clear_stats()

        elif action == 'isolate_node_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Isolate MLS 1")
            mls_1.to_wbx_spine_1.shutdown(snmp=True)
            mls_1.to_mls_2.shutdown(snmp=True)
            mls_1.to_hub_1.shutdown(snmp=True)

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

        elif action == 'sf_hub_1_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Cause a silent failure between HUB1 and MLS1")
            mls_1.send_cli_command('/configure filter ipv6-filter 39 default-action drop')
            mls_1.send_cli_command('/configure filter ip-filter 39 default-action drop')
            utils.countdown(10)

        elif action == 'sf_hub_2_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Cause a silent failure between HUB2 and MLS2")
            mls_2.send_cli_command('/configure filter ipv6-filter 129 default-action drop')
            mls_2.send_cli_command('/configure filter ip-filter 129 default-action drop')
            utils.countdown(10)

        elif action == 'fail_off_1_vpls':
            log_file.info("------------------------------")
            log_file.info("** Cause a silent failure between HUB1 and MLS1")
            log_file.info("Shutdown VPLS %s on Offload 1" %(off_1.off_vpls.id))
            off_1.off_vpls.shutdown()

        elif action == 'fail_off_2_vpls':
            log_file.info("------------------------------")
            log_file.info("** Cause a silent failure between HUB2 and MLS2")
            log_file.info("Shutdown VPLS %s on Offload 2" %(off_2.off_vpls.id))
            off_2.off_vpls.shutdown()

        elif action == 'sanity':
            log_file.info("------------------------------")
            log_file.info("** Sanity test. No fail action")
            log_file.info("------------------------------")

        elif action == 'fail_sr1_hub_1_lag_to_mls_1':
            log_file.info("------------------------------")
            log_file.info("** Shutdown MLS1 to SR1 HUB 1 Lag")
            mls_1.to_sr1_hub_1_10.shutdown(snmp=True)
            utils.countdown(10)

        elif action == 'fail_sr1_hub_2_lag_to_mls_2':
            log_file.info("------------------------------")
            log_file.info("** Shutdown MLS2 to SR1 HUB 2 Lag")
            mls_2.to_sr1_hub_2_10.shutdown(snmp=True)
            utils.countdown(10)

        else:
            log_file.info("-----------------------------")
            log_file.info("** Undefined test case action")
            log_file.info("-----------------------------")
            log_file.info("")
            log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
            ixia_100g.stop_traffic()
            return 'FAIL'

        utils.countdown(20)

        log_file.info("")
        log_file.info("-------------------------------------------------------------------")
        log_file.info("Phase 3: Look at port util, stop Ixia, collect & Analyze Ixia Stats")
        log_file.info("-------------------------------------------------------------------")
        log_file.info("")

        if 'reboot_node' not in action:
            print ""
            #show_all_port_util(testbed_nodes)
            #mls_1.show_log_99()

        # Stop Ixia stream
        log_file.info("Stop Ixia Traffic Stream %s" %(ixia_100g.traffic_names))
        ixia_100g.stop_traffic()
        log_file.info("")
        log_file.info("Get stats for all traffic items")
        log_file.info("--------------------------------------------------")
        ixia_100g.set_stats()
        log_file.info("")

        #Allan
        kpidict=OrderedDict()
        kpidict['KPIs'] = list()
        kpi = '.'.join([testcase_name,'loss_ms'])
        kpidict['KPIs'].append(kpi)

        # Empty list.  May still be populated by earlier action
        drill_down_names = []
        for traffic_item in ixia_100g.traffic_names:
            key = action + '-' + traffic_item 
            #loss_ms = ixia_100g.get_stats(traffic_item,'loss_ms')
            #kpidict['.'.join([kpi,traffic_item])] = loss_ms
            if ixia_100g.get_stats(traffic_item,'rx') > ixia_100g.get_stats(traffic_item,'tx'):
                log_file.error("Phase 3: Traffic item %s Rx > Tx !" %(traffic_item))
                phase_3_result = 'FAIL'
            else:
                loss_ms = ixia_100g.get_stats(traffic_item,'loss_ms')
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
            log_file.info("Phase 3 Drill Down per IPv6 traffic class stats for streams with loss")
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


            log_file.info("--------------------------------------------------------------")
            log_file.info("Drill Down per source / destination pair for error streams")
            log_file.info("--------------------------------------------------------------")
            for drill_down_name in drill_down_names:
                log_file.info("")
                # Polling ixia too quickly gives result from last poll
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
        log_file.info("--------------------------------------------------")
        log_file.info("Phase 4: Recover Failure")
        log_file.info("--------------------------------------------------")
        log_file.info("")

        if mls_1.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result == 'FAIL'
        else:
            log_file.info("Valid standby on MLS 1")

        if mls_2.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result == 'FAIL'
        else:
            log_file.info("Valid standby on MLS 2")

        if hub_1.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result == 'FAIL'
        else:
            log_file.info("Valid standby on Hub 1")

        if hub_2.wait_for_valid_standby_cpm(standby_wait) != 'OK':
            phase_4_result == 'FAIL'
        else:
            log_file.info("Valid standby on Hub 2")

        if topology == 'MLS':
            set_mode_mls_bg(mls_1, mls_2, off_1, off_2, hub_1, hub_2)
            if (check_mode_mls_bg(mls_1, mls_2, off_1, off_2, hub_1, hub_2) != 'OK'):
                phase_4_result == 'FAIL'

        elif topology == 'CRAN_OFF':
            set_mode_hub_with_offload()
            mls_1.send_cli_command('/configure filter ipv6-filter 39 default-action forward')
            mls_1.send_cli_command('/configure filter ip-filter 39 default-action forward')
            mls_2.send_cli_command('/configure filter ipv6-filter 129 default-action forward')
            mls_2.send_cli_command('/configure filter ip-filter 129 default-action forward')
            off_1.off_vpls.no_shutdown()
            off_2.off_vpls.no_shutdown()
            if not check_mode_hub_with_offload(): phase_4_result == 'FAIL'

        elif topology == 'CRAN_NO_OFF':
            set_mode_hub_no_offload()
            mls_1.send_cli_command('/configure filter ipv6-filter 39 default-action forward')
            mls_1.send_cli_command('/configure filter ip-filter 39 default-action forward')
            mls_2.send_cli_command('/configure filter ipv6-filter 129 default-action forward')
            mls_2.send_cli_command('/configure filter ip-filter 129 default-action forward')
            off_1.off_vpls.no_shutdown()
            off_2.off_vpls.no_shutdown()
            if not check_mode_hub_no_offload(): phase_4_result == 'FAIL'

        elif topology == 'SR1_CRAN_NO_OFF':
            set_mode_sr1_hub_no_offload()
            if not check_mode_sr1_hub_no_offload(): phase_4_result == 'FAIL'

        elif topology == 'NG_CRAN_NO_OFF':
            set_mode_ng_hub_no_offload(el_1, el_2, wbx_spine_1, wbx_spine_2, mls_1, mls_2, off_1, off_2, hub_1, hub_2)
            mls_1.send_cli_command('/configure filter ipv6-filter 39 default-action forward')
            mls_1.send_cli_command('/configure filter ip-filter 39 default-action forward')
            mls_2.send_cli_command('/configure filter ipv6-filter 129 default-action forward')
            mls_2.send_cli_command('/configure filter ip-filter 129 default-action forward')
            mls_1.ran_vprn.no_shutdown()
            mls_2.ran_vprn.no_shutdown()
            if not check_mode_ng_hub_no_offload(): phase_4_result = 'FAIL'

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

    wbx_89_tot = wbx_89.get_mem_current_total()
    wbx_89_use = wbx_89.get_mem_total_in_use()
    wbx_89_avl = wbx_89.get_mem_available()

    wbx_98_tot = wbx_98.get_mem_current_total()
    wbx_98_use = wbx_98.get_mem_total_in_use()
    wbx_98_avl = wbx_98.get_mem_available()

    log_file.info("")
    log_file.info("")
    log_file.info("WBX Pools (Bytes)")
    log_file.info("-----------------")
    log_file.info("WBX 89: Total %s | In Use %s | Available %s " %(wbx_89_tot,wbx_89_use,wbx_89_avl))
    log_file.info("WBX 98: Total %s | In Use %s | Available %s " %(wbx_98_tot,wbx_98_use,wbx_98_avl))
    log_file.info("")
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
        edn_results['mls_1_up']   = testbed_data['mls_1'].send_cli_command('show router 4 interface | match SRa8-Hub1 | match "Down/Up" | count ')
        edn_results['mls_1_down'] = testbed_data['mls_1'].send_cli_command('show router 4 interface | match SRa8-Hub2 | match "Down/Up" | count ')

        edn_results['mls_2_up']   = testbed_data['mls_2'].send_cli_command('show router 4 interface | match SRa8-Hub2 | match "Down/Up" | count ')
        edn_results['mls_2_down'] = testbed_data['mls_2'].send_cli_command('show router 4 interface | match SRa8-Hub1 | match "Down/Up" | count ')

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

    testbed_data['mls_1'].send_cli_command('/clear router 4 vrrp interface "SR1-CRAN-Hubs-BBU-OAM" ')

    while count <= wait_min:
        edn_check = True 
        edn_results['mls_1_down'] = testbed_data['mls_1'].send_cli_command('show router 4 interface | match SR1-CRAN-Hub | match "Down/Down" | count ')

        edn_results['mls_2_up']   = testbed_data['mls_2'].send_cli_command('show router 4 interface | match SR1-CRAN-Hub | match "Down/Up" | count ')

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
        res, cli_return = node.send_cli_command('show router route-table ipv6 %s' %(route))
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
