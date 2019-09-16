#!/usr/bin/env python3.7
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

tb  = attrdict.AttrDict()
topology = 'none'
byway = 'snmp'


def testbed_init(testbed_file):

    global tb
    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info('Initalize Testbed')
    log_file.info("--------------------------------------------------")

    if tb:
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info('Testbed already initialized')
        #return

    tb = node.Testbed(testbed_file, use_ixia=True)  #  !!!!!!!!!!!! Set use_ixia=False if you want to bypass ixia

def config_v4_underlay(status):

    tb.offload_1.send_cli_command('/configure router interface to-SP1 %s' %(status))
    tb.offload_1.send_cli_command('/configure router interface to-SP2 %s' %(status))

    tb.offload_2.send_cli_command('/configure router interface to-SP1 %s' %(status))
    tb.offload_2.send_cli_command('/configure router interface to-SP2 %s' %(status))

    tb.spine_1.send_cli_command('/configure router interface to-BL1 %s' %(status))
    tb.spine_1.send_cli_command('/configure router interface to-BL2 %s' %(status))
    tb.spine_1.send_cli_command('/configure router interface to-AL1 %s' %(status))
    tb.spine_1.send_cli_command('/configure router interface to-AL2 %s' %(status))

    tb.spine_2.send_cli_command('/configure router interface to-BL1 %s' %(status))
    tb.spine_2.send_cli_command('/configure router interface to-BL2 %s' %(status))
    tb.spine_2.send_cli_command('/configure router interface to-AL1 %s' %(status))
    tb.spine_2.send_cli_command('/configure router interface to-AL2 %s' %(status))

    tb.al_1.send_cli_command('/configure router interface to-SP1 %s' %(status))
    tb.al_1.send_cli_command('/configure router interface to-SP2 %s' %(status))
    tb.al_1.send_cli_command('/configure router interface to-H1 %s' %(status))

    tb.al_2.send_cli_command('/configure router interface to-SP1 %s' %(status))
    tb.al_2.send_cli_command('/configure router interface to-SP2 %s' %(status))
    tb.al_2.send_cli_command('/configure router interface to-H2 %s' %(status))


    tb.hub_1.send_cli_command('/configure router interface to-AL1 %s' %(status))
    tb.hub_1.send_cli_command('/configure router interface to-CA1 %s' %(status))
    tb.hub_2.send_cli_command('/configure router interface to-AL2 %s' %(status))
    tb.hub_2.send_cli_command('/configure router interface to-CA1 %s' %(status))

    tb.ca_1.send_cli_command('/configure router interface to-H1 %s' %(status))
    tb.ca_1.send_cli_command('/configure router interface to-H2 %s' %(status))

def isis_flat():

        tb.offload_1.send_cli_command('/configure router isis level-capability level-1/2')
        tb.offload_1.send_cli_command('/configure router isis area-id 49.0001')

        tb.offload_2.send_cli_command('/configure router isis level-capability level-1/2')
        tb.offload_2.send_cli_command('/configure router isis area-id 49.0001')

        tb.spine_1.send_cli_command('/configure router isis level-capability level-1/2')
        tb.spine_1.send_cli_command('/configure router isis area-id 49.0001')

        tb.spine_2.send_cli_command('/configure router isis level-capability level-1/2')
        tb.spine_2.send_cli_command('/configure router isis area-id 49.0001')

        tb.al_1.send_cli_command('/configure router isis level-capability level-1/2')
        tb.al_1.send_cli_command('/configure router isis area-id 49.0001')
        tb.al_1.send_cli_command('/configure router isis no area-id 49.0002')

        tb.al_2.send_cli_command('/configure router isis level-capability level-1/2')
        tb.al_2.send_cli_command('/configure router isis area-id 49.0001')
        tb.al_2.send_cli_command('/configure router isis no area-id 49.0002')

        tb.hub_1.send_cli_command('/configure router isis level-capability level-1/2')
        tb.hub_1.send_cli_command('/configure router isis area-id 49.0001')
        tb.hub_1.send_cli_command('/configure router isis no area-id 49.0002')

        tb.hub_2.send_cli_command('/configure router isis level-capability level-1/2')
        tb.hub_2.send_cli_command('/configure router isis area-id 49.0001')
        tb.hub_2.send_cli_command('/configure router isis no area-id 49.0002')

        tb.hub_1.send_cli_command('/configure router isis interface to-AL1 level-capability level-1/2')

def isis_boundary_on_access():

        tb.offload_1.send_cli_command('/configure router isis level-capability level-2')
        tb.offload_1.send_cli_command('/configure router isis area-id 49.0001')

        tb.offload_2.send_cli_command('/configure router isis level-capability level-2')
        tb.offload_2.send_cli_command('/configure router isis area-id 49.0001')

        tb.spine_1.send_cli_command('/configure router isis level-capability level-2')
        tb.spine_1.send_cli_command('/configure router isis area-id 49.0001')

        tb.spine_2.send_cli_command('/configure router isis level-capability level-2')
        tb.spine_2.send_cli_command('/configure router isis area-id 49.0001')

        tb.al_1.send_cli_command('/configure router isis level-capability level-1/2')
        tb.al_1.send_cli_command('/configure router isis area-id 49.0002')
        tb.al_1.send_cli_command('/configure router isis no area-id 49.0001')

        tb.al_2.send_cli_command('/configure router isis level-capability level-1/2')
        tb.al_2.send_cli_command('/configure router isis area-id 49.0002')
        tb.al_2.send_cli_command('/configure router isis no area-id 49.0001')

        tb.hub_1.send_cli_command('/configure router isis level-capability level-1')
        tb.hub_1.send_cli_command('/configure router isis area-id 49.0002')
        tb.hub_1.send_cli_command('/configure router isis no area-id 49.0001')

        tb.hub_2.send_cli_command('/configure router isis level-capability level-1')
        tb.hub_2.send_cli_command('/configure router isis area-id 49.0002')
        tb.hub_2.send_cli_command('/configure router isis no area-id 49.0001')

        tb.hub_1.send_cli_command('/configure router isis interface to-AL1 level-capability level-1/2')

def testbed_config(mode,underlay):

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("Testbed Name ...................... %s" %(tb.name))
    log_file.info("Testbed mode ...................... %s" %(mode))
    log_file.info("Underlay .......................... %s" %(underlay))
    log_file.info("--------------------------------------------------")

    # No plans for v6 underlay at the moment
    # Assume v4 config always present

    #if underlay == 'v4':
    #    config_v4_underlay('no shutdown')
    #elif underlay == 'v6':
    #    config_v4_underlay('shutdown')
    #else:
    #    log_file.info("Leave underlay unchanged")


    if mode == 'flat_access_no_vprn':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("ISIS  : Flat")
        log_file.info("VPRNs : MTSO Exit and CRAN Hub")
        log_file.info("--------------------------------------------------")
        #isis_flat()
        #tb.al_1.ran_vprn.shutdown()
        #tb.al_2.ran_vprn.shutdown()
        tb.hub_1.ran_vprn.no_shutdown()
        tb.hub_2.ran_vprn.no_shutdown()
    elif mode == 'flat_access_vprn':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("ISIS  : Flat")
        log_file.info("VPRNs : MTSO Exit, MTSO Access and CRAN Hub")
        log_file.info("--------------------------------------------------")
        #isis_flat()
        tb.al_1.ran_vprn.no_shutdown()
        tb.al_2.ran_vprn.no_shutdown()
        tb.hub_1.ran_vprn.no_shutdown()
        tb.hub_2.ran_vprn.no_shutdown()
    elif mode == 'access_no_vprn':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("ISIS  : Instances")
        log_file.info("VPRNs : MTSO Exit and CRAN Hub")
        log_file.info("--------------------------------------------------")
        #isis_boundary_on_access()
        #tb.al_1.ran_vprn.shutdown()
        #tb.al_2.ran_vprn.shutdown()
        #tb.hub_1.ran_vprn.no_shutdown()
        #tb.hub_2.ran_vprn.no_shutdown()
    elif mode == 'access_vprn':
        log_file.info("")
        log_file.info("--------------------------------------------------")
        log_file.info("ISIS  : Instances")
        log_file.info("VPRNs : MTSO Exit, MTSO Access and CRAN Hub")
        log_file.info("--------------------------------------------------")
        #isis_boundary_on_access()
        tb.al_1.ran_vprn.no_shutdown()
        tb.al_2.ran_vprn.no_shutdown()
        tb.hub_1.ran_vprn.no_shutdown()
        tb.hub_2.ran_vprn.no_shutdown()

def print_testbed_info():

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("Testbed Info")
    log_file.info("Exit Leaf 1 chassis type ................ %s" %(tb.offload_1.get_chassis_type()))
    log_file.info("Exit Leaf 1 Active CPM software version . %s" %(tb.offload_1.get_active_cpm_sw_version()))
    log_file.info("Exit Leaf 2 chassis type ................ %s" %(tb.offload_2.get_chassis_type()))
    log_file.info("Exit Leaf 2 Active CPM software version . %s" %(tb.offload_2.get_active_cpm_sw_version()))
    log_file.info("--------------------------------------------------")

def show_north_traffic_util():

    off1_to_mls1_tx  = round(tb.offload_1.to_mls_1.get_util_perc('tx'),2)
    off2_to_mls2_tx  = round(tb.offload_2.to_mls_2.get_util_perc('tx'),2)

    off1_to_hub1_tx  = round(tb.offload_1.to_hub1.get_util_perc('tx'),2)
    off2_to_hub2_tx  = round(tb.offload_2.to_hub2.get_util_perc('tx'),2)

    hub1_to_ixr_tx  = round(tb.hub_1.to_ixr.get_util_perc('tx'),2)
    hub2_to_ixr_tx  = round(tb.hub_2.to_ixr.get_util_perc('tx'),2)

    hub1_to_hub2_tx  = round(tb.hub_1.to_hub_2.get_util_perc('tx'),2)
    hub2_to_hub1_tx  = round(tb.hub_2.to_hub_1.get_util_perc('tx'),2)

    mls1_to_mls2_edn_tx  = round(tb.mls_1.to_mls_2_edn_vprn.get_util_perc('tx'),2)
    mls2_to_mls1_edn_tx  = round(tb.mls_2.to_mls_1_edn_vprn.get_util_perc('tx'),2)

    mls1_to_mls2_ran_tx  = round(tb.mls_1.to_mls_2_base.get_util_perc('tx'),2)
    mls2_to_mls1_ran_tx  = round(tb.mls_2.to_mls_1_base.get_util_perc('tx'),2)

    log_fmt_a = ' ||{:>22}{:>23}'
    log_fmt_b = ' ||{:>27}{:>13}'
    log_fmt_c = ' ||{:>30}{:>5}'

    log_file.info(" Northbound traffic flow" )
    log_file.info(" Percent link utilization" )
    log_file.info("")
    log_file.info("------------------------" )
    log_file.info("" )
    log_file.info(" ^^")
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                 | MLS1 |E-%3s   %3s-E| MLS2 |       E=EDN" %(mls1_to_mls2_edn_tx,mls2_to_mls1_edn_tx))
    log_file.info(" ||                 |      |--%3s   %3s--|      |" %(mls1_to_mls2_ran_tx,mls2_to_mls1_ran_tx))
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                    |                      |" )
    log_file.info(log_fmt_a.format(off1_to_mls1_tx,off2_to_mls2_tx))
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                 | OFF1 |               | OFF2 | " )
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                    |                      |" )
    log_file.info(log_fmt_a.format(off1_to_hub1_tx,off2_to_hub2_tx))
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                 +------+               +-----+ " )
    log_file.info(" ||                 | HUB1 |--%s   %s--| HUB2 |" %(hub1_to_hub2_tx,hub2_to_hub1_tx))
    log_file.info(" ||                 +------+               +------+" )
    log_file.info(" ||                         \              /" )
    log_file.info(log_fmt_b.format(hub1_to_ixr_tx,hub2_to_ixr_tx))
    log_file.info(" ||                            \         /" )
    log_file.info(" ||                             +-------+" )
    log_file.info(" ||                             |  IXR  |" )
    log_file.info(" ||                             +-------+" )
    log_file.info(" ||                                 |" )
    log_file.info("" )

def show_south_traffic_util():
    off1_to_mls1_rx  = round(tb.offload_1.to_mls_1.get_util_perc('rx'),2)
    off2_to_mls2_rx  = round(tb.offload_2.to_mls_2.get_util_perc('rx'),2)

    off1_to_hub1_rx  = round(tb.offload_1.to_hub1.get_util_perc('rx'),2)
    off2_to_hub2_rx  = round(tb.offload_2.to_hub2.get_util_perc('rx'),2)

    hub1_to_ixr_rx  = round(tb.hub_1.to_ixr.get_util_perc('rx'),2)
    hub2_to_ixr_rx  = round(tb.hub_2.to_ixr.get_util_perc('rx'),2)

    hub1_to_hub2_rx  = round(tb.hub_1.to_hub_2.get_util_perc('rx'),2)
    hub2_to_hub1_rx  = round(tb.hub_2.to_hub_1.get_util_perc('rx'),2)

    mls1_to_mls2_edn_rx  = round(tb.mls_1.to_mls_2_edn_vprn.get_util_perc('rx'),2)
    mls2_to_mls1_edn_rx  = round(tb.mls_2.to_mls_1_edn_vprn.get_util_perc('rx'),2)

    mls1_to_mls2_ran_rx  = round(tb.mls_1.to_mls_2_base.get_util_perc('rx'),2)
    mls2_to_mls1_ran_rx  = round(tb.mls_2.to_mls_1_base.get_util_perc('rx'),2)

    log_fmt_a = ' ||{:>22}{:>23}'
    log_fmt_b = ' ||{:>27}{:>13}'
    log_fmt_c = ' ||{:>30}{:>5}'

    log_file.info(" Southbound traffic flow" )
    log_file.info(" Percent link utilization" )
    log_file.info("")
    log_file.info("------------------------" )
    log_file.info("" )
    log_file.info(" ||")
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                 | MLS1 |E-%3s   %3s-E| MLS2 |       E=EDN" %(mls1_to_mls2_edn_rx,mls2_to_mls1_edn_rx))
    log_file.info(" ||                 |      |--%3s   %3s--|      |" %(mls1_to_mls2_ran_rx,mls2_to_mls1_ran_rx))
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                    |                      |" )
    log_file.info(log_fmt_a.format(off1_to_mls1_rx,off2_to_mls2_rx))
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                 | OFF1 |               | OFF2 | " )
    log_file.info(" ||                 +------+               +------+ " )
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                    |                      |" )
    log_file.info(log_fmt_a.format(off1_to_hub1_rx,off2_to_hub2_rx))
    log_file.info(" ||                    |                      |" )
    log_file.info(" ||                 +------+               +-----+ " )
    log_file.info(" ||                 | HUB1 |--%s   %s--| HUB2 |" %(hub1_to_hub2_rx,hub2_to_hub1_rx))
    log_file.info(" ||                 +------+               +------+" )
    log_file.info(" ||                         \              /" )
    log_file.info(log_fmt_b.format(hub1_to_ixr_rx,hub2_to_ixr_rx))
    log_file.info(" ||                            \         /" )
    log_file.info(" ||                             +-------+" )
    log_file.info(" ||                             |  IXR  |" )
    log_file.info(" ||                             +-------+" )
    log_file.info(" ||                                 |" )
    log_file.info(" \/" )

def set_all_port_ether_stats_itvl(itvl=300):

    log_file.info("Set util-stats-interval on all testbed ports to %s seconds" %(itvl))
    #for nx in tb.node_dict.values():
    #    if not nx.sysname: nx.sysname = nx.get_system_name()
    #    if "IXR" not in nx.sysname:
    #        for px in nx.port_dict.values() :
    #            px.set_ether_stats_interval(itvl)

def print_test_result(testcase_name, test_pass, duration):

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("Testcase: %s " %(testcase_name))
    log_file.info("Duration: %s seconds" %(str(duration)))
    log_file.info("")
    if test_pass: 
        log_file.info("Result: PASS")
    else:
        log_file.error("Result: FAIL")
    log_file.info("--------------------------------------------------")


def generate_test_result_list(testcase_name,test_pass):

    test_result_list = [] 
    if test_pass:
        test_result = 'PASS'
    else:
        test_result = 'FAIL'

    test_result_list.append(test_result)
    #test_result_dict = {} 
    #test_result_list.append(test_result_dict)

    kpidict=OrderedDict()
    kpidict['KPIs'] = list()
    kpi = '.'.join([testcase_name,'loss_ms'])
    kpidict['KPIs'].append(kpi)
    for traffic_item in tb.ixia_seg_rtg_offload.traffic_names:
        if 'Multicast' in traffic_item:
            log_file.info("Skip Multicast loss ms plot")
        else:
            loss_ms = tb.ixia_seg_rtg_offload.get_stats(traffic_item,'loss_ms')
            kpidict['.'.join([kpi,traffic_item])] = loss_ms

    test_result_list.append(kpidict)

    return test_result_list

def sanity():

    result = True
    return result

def fail_offload1_to_hub1():

    result = True
    tb.offload_1.to_hub1.shutdown(opt=byway)
    return result

def fail_offload2_to_hub2():

    result = True
    tb.offload_2.to_hub2.shutdown(opt=byway)
    return result

def fail_offload1_to_mls_1():

    result = True

    tb.offload_1.to_mls_1.shutdown(opt=byway)
    return result

def fail_offload2_to_mls_2():

    result = True

    tb.offload_2.to_mls_2.shutdown(opt=byway)
    return result

def fail_hub_2_to_ixr():

    result = True

    tb.hub_2.to_ixr.shutdown(opt=byway)
    return result

def fail_mls1_to_pe():
    result = True

    tb.mls_1.to_pe.shutdown(opt=byway)
    return result
    
def fail_mls2_to_pe():
    result = True

    tb.mls_2.to_pe.shutdown(opt=byway)
    return result

def reboot_offload1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Offload 1")
    log_file.info("-----------------------------------")

    tb.offload_1.sr_reboot()
    tb.offload_1.close()
    return result

def reboot_offload2():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Offload 2")
    log_file.info("-----------------------------------")

    tb.offload_1.sr_reboot()
    tb.offload_1.close()
    return result

def reboot_hub_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Hub 1")
    log_file.info("-----------------------------------")

    tb.hub_1.sr_reboot()
    tb.hub_1.close()
    return result

def reboot_hub_2():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Hub 2")
    log_file.info("-----------------------------------")

    tb.hub_2.sr_reboot()
    tb.hub_2.close()
    return result

def isolate_offload_1():

    log_file.info("-----------------------------------")
    log_file.info("Isolate Border Leaf 1")
    log_file.info("-----------------------------------")

    tb.offload_1.to_mls_1_vxlan.shutdown(opt=byway)
    tb.offload_1.to_hub1.shutdown(opt=byway)
    
    result = True
    return result

def isolate_offload_2():

    log_file.info("-----------------------------------")
    log_file.info("Isolate Border Leaf 2")
    log_file.info("-----------------------------------")

    tb.offload_2.to_mls_2_vxlan.shutdown(opt=byway)
    tb.offload_2.to_hub2.shutdown(opt=byway)
    
    result = True
    return result

def isolate_hub_1():

    log_file.info("-----------------------------------")
    log_file.info("Isolate Hub 1")
    log_file.info("-----------------------------------")

    tb.hub_1.to_offload_1.shutdown(opt=byway)
    #tb.hub_1.to_hub_2.shutdown(opt=byway)
    tb.hub_1.to_ixr.shutdown(opt=byway)
    result = True
    return result

def isolate_hub_2():

    log_file.info("-----------------------------------")
    log_file.info("Isolate Hub 2")
    log_file.info("-----------------------------------")

    tb.hub_2.to_offload_2.shutdown(opt=byway)
    #tb.hub_2.to_hub_1.shutdown(opt=byway)
    tb.hub_2.to_ixr.shutdown(opt=byway)
    result = True
    return result

def check_edn_vrrp_master_on_hub1():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Check EDN VRRP Master For IXR-S on Hub1")
    log_file.info("--------------------------------------------------------")
    if not tb.hub_1.Is_VRRP_Master('SR-IXR-CRAN-Hubs-BBU-OAM_2',44):
        result = False
    return result

def check_edn_vrrp_master_on_hub2():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Check EDN VRRP Master For IXR-S on Hub2")
    log_file.info("--------------------------------------------------------")
    if not tb.hub_2.Is_VRRP_Master('SR-IXR-CRAN-Hubs-BBU-OAM_2',44):
        result = False
    return result

def fail_vrrp_edn_hub_to_ixr():

    result = True

    #tb.hub_1.to_ixr.shutdown(opt=byway)
    if not check_edn_vrrp_master_on_hub1():
      if not check_edn_vrrp_master_on_hub2():
        log_file.info("ERROR:  NO VRRP MASTER ON EDN")
        result = False
      else:
        log_file.info("EDN VRRP Master on Hub2")
        tb.hub_2.to_ixr.shutdown(opt=byway)
    else:
        log_file.info("EDN VRRP Master on Hub1")
        tb.hub_1.to_ixr.shutdown(opt=byway)
    return result

def check_ran_vrrp_master_on_hub1():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Check RAN VRRP Master For IXR-S on Hub1")
    log_file.info("--------------------------------------------------------")
    if not tb.hub_1.Is_VRRP_Master('To-IXR-S-DH-2',55):
        result = False
    return result

def check_ran_vrrp_master_on_hub2():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Check RAN VRRP Master For IXR-S on Hub2")
    log_file.info("--------------------------------------------------------")
    if not tb.hub_2.Is_VRRP_Master('To-IXR-S-DH-2',55):
        result = False
    else:
        result = True
    return result

def fail_vrrp_ran_hub_to_ixr():

    result = True

    if not check_ran_vrrp_master_on_hub1():
      if not check_ran_vrrp_master_on_hub2():
          log_file.info("ERROR:  NO VRRP MASTER ON RAN")
          result = False
      else:
          log_file.info("RAN VRRP Master on Hub2")
          tb.hub_2.to_ixr.shutdown(opt=byway)
    else:
        log_file.info("RAN VRRP Master on Hub1")
        tb.hub_1.to_ixr.shutdown(opt=byway)
    return result

def silent_failure_10s_hub1():
    result = True
    if not tb.hub_1.l2_silent_failure(163,10):
        result = False
    return result

def silent_failure_10s_hub2():
    result = True
    if not tb.hub_2.l2_silent_failure(164,10):
        result = False
    return result

def silent_failure_60s_hub1():
    result = True
    if not tb.hub_1.l2_silent_failure(163,10):
        result = False
    return result

def silent_failure_60s_hub2():
    result = True
    if not tb.hub_2.l2_silent_failure(164,10):
        result = False
    return result

def ran_vprn_shut_offload1():
    result = True
    if not tb.offload_1.flap_vprn(1,10):
        result = False
    return result

def ran_vprn_shut_offload2():
    result = True
    if not tb.offload_2.flap_vprn(1,10):
        result = False
    return result

def edn_vprn_shut_offload1():
    result = True
    if not tb.offload_1.flap_vprn(4,10):
        result = False
    return result

def edn_vprn_shut_offload2():
    result = True
    if not tb.offload_2.flap_vprn(4,10):
        result = False
    return result

def ran_flap_bgp_offload1():
    result = True
    if not tb.offload_1.flap_bgp(1,10):
        result = False
    return result

def ran_flap_bgp_offload2():
    result = True
    if not tb.offload_2.flap_bgp(1,10):
        result = False
    return result

def edn_flap_bgp_offload2():
    result = True
    if not tb.offload_2.flap_bgp(4,10):
        result = False
    return result

def edn_flap_bgp_offload1():
    result = True
    if not tb.offload_1.flap_bgp(4,10):
        result = False
    return result

def base_bgp_flap_hub1():
    result = True
    if not tb.hub_1.flap_bgp(0,10):
        result = False
    return result

def base_bgp_flap_hub2():
    result = True
    if not tb.hub_2.flap_bgp(0,10):
        result = False
    return result

def restore_base_set_up():

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("No shutdown all ports")
    log_file.info("-----------------------------------")
    for nx in tb.node_dict.values():
        for px in nx.port_dict.values() :
            print (px.name)
            px.no_shutdown(opt=byway,verbose=False)

def check_base_set_up(wait):

    result = True
    count = 0

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Check ports")
    log_file.info("-----------------------------------")
    log_file.info("Wait up to %s seconds for all testbed ports to come oper up" %(wait))
    while count <= wait:
        result = True 
        for nx in tb.node_dict.values():
            for px in nx.port_dict.values() :
                port_oper_status  = px.get_port_info('oper', verbose=True)
                if port_oper_status == 'down':
                    print (px.name)
                    result = False 
        if result:
            log_file.info("All Port Oper Up After %s seconds" %(count))
            break
        else:
            count +=1
            time.sleep(1)
            log_file.info("")

    return result

def check_bgp_underlay():
    result = True
    if not tb.offload_1.verify_bgp_underlay("to-IEN-Hub5",90):
        log_file.error("--------------------------------------------")
        log_file.error('BGP Underlay to-IEN-Hub5 on Offload1 is DOWN')
        log_file.error("--------------------------------------------")
        result = False
    if not tb.offload_1.verify_bgp_underlay("to-IEN-Hub6",60):
        log_file.error("--------------------------------------------")
        log_file.error('BGP Underlay to-IEN-Hub6 on Offload1 is DOWN')
        log_file.error("--------------------------------------------")
        result = False
    if not tb.offload_2.verify_bgp_underlay("to-IEN-Hub5",60):
        log_file.error("--------------------------------------------")
        log_file.error('BGP Underlay to-IEN-Hub5 on Offload2 is DOWN')
        log_file.error("--------------------------------------------")
        result = False
    if not tb.offload_2.verify_bgp_underlay("to-IEN-Hub6",60):
        log_file.error("--------------------------------------------")
        log_file.error('BGP Underlay to-IEN-Hub6 on Offload2 is DOWN')
        log_file.error("--------------------------------------------")
        result = False
    return result

def check_mda_state():
    result = True
    if not tb.offload_1.verify_mda_state(1,1):
        log_file.error("--------------------------")
        log_file.error('MDA 1/1 is in Failed State')
        log_file.error("--------------------------")
        result = False
    if not tb.offload_1.verify_mda_state(1,2):
        log_file.error("--------------------------")
        log_file.error('MDA 1/2 is in Failed State')
        log_file.error("--------------------------")
        result = False
    if not tb.offload_2.verify_mda_state(1,1):
        log_file.error("--------------------------")
        log_file.error('MDA 1/1 is in Failed State')
        log_file.error("--------------------------")
        result = False
    if not tb.offload_2.verify_mda_state(1,2):
        log_file.error("--------------------------")
        log_file.error('MDA 1/2 is in Failed State')
        log_file.error("--------------------------")
        result = False
    return result

def check_isis_adjacency():
    result = True
    if not tb.offload_1.wait_isis_adjacency_up('base',1,30,3):
        result = False
    if not tb.offload_2.wait_isis_adjacency_up('base',1,30,3):
        result = False 
    if not tb.hub_1.wait_isis_adjacency_up('base',1,30,3):
        result = False
    if not tb.hub_2.wait_isis_adjacency_up('base',1,30,3):
        result = False
    return result

def check_stats(max_outage,testcase_name):

    result = True

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("Get stats for all traffic items")
    log_file.info("--------------------------------------------------")

    tb.ixia_seg_rtg_offload.set_stats()

    for traffic_item in tb.ixia_seg_rtg_offload.traffic_names:
        if tb.ixia_seg_rtg_offload.get_stats(traffic_item,'rx') > tb.ixia_seg_rtg_offload.get_stats(traffic_item,'tx'):
            if 'Multicast' in traffic_item:
                log_file.info("Multicast Traffic item %s Rx > Tx !" %(traffic_item))
                log_file.info("Multicast Traffic item %s Pass" %(traffic_item))
                log_file.info("")
            else:
                log_file.error("Unicast Traffic item %s Rx > Tx !" %(traffic_item))
                log_file.error("Unicast Traffic item %s Fail" %(traffic_item))
                log_file.error("")
                result = False
        else:
            loss_ms = tb.ixia_seg_rtg_offload.get_stats(traffic_item,'loss_ms')
            if loss_ms > max_outage:
                if testcase_name == 'reboot_hub_1_access_no_vprn' or testcase_name == 'reboot_hub_1_access_vprn':
                    if 'Hub-1' in traffic_item:
                        log_file.info("Traffic item %s Loss of %s ms > %s ms" %(traffic_item, loss_ms, max_outage))
                        log_file.info("But HUB 1 rebooted ... so outage OK")
                        log_file.info("Traffic item %s Pass" %(traffic_item))
                elif testcase_name == 'isolate_hub_1_access_no_vprn' or testcase_name == 'isolate_hub_1_access_vprn':
                        log_file.info("Traffic item %s Loss of %s ms > %s ms" %(traffic_item, loss_ms, max_outage))
                        log_file.info("But HUB 1 isolated ... so outage OK")
                        log_file.info("Traffic item %s Pass" %(traffic_item))
                else:
                    log_file.error("Traffic item %s Loss of %s ms > %s ms" %(traffic_item, loss_ms, max_outage))
                    log_file.error("Traffic item %s Fail" %(traffic_item))
                    log_file.error("")
                    result = False
            else:
                log_file.info("Traffic item %s Loss of %s ms < %s ms" %(traffic_item, loss_ms, max_outage))
                log_file.info("Traffic item %s Pass" %(traffic_item))
                log_file.info("")
    
    return result


def check_all_ports_for_errors():

    log_fmt = '{:<25} {:<20} {:<20}'
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Check all ports for errors")
    log_file.info("-----------------------------------")
    for nx in tb.node_dict.values():
        log_file.info("Node %s" %(nx.sysname))
        log_file.info("Port                      Tx-Errors            Rx-Errors")
        for px in nx.port_dict.values():
            tx_error = px.get_port_tx_errors()
            rx_error = px.get_port_rx_errors()
            log_file.info(log_fmt.format(px.name, tx_error, rx_error))
        log_file.info("")
            
def check_all_port_util():

    log_fmt = '{:<25} {:<20} {:<20}'
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Check all port utilization")
    log_file.info("-----------------------------------")
    for nx in tb.node_dict.values():
        log_file.info("Node %s" %(nx.sysname))
        log_file.info("Port                      Tx-Util            Rx-Util")
        for px in nx.port_dict.values():
            tx_util = px.get_port_tx_unicast_utilization()
            rx_util = px.get_port_rx_unicast_utilization()
            log_file.info(log_fmt.format(px.name, tx_util, rx_util))
        log_file.info("")
            
def ping_all_nodes():

    ping_result = True
    for nx in tb.node_dict.values():
        if not nx.ping():
            log_file.error("Ping to %s failed" %(nx.name))
            ping_result = False

    return ping_result

def main(testcase_name='sanity_access_no_vprn',testsuite_name='vzw_seg_rtg_offload',csv='false',testbed_file='vzw_seg_rtg_offload.yaml'):

    test_pass                  = True 
    #test_path                 = '/automation/python/tests/'
    #testbed_file              = test_path+testbed_file
    port_wait                  = 120
    underlay                   = 'v4'
    max_outage_sanity          = 0
    max_outage_default         = 750
    max_outage_mls_link_fail   = 3000
    max_outage_reboot          = 3500
    max_outage_edn_host_switch = 2000
    max_outage_vprn_fail       = 2000
    max_outage_vrrp_fail       = 2000
    wait_after_reboot          = 360

    test_result_list = []

    # Initialize the testbed
    testbed_init(testbed_file)

    # Print testbed info
    print_testbed_info()

    
    # Set testbed mode based on testcase name
    #if 'access_no_vprn' in testcase_name:
    #    mode = 'access_no_vprn'
    #elif 'access_vprn' in testcase_name:
    #    mode = 'access_vprn'
    #else:
    #    log_file.error("Can't find testbed mode .. assume no VPRNs on access nodes")
    #    mode = 'access_no_vprn'
    #testbed_config(mode,underlay)

    set_all_port_ether_stats_itvl(30)

    print ("!!!!!!!!!!!! PLEASE NOTE: ADMIN SAVE IS CURRENTLY NOT DONE DURING SCRIPT RUN !!!!!!!!!");
    #log_file.info("")
    #log_file.info("-----------------------------------")
    #log_file.info("Perform admin save on all node")
    #log_file.info("-----------------------------------")
    #tb.offload_1.admin_save()
    #tb.offload_2.admin_save()
    #tb.hub_1.admin_save()
    #tb.hub_2.admin_save()
    #tb.vc.admin_save()

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Test suite   : %s" %(testsuite_name))
    log_file.info("Test case    : %s" %(testcase_name))
    log_file.info("-----------------------------------")

    # Start the clock 
    start_time = datetime.now()

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info('Bring all testbed ports up')
    log_file.info("-----------------------------------")
    restore_base_set_up() 

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info('Check all expected ports are up')
    log_file.info("-----------------------------------")
    if not check_base_set_up(30): 
        test_pass = False
        log_file.error("")
        log_file.error("-------------------------------------")
        log_file.error('Base set up check failed - ports down')
        log_file.error("-------------------------------------")

    log_file.info("")
    log_file.info("---------------------------------------")
    log_file.info('Check ISIS adjacencies and BGP Underlay')
    log_file.info("---------------------------------------")    
    if not check_isis_adjacency():
        test_pass = False
    if not check_bgp_underlay():
        test_pass = False

    if not check_mda_state():
        test_pass = False

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info('Check all nodes for hw errors')
    log_file.info("-----------------------------------")
    for error_node in tb.node_dict.values():
        error_node.check_for_hw_errors()
            
    log_file.info("")
    log_file.info("---------------------")
    log_file.info('     Check PIM       ')
    log_file.info("---------------------")
    if not tb.hub_1.wait_pim_resolved(tb.hub_1.ran_vprn.id,'ipv6',60): 
        if not tb.hub_2.wait_pim_resolved(tb.hub_2.ran_vprn.id,'ipv6',60): 
            test_pass = False
        else:
            log_file.info(' -----> PIM resolved on Hub 2. ')
            tb.hub_1.send_cli_command('show router %s pim group %s' %(tb.hub_1.ran_vprn.id,'ipv6'), see_return=True)            
    else:
        log_file.info(' -----> PIM resolved on Hub 1. ')
        tb.hub_1.send_cli_command('show router %s pim group %s' %(tb.hub_1.ran_vprn.id,'ipv6'), see_return=True)

    log_file.info("")
    log_file.info("------------------------------------------")
    log_file.info('Look at the number of BGP routes')
    log_file.info("------------------------------------------")
    tb.offload_1.send_cli_command('show router bgp summary neighbor 1.1.0.51 |  match Summary post-lines 13' , see_return=True)

    log_file.info("------------------------------------------")
    log_file.info('Ping all nodes ')
    log_file.info("------------------------------------------")
    if not ping_all_nodes(): 
        log_file.error("-------------------")
        log_file.error('Ping Tests Failed .')
        log_file.error("-------------------")
        test_pass = False

    if not test_pass:
        log_file.error("")
        log_file.error("----------------------------------------")
        log_file.error("Initial checks did not pass.  Skip test.")
        log_file.error("----------------------------------------")

        test_result = 'FAIL'

        test_result_list.append(test_result)

        # Stop the clock 
        end_time = datetime.now()
        test_dur = end_time - start_time
        duration = test_dur.total_seconds()

        # Print test result
        print_test_result(testcase_name,test_pass, duration)
  
        # Exit Main and Return FAIL !!!
        return test_result_list

    else:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Enable Ixia streams")
        log_file.info("-----------------------------------")
        #tb.ixia_seg_rtg_offload.set_traffic(pattern=ixia_pattern, commit=True)

        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Start Ixia streams")
        log_file.info("-----------------------------------")
        tb.ixia_seg_rtg_offload.start_traffic()
        
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Wait 10 secs after starting Ixia.  ")
        log_file.info("-----------------------------------")
        
        utils.countdown(10)
        log_file.info("")

        # Clear Ixia stats  
        tb.ixia_seg_rtg_offload.clear_stats()

        log_file.info("")
        log_file.info("-----------------------------------------")
        log_file.info("Wait 10 secs after clearing Ixia Stats...")
        log_file.info("-----------------------------------------")
        utils.countdown(10)

        # Show initial traffic flow 
        show_north_traffic_util()
        show_south_traffic_util()

        # Run the testcase 
        tmp_pattern = tb.ixia_seg_rtg_offload.pattern
        max_outage = max_outage_default
        
        # TODO - Change this to if 'xxx' in yyy
        if 'sanity_access' in testcase_name:
            max_outage = max_outage_sanity 
        
        #####  LINK FAILURE TESTS #########
        elif 'fail_offload1_to_hub_1' in testcase_name:
            if not fail_offload1_to_hub1(): test_pass = False 
        elif 'fail_offload2_to_hub_2' in testcase_name:
            if not fail_offload2_to_hub2(): test_pass = False 
        elif 'fail_offload1_to_mls_1' in testcase_name:
            max_outage = max_outage_mls_link_fail
            if not fail_offload1_to_mls_1(): test_pass = False
        elif 'fail_offload2_to_mls_2' in testcase_name:
            max_outage = max_outage_mls_link_fail
            if not fail_offload2_to_mls_2(): test_pass = False 
        elif 'fail_mls_1_to_pe' in testcase_name:
            max_outage = max_outage_mls_link_fail
            if not fail_mls1_to_pe(): test_pass = False
        elif 'fail_mls_2_to_pe' in testcase_name:
            max_outage = max_outage_mls_link_fail
            if not fail_mls2_to_pe(): test_pass = False 

        #####  REBOOT FAILURE TESTS #########
        elif 'reboot_offload1' in testcase_name:
            max_outage = max_outage_reboot 
            if not reboot_offload1(): test_pass = False  
        elif 'reboot_offload2' in testcase_name:
            max_outage = max_outage_reboot 
            if not reboot_offload1(): test_pass = False  
        elif 'reboot_hub1' in testcase_name:
            max_outage = max_outage_reboot 
            if not reboot_hub_1(): test_pass = False
        elif 'reboot_hub2' in testcase_name:
            max_outage = max_outage_reboot 
            if not reboot_hub_2(): test_pass = False  

        ################ IXR VRRP TESTS ################
        elif 'fail_vrrp_edn_hub_to_ixr' in testcase_name:
            max_outage = max_outage_vrrp_fail 
            if not fail_vrrp_edn_hub_to_ixr(): test_pass = False
        elif 'fail_vrrp_ran_hub_to_ixr' in testcase_name:
            max_outage = max_outage_vrrp_fail 
            if not fail_vrrp_ran_hub_to_ixr(): test_pass = False

        ################ SILENT FAILURES ###############
        elif 'silent_failure_10s_hub_1_to_offload1' in testcase_name:
            if not silent_failure_10s_hub1(): test_pass = False
        elif 'silent_failure_10s_hub_2_to_offload1' in testcase_name:
            if not silent_failure_10s_hub2(): test_pass = False
        elif 'silent_failure_60s_hub_1_to_offload1' in testcase_name:
            if not silent_failure_60s_hub1(): test_pass = False
        elif 'silent_failure_60s_hub_2_to_offload1' in testcase_name:
            if not silent_failure_60s_hub2(): test_pass = False

        ################ VPRN FLAP ###############
        elif 'ran_vprn_shut_offload1' in testcase_name:
            max_outage = max_outage_vprn_fail 
            if not ran_vprn_shut_offload1(): test_pass = False
        elif 'ran_vprn_shut_offload2' in testcase_name:
            max_outage = max_outage_vprn_fail 
            if not ran_vprn_shut_offload2(): test_pass = False 
        elif 'edn_vprn_shut_offload1' in testcase_name:
            max_outage = max_outage_vprn_fail 
            if not edn_vprn_shut_offload1(): test_pass = False
        elif 'edn_vprn_shut_offload2' in testcase_name:
            if not edn_vprn_shut_offload2(): test_pass = False

        ################ VPRN and BGP FLAP ###############
        elif 'ran_flap_bgp_offload1' in testcase_name:
            if not ran_flap_bgp_offload1(): test_pass = False
        elif 'ran_flap_bgp_offload2' in testcase_name:
            if not ran_flap_bgp_offload2(): test_pass = False        
        elif 'edn_flap_bgp_offload1' in testcase_name:
            if not edn_flap_bgp_offload1(): test_pass = False
        elif 'edn_flap_bgp_offload2' in testcase_name:
            if not edn_flap_bgp_offload2(): test_pass = False
        elif 'base_bgp_flap_hub1' in testcase_name:
            if not base_bgp_flap_hub1(): test_pass = False
        elif 'base_bgp_flap_hub2' in testcase_name:
            if not base_bgp_flap_hub2(): test_pass = False
        else:
            log_file.error("Testcase %s does not exist" %(testcase_name))
       
        # If a failure has been triggered - show resulting traffic flow 
        if 'reboot' not in testcase_name:
            if 'sanity' not in testcase_name:
                utils.countdown(60)
                log_file.info("")
                log_file.info("------------------------------------------")
                log_file.info('Traffic flow after network failure')
                log_file.info("------------------------------------------")
                
                show_north_traffic_util()
                show_south_traffic_util()

        # Stop the Ixia streams
        tb.ixia_seg_rtg_offload.stop_traffic()

        if 'reboot' in testcase_name:
            log_file.info('Reboot case')
            for nx in tb.node_dict.values():
               if not nx.wait_node_up(wait_after_reboot):
                   log_file.error ("Node %s ip %s not up after %s s" %(nx.sysname, nx.ip, wait_after_reboot))
            log_file.info("Nodes are back up.  But wont take CLI/SNMP commands for a while.  So wait.")    
            utils.countdown(240)

        # Restore all testcase failures 
        restore_base_set_up()
         
        if not check_base_set_up(60): 
            test_pass = False
            log_file.error("")
            log_file.error("--------------------------------------------------")
            log_file.error('Post-Failure Base set up check failed - ports down')
            log_file.error("--------------------------------------------------")

            test_result = 'FAIL'

            test_result_list.append(test_result)

            # Stop the clock 
            end_time = datetime.now()
            test_dur = end_time - start_time
            duration = test_dur.total_seconds()

            # Print test result
            print_test_result(testcase_name,test_pass, duration)
  
            # Exit Main and Return FAIL !!!
            return test_result_list

        log_file.info("")
        log_file.info("--------------------------")
        log_file.info('Post-Failure check of MDA ')
        log_file.info("---------------------------")   
        if not check_mda_state():
            test_pass = False

        log_file.info("")
        log_file.info("--------------------------------------")
        log_file.info('Post-Failure check of ISIS adjacencies')
        log_file.info("--------------------------------------")    
        if not check_isis_adjacency():
            test_pass = False
        
        log_file.info("")
        log_file.info("----------------------------------")
        log_file.info('Post-Failure check of BGP Underlay')
        log_file.info("----------------------------------")   
        if not check_bgp_underlay():
            test_pass = False

        log_file.info("")
        log_file.info("-----------------------")
        log_file.info('Post-Failure PIM Check ')
        log_file.info("-----------------------")
        if not tb.hub_1.wait_pim_resolved(tb.hub_1.ran_vprn.id,'ipv6',60): 
            if not tb.hub_2.wait_pim_resolved(tb.hub_2.ran_vprn.id,'ipv6',60): 
               test_pass = False
            else:
               log_file.info(' --------> PIM resolved on Hub 2. ')
               log_file.info("")
               tb.hub_1.send_cli_command('show router %s pim group %s' %(tb.hub_1.ran_vprn.id,'ipv6'), 
                    see_return=True)            
        else:
            log_file.info(' ----------> PIM resolved on Hub 1. ')
            log_file.info("")
            tb.hub_1.send_cli_command('show router %s pim group %s' %(tb.hub_1.ran_vprn.id,'ipv6'), 
                    see_return=True)
        
        log_file.info("")
        log_file.info("------------------------------------------------------------")
        log_file.info('Verify IPv6 Default for RAN and EDN on Offload1 and Offload2')
        log_file.info("------------------------------------------------------------")

        # Wait for both Offload's to see the default route for RAN from MLS
        if not tb.offload_1.wait_route_match('1','::/0',tb.offload_1.ran_vprn.def_nh,120): 
            test_pass = False
        if not tb.offload_2.wait_route_match('1','::/0',tb.offload_2.ran_vprn.def_nh,120): 
            test_pass = False
        
        #Wait for both Offload's to see the default route for EDN from MLS
        if not tb.offload_1.wait_route_match('4','::/0',tb.offload_1.edn_vprn.def_nh,120): 
            test_pass = False
        if not tb.offload_2.wait_route_match('4','::/0',tb.offload_2.edn_vprn.def_nh,120): 
            test_pass = False
        
        log_file.info("")
        log_file.info("----------------------------------------------------")
        log_file.info('Verify IPv6 Default for RAN and EDN on Hub1 and Hub2')
        log_file.info("----------------------------------------------------")

        # Wait for both hubs to see the default route from both BLs
        # Verify RAN Default Route on Hub
        if not tb.hub_1.wait_route_match('55','::/0',tb.hub_1.ran_vprn.def_nh,90): 
            test_pass = False
        if not tb.hub_2.wait_route_match('55','::/0',tb.hub_2.ran_vprn.def_nh,90): 
            test_pass = False
        
        # Verify EDN Default Route on Hub
        if not tb.hub_1.wait_route_match('44','::/0',tb.hub_1.edn_vprn.def_nh,90): 
            test_pass = False
        if not tb.hub_2.wait_route_match('44','::/0',tb.hub_2.edn_vprn.def_nh,90): 
            test_pass = False

        # Check the Ixia stats 
        if not check_stats(max_outage,testcase_name): 
            test_pass = False         
        
        # Stop the clock 
        end_time = datetime.now()
        test_dur = end_time - start_time
        duration = test_dur.total_seconds()
        
        # Print test result
        print_test_result(testcase_name,test_pass, duration)

        # Generate testlist
        test_result_list = generate_test_result_list(testcase_name,test_pass)

        utils.countdown(5)

        # close ssh connections
        for nx in tb.node_dict.values():
          nx.close()

        return test_result_list


if (__name__ == '__main__'):

    print("\n\nParsing input parameters...\n")

    # Get all user input command options
    try:
        optlist, args = getopt.getopt(sys.argv[1:],"t:s:c:h")
    except getopt.GetoptError as err:
        print("\nERROR: %s" %(err))
        sys.exit(0)

    test_params=dict()
    #test_params['testbed_mode'] = ''
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
            # enaoffloade csv stat logging
            test_params['csv'] = val
        else: 
            print("option: %s a is not implemented yet!!"%(opt,val))
            sys.exit() 
    
    # Check for mandatory arguements
    if test_params['testcase_name'] == '':
        print("\nERROR: Option -t (testcase) is mandatory")
        sys.exit()

    main(**test_params)
