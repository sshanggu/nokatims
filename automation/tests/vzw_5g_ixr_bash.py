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

# Create a log file
log_file=utils.get_logger(__name__)

tb=attrdict.AttrDict()
topology = 'none'


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

    tb = node.Testbed(testbed_file)

def port_bounce (side,loops = 1):

    loop = 1
    result = 'PASS'
    if side == 'remote':
        f_node = tb.dut_b
        f_port = tb.dut_b.local_port_1
        c_node = tb.dut_a
        c_port = tb.dut_a.local_port_1
    elif side == 'local':
        f_node = tb.dut_a
        f_port = tb.dut_a.local_port_1
        c_node = tb.dut_b
        c_port = tb.dut_b.local_port_1
    else:
        return 'FAIL'

    log_file.info("")
    log_file.info("Bounce port is %s to IXR" %(side))
    log_file.info("")
    log_file.info("Bounce node %s port %s %s times" %(f_node.sysname, f_port.name,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        f_port.shutdown(snmp=True)
        if not (f_port.wait_port_oper_down_ex(120)):
            log_file.error("Node %s port %s did NOT go oper down during bounce number %s" %(f_node.sysname, f_port.name,loop))
            result = 'FAIL'
        if not (c_port.wait_port_oper_down_ex(120)):
            log_file.error("Node %s port %s did NOT go oper down during bounce number %s" %(c_node.sysname, c_port.name,loop))
            result = 'FAIL'
        f_port.no_shutdown(snmp=True)
        if not (f_port.wait_port_oper_up_ex(120)):
            log_file.error("Node %s port %s did NOT come oper up during bounce number %s" %(f_node.sysname, f_port.name,loop))
            result = 'FAIL'
        if not (c_port.wait_port_oper_up_ex(120)):
            log_file.error("Node %s port %s did NOT come oper up during bounce number %s" %(c_node.sysname, c_port.name,loop))
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result


def lag_bounce (side,loops = 1):

    loop = 1
    result = 'PASS'

    if side == 'remote':
        f_node = tb.dut_b
        f_lag  = tb.dut_b.local_lag_1
        c_node = tb.dut_a
        c_lag  = tb.dut_a.local_lag_1
    elif side == 'local':
        f_node = tb.dut_a
        f_lag  = tb.dut_a.local_lag_1
        c_node = tb.dut_b
        c_lag  = tb.dut_b.local_lag_1
    else:
        return 'FAIL'

    log_file.info("")
    log_file.info("Bounce lag is %s to DUT-A" %(side))
    log_file.info("")
    log_file.info("Bounce node %s lag %s %s times" %(f_node.sysname, f_lag.name,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        f_lag.shutdown(snmp=True)
        if not (f_lag.wait_port_oper_down_ex(120)):
            log_file.error("Node %s lag %s did NOT go oper down during bounce number %s" %(f_node.sysname, f_lag.name,loop))
            result = 'FAIL'
        if not (c_lag.wait_port_oper_down_ex(120)):
            log_file.error("Node %s lag %s did NOT go oper down during bounce number %s" %(c_node.sysname, c_lag.name,loop))
            result = 'FAIL'
        f_lag.no_shutdown(snmp=True)
        if not (f_lag.wait_port_oper_up_ex(120)):
            log_file.error("Node %s lag %s did NOT come oper up during bounce number %s" %(f_node.sysname, f_lag.name,loop))
            result = 'FAIL'
        if not (c_lag.wait_port_oper_up_ex(120)):
            log_file.error("Node %s lag %s did NOT come oper up during bounce number %s" %(c_node.sysname, c_lag.name,loop))
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result


def vpls_bounce(loops = 1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Bounce node %s vpls %s %s times" %(tb.dut_a.sysname, tb.dut_a.vpls_1.id,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        tb.dut_a.vpls_1.shutdown()
        if not (tb.dut_a.vpls_1.wait_service_oper_down_ex(120)):
            log_file.error("Node %s service %s did NOT go oper down during bounce number %s" %(tb.dut_a.sysname, tb.dut_a.vpls_1.id,loop))
            result = 'FAIL'
        tb.dut_a.vpls_1.no_shutdown()
        if not (tb.dut_a.vpls_1.wait_service_oper_up_ex(120)):
            log_file.error("Node %s service %s did NOT go oper up during bounce number %s" %(tb.dut_a.sysname, tb.dut_a.vpls_1.id,loop))
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result


def vpls_add_delete(loops = 1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("On node %s add / delete a vpls %s times" %(tb.dut_a.sysname,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        tb.dut_a.send_cli_command("/configure service vpls %s customer 1 create no shutdown" %('999'))
        tb.dut_a.send_cli_command("/configure service vpls %s sap %s create no shutdown" %('999','1/1/c53/1:999'))
        tb.dut_a.send_cli_command("/configure service vpls %s sap %s shutdown" %('999','1/1/c53/1:999'))
        tb.dut_a.send_cli_command("/configure service vpls %s no sap %s" %('999','1/1/c53/1:999'))
        tb.dut_a.send_cli_command("/configure service vpls %s shutdown" %('999'))
        tb.dut_a.send_cli_command("/configure service no vpls %s" %('999'))
        utils.countdown(1)
        loop +=1
        log_file.info("")
    return result


def vpls_add_delete_many(loops = 1):

    loop = 1
    result = 'PASS'

    vpls_num = 9500
    sap_num  = 3500

    log_file.info("")
    log_file.info("On node %s add / delete a vpls %s times" %(tb.dut_a.sysname,loops))
    while not loop > loops:
        vpls_num = 9500
        sap_num  = 10
        vpls_num = vpls_num + loop
        sap_num  = sap_num + loop
        sap  = '1/1/c53/1:' + str(sap_num)
        log_file.info("Loop %s of %s" %(loop,loops))
        log_file.info("VPLS %s" %(vpls_num))
        log_file.info("SAP %s"  %(sap))
        tb.dut_a.send_cli_command("/configure service vpls %s customer 1 create no shutdown" %(vpls_num))
        tb.dut_a.send_cli_command("/configure service vpls %s sap %s create no shutdown" %(vpls_num,sap))
        loop +=1
        log_file.info("")

    loop = 1
    log_file.info("Done!")

    utils.countdown(30)

    while not loop > loops:
        vpls_num = 9500
        sap_num  = 10
        vpls_num = vpls_num + loop
        sap_num  = sap_num + loop
        sap  = '1/1/c53/1:' + str(sap_num)
        log_file.info("Loop %s of %s" %(loop,loops))
        log_file.info("VPLS %s" %(vpls_num))
        log_file.info("SAP %s"  %(sap))

        tb.dut_a.send_cli_command("/configure service vpls %s sap %s shutdown" %(vpls_num,sap))
        tb.dut_a.send_cli_command("/configure service vpls %s no sap %s" %(vpls_num,sap))
        tb.dut_a.send_cli_command("/configure service vpls %s shutdown" %(vpls_num))
        tb.dut_a.send_cli_command("/configure service no vpls %s" %(vpls_num))
        #utils.countdown(1)
        loop +=1
        log_file.info("")

    return result

def vpls_sap_bounce(loops = 1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Bounce node %s vpls %s sap %s %s times" %(tb.dut_a.sysname,tb.dut_a.vpls_1.id,tb.dut_a.vpls_1.sap_1,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        tb.dut_a.vpls_1.sap_1.shutdown()
        if not (tb.dut_a.vpls_1.sap_1.wait_sap_oper_down_ex(120)):
            log_file.error("Node %s sap %s did NOT go oper down during bounce number %s" %(tb.dut_a.sysname, tb.dut_a.vpls_1.id,loop))
            result = 'FAIL'
        tb.dut_a.vpls_1.sap_1.no_shutdown()
        if not (tb.dut_a.vpls_1.sap_1.wait_sap_oper_up_ex(120)):
            log_file.error("Node %s sap %s did NOT go oper up during bounce number %s" %(tb.dut_a.sysname, tb_dut_a.vpls_1.id,loop))
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result

def vpls_sap_add_delete(loops = 1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Bounce node %s vpls %s sap %s %s times" %(tb.dut_a.sysname,tb.dut_a.vpls_1.id,tb.dut_a.vpls_1.sap_1,loops))
    while not loop > loops:
        log_file.info("Loop %s" %(loop))
        tb.dut_a.send_cli_command("/configure service vpls %s sap %s create no shutdown" %(tb.dut_a.vpls_1.id,'1/1/c53/1:999'))
        tb.dut_a.send_cli_command("/configure service vpls %s sap %s shutdown" %(tb.dut_a.vpls_1.id,'1/1/c53/1:999'))
        tb.dut_a.send_cli_command("/configure service vpls %s no sap %s" %(tb.dut_a.vpls_1.id,'1/1/c53/1:999'))
        utils.countdown(1)
        loop +=1
        log_file.info("")
    return result


def bof_save(loops=1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Perform a bof save on %s %s times" %(tb.dut_a.sysname,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        if not (tb.dut_a.bof_save()):
            result = 'FAIL'
        if not (tb.dut_a.check_bof_save()):
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result


def admin_save(loops=1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Perform an admin save on %s %s times" %(tb.dut_a.sysname,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        if not (tb.dut_a.admin_save()):
            result = 'FAIL'
        if not (tb.dut_a.check_admin_save()):
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result


def admin_save_detail(loops=1):

    loop = 1
    result = 'PASS'


    log_file.info("")
    log_file.info("Perform an admin save detail on %s %s times" %(tb.dut_a.sysname,loops))
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        if not (tb.dut_a.admin_save_detail()):
            result = 'FAIL'
        if not (tb.dut_a.check_admin_save()):
            result = 'FAIL'
        loop +=1
        log_file.info("")
    return result

def reboot_node(loops=1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Perform a reboot on node %s %s times" %(tb.dut_a.sysname,loops))

    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))

        tb.dut_a.sr_reboot() 
        tb.dut_a.close() 

        if tb.dut_b.local_port_1.wait_port_oper_down_ex(30): 
            log_file.info("DUT-B sees port to DUT-A go down")
        else: 
            log_file.error("DUT-B never saw port to DUT-A go down")
            result = 'FAIL'

        utils.countdown(5)

        if tb.dut_a.wait_node_up(300):
            log_file.info("DUT-A responds to ping OK")
            log_file.info("But node is not fully back up yet")
        else:
            log_file.error("Node did not come back up after reboot")

        log_file.info("Wait for DUT-B to see port to DUT-A come up")
        if tb.dut_b.local_port_1.wait_port_oper_up_ex(300):
            log_file.info("DUT-B sees port to DUT-A come back up")
        else:
            log_file.info("DUT-B did not see port to DUT-A come back up")
            result = 'FAIL'

        tb.dut_a.send_cli_command("show time")
        loop +=1
        log_file.info("")

    return result

def mgmt_ipv6_ping(loops=1):

    loop   = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Ping the IPv6 management address %s times" %(loops))

    if not (tb.dut_a.ping6(count=loops,size=2000,gap=0.2)): 
        result = 'FAIL'

    return result

def upgrade_node(bofsave=False,cloud_init='v2',new_onie=None,loops=1):

    loop   = 1
    result = 'PASS'

    f_node = tb.wbx
    c_node = tb.hub_1

    log_file.info("")
    log_file.info("Perform a node upgrade %s times" %(loops))
    log_file.info("")
    log_file.info("********************************")
    log_file.info("")
    log_file.info("With cloud-init.cfg version = %s" %(cloud_init))
    log_file.info("")
    log_file.info("********************************")

    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))

        if bofsave:
            log_file.info("OK to save bof")
            log_file.info("Execute a bof save")
            if not (f_node.bof_save()):
                log_file.error("bof save failed")
                result = 'FAIL'
            if not (f_node.check_bof_save()):
                result = 'FAIL'
                log_file.error("bof save failed")
        else:
            log_file.info("DON'T save bof")

        log_file.info("Execute an admin save")
        if not (f_node.admin_save()):
            log_file.error("admin save failed")
            result = 'FAIL'
        if not (f_node.check_admin_save()):
            log_file.error("admin save failed")
            result = 'FAIL'

        log_file.info("Upgrade WBX")
        log_file.info("Cloud init version = %s" %(cloud_init))
        log_file.info("")
        if not f_node.wbx_hv_upgrade(cloud_init,new_onie):
            result == 'FAIL'
        f_node.close()

        if c_node.to_wbx.wait_port_oper_down_ex(30): 
            log_file.info("Hub 1 sees port to WBX 89 go down")
        else: 
            log_file.error("Hub 1 never saw port to WBX 89 go down")
            result = 'FAIL'

        utils.countdown(5)

        if f_node.wait_node_up(300):
            log_file.info("WBX VM responds to ping OK")
            log_file.info("But node is not fully back up yet")
        else:
            log_file.error("Node did not come back up after reboot")
            result = 'FAIL'

        log_file.info("Wait for connected CRAN Hub to see WBX port come up")
        if c_node.to_wbx.wait_port_oper_up_ex(300):
            log_file.info("Hub 1 sees port to WBX 89 come back up")
        else:
            log_file.error("Hub 1 did not see port to WBX 89 come back up")
            result = 'FAIL'

        loop +=1
        log_file.info("")
        
        if result == 'FAIL':
            return result

    return result

def robo_user(cli,loops=1):

    loop = 1
    result = 'PASS'

    log_file.info("")
    log_file.info("Execute CLI command %s %s %s times" %(cli,tb.dut_a.sysname,loops))
    tb.dut_a.send_cli_command('exit all')
    tb.dut_a.send_cli_command('environment no more')
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        tb.dut_a.send_cli_command(cli)
        loop +=1
        log_file.info("")
    tb.dut_a.send_cli_command('exit all')
    return result

def multi_port_bounce(side,loops = 1):

    loop = 1
    result = 'PASS'
    f_node = tb.wbx_spine_2
    f_ports = [f_node.local_port_3,f_node.local_port_5,f_node.local_port_7,f_node.local_port_9,f_node.local_port_11,f_node.local_port_13,f_node.local_port_15,f_node.local_port_17, \
               f_node.local_port_19,f_node.local_port_21,f_node.local_port_23,f_node.local_port_25,f_node.local_port_27,f_node.local_port_29,f_node.local_port_31,f_node.local_port_33, \
               f_node.local_port_35,f_node.local_port_37,f_node.local_port_39,f_node.local_port_41,f_node.local_port_43,f_node.local_port_45,f_node.local_port_47]

    c_node  = tb.wbx_spine_2

    c_ports = [c_node.local_port_4,c_node.local_port_6,c_node.local_port_8,c_node.local_port_10,c_node.local_port_12,c_node.local_port_14,c_node.local_port_16,c_node.local_port_18, \
               c_node.local_port_20,c_node.local_port_22,c_node.local_port_24,c_node.local_port_26,c_node.local_port_28,c_node.local_port_30,c_node.local_port_32,c_node.local_port_34, \
               c_node.local_port_36,c_node.local_port_48,c_node.local_port_40,c_node.local_port_42,c_node.local_port_44,c_node.local_port_46,f_node.local_port_48]

    c_lags  = [c_node.local_lag_4,c_node.local_lag_6,c_node.local_lag_8,c_node.local_lag_10,c_node.local_lag_12,c_node.local_lag_14,c_node.local_lag_16, \
               c_node.local_lag_18,c_node.local_lag_20,c_node.local_lag_22,c_node.local_lag_24,c_node.local_lag_26,c_node.local_lag_28,c_node.local_lag_30, \
               c_node.local_lag_32,c_node.local_lag_34,c_node.local_lag_36,c_node.local_lag_38,c_node.local_lag_40,c_node.local_lag_42,c_node.local_lag_44, \
               c_node.local_lag_46, c_node.local_lag_48]

    log_file.info("")
    log_file.info("Bounce port is %s to WBX" %(side))
    log_file.info("")
    log_file.info("Bounce node %s ports below %s times" %(f_node.sysname, loops))
    for f_port in f_ports:
        log_file.info("Port %s " %(f_port.name))
    log_file.info("")
    log_file.info("Check the ports and associated lags go down and come back up")
    while not loop > loops:
        log_file.info("Loop %s of %s" %(loop,loops))
        for f_port in f_ports:
            f_port.shutdown(snmp=True)
        for c_port in c_ports:
            if not (c_port.wait_port_oper_down_ex(120)):
                log_file.error("Node %s port %s did NOT go oper down during bounce number %s" %(c_node.sysname, c_port.name,loop))
                result = 'FAIL'
        for c_lag in c_lags:
            if not (c_lag.wait_port_oper_down_ex(120)):
                log_file.error("Node %s port %s did NOT go oper down during bounce number %s" %(c_node.sysname, c_lag.name,loop))
                result = 'FAIL'
        for f_port in f_ports:
            f_port.no_shutdown(snmp=True)
        for c_port in c_ports:
            if not (c_port.wait_port_oper_up_ex(120)):
                log_file.error("Node %s port %s did NOT come oper up during bounce number %s" %(c_node.sysname, c_port.name,loop))
                result = 'FAIL'
        for c_lag in c_lags:
            if not (c_lag.wait_port_oper_up_ex(120)):
                log_file.error("Node %s port %s did NOT come oper up during bounce number %s" %(c_node.sysname, c_lag.name,loop))
                result = 'FAIL'
        loop +=1
    return result

def check_all_lags_up():

    result  = True 

    c_node  = tb.wbx_spine_2

    c_lags  = [c_node.local_lag_4,c_node.local_lag_5,c_node.local_lag_6,c_node.local_lag_7,c_node.local_lag_8,c_node.local_lag_9,c_node.local_lag_10, \
               c_node.local_lag_11,c_node.local_lag_12,c_node.local_lag_13,c_node.local_lag_14,c_node.local_lag_15,c_node.local_lag_16,c_node.local_lag_17, \
               c_node.local_lag_18,c_node.local_lag_19,c_node.local_lag_20,c_node.local_lag_21,c_node.local_lag_22,c_node.local_lag_23,c_node.local_lag_24, \
               c_node.local_lag_25,c_node.local_lag_26,c_node.local_lag_27,c_node.local_lag_28,c_node.local_lag_29,c_node.local_lag_30,c_node.local_lag_31, \
               c_node.local_lag_32,c_node.local_lag_33,c_node.local_lag_34,c_node.local_lag_35,c_node.local_lag_36,c_node.local_lag_37,c_node.local_lag_38, \
               c_node.local_lag_39,c_node.local_lag_40,c_node.local_lag_41,c_node.local_lag_42,c_node.local_lag_43,c_node.local_lag_44,c_node.local_lag_45, \
               c_node.local_lag_46,c_node.local_lag_47,c_node.local_lag_48]

    log_file.info("")
    log_file.info("Check all expected lags are up")
    log_file.info("")
    for c_lag in c_lags:
        if not (c_lag.wait_port_oper_up_ex(120)):
            log_file.error("Node %s port %s did NOT come oper up " %(c_node.sysname, c_lag.name))
            result = False 

    return result

def main(testcase_name='',testsuite_name='vzw_5g_wbx_bash',csv='false',testbed_file='vzw_5g_100g.yaml'):

    hub_site_stat       = {}
    hub_site_stat_final = {}
    port_result         = 'PASS'
    test_result         = 'PASS'
    test_path           = '/automation/python/tests/'
    testbed_file        = test_path+testbed_file
    port_wait           = 120
    upgrade_loops       = 1
    reboot_loops        = 1
    save_loops          = 10
    add_loops           = 10
    bounce_loops        = 10

    log_file.info("")
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("")
    log_file.info("Suite    : %s" %(testsuite_name))
    log_file.info("Testcase : %s" %(testcase_name))
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("")
    log_file.info("")

    start_time = datetime.now()

    # Initialize the testbed
    testbed_init(testbed_file)

    log_file.info('Clear log-99 on DUT-A')
    tb.dut_a.clear_log_99()

    log_file.info('Show initial DUT-A bof')
    tb.dut_a.show_bof()

    #log_file.info('Poll IXR-S memory usage before test')
    #tb.dut_a = tb.dut_a.get_mem_current_total()
    #tb.dut_a = tb.dut_a.get_mem_total_in_use()
    #tb.dut_a = tb.dut_a.get_mem_available()

    dut_ver_b = tb.dut_a.get_active_cpm_sw_version()

    if testcase_name   == 'remote_port_bounce':
        test_result = port_bounce('remote',loops=bounce_loops)
    elif testcase_name == 'remote_lag_bounce':
        test_result = lag_bounce('remote',loops=bounce_loops)
    elif testcase_name == 'local_port_bounce':
        test_result = port_bounce('local',loops=bounce_loops)
    elif testcase_name == 'local_lag_bounce':
        test_result = lag_bounce('local',loops=bounce_loops)
    elif testcase_name == 'local_vpls_bounce':
        test_result = vpls_bounce(loops=bounce_loops)
    elif testcase_name == 'local_vpls_add_delete':
        test_result = vpls_add_delete(loops=add_loops)
    elif testcase_name == 'local_vpls_add_delete_many':
        test_result = vpls_add_delete_many(loops=add_loops)
    elif testcase_name == 'local_vpls_sap_bounce':
        test_result = vpls_sap_bounce(loops=bounce_loops)
    elif testcase_name == 'local_vpls_sap_add_delete':
        test_result = vpls_sap_add_delete(loops=add_loops)
    elif testcase_name == 'local_admin_save':
        test_result = admin_save(loops=save_loops)
    elif testcase_name == 'local_admin_save_detail':
        test_result = admin_save_detail(loops=save_loops)
    elif testcase_name == 'local_bof_save':
        test_result = bof_save(loops=save_loops)
    elif testcase_name == 'reboot_node':
        test_result = reboot_node(loops=reboot_loops)
    elif testcase_name == 'mgmt_ipv6_ping':
        test_result = mgmt_ipv6_ping(loops=100)
    elif testcase_name == 'robo_user_show_port_detail':
        test_result = robo_user('show port 1/1/c53/1 detail',loops=bounce_loops)
    elif testcase_name == 'robo_user_show_service_all':
        test_result = robo_user('show service id 1 all',loops=bounce_loops)
    elif testcase_name == 'robo_user_show_sap_detail':
        test_result = robo_user('show service id 1 sap 1/1/c53/1:1 detail',loops=bounce_loops)
    elif testcase_name == 'local_multi_port_bounce':
        test_result = multi_port_bounce('local',loops=bounce_loops)
    else:
        log_file.error("Testcase %s does not exist" %(testcase_name))

    log_file.info('Show log-99 on IXR-S')
    tb.dut_a.show_log_99()

    log_file.info('Show final WBX bof')
    tb.dut_a.show_bof()

    #log_file.info('Poll IXR memory usage after test')
    #dut_a = tb.dut_a.get_mem_current_total()
    #dut_a = tb.dut_a.get_mem_total_in_use()
    #dut_a = tb.dut_a.get_mem_available()

    dut_ver_a = tb.dut_a.get_active_cpm_sw_version()

    log_file.info("")
    #log_file.info('Display IXR-S memory usage before and after test:')
    #log_file.info("")
    #log_file.info('Total before test ...... %s after test .... %s' %(dut_a,dut_a))
    #log_file.info('In use before test ..... %s after test .... %s' %(dut_a,dut_a))
    #log_file.info('Available before test .. %s after test .... %s' %(dut_a,dut_a))

    log_file.info("")
    log_file.info('Check IXR-S again for hw errors:')
    tb.dut_a.check_for_hw_errors()

    log_file.info("")
    log_file.info('Confirm the IXR-S IPv6 MGT address can still be pinged')
    if not (tb.dut_a.ping6(count=3,size=2000,gap=0.2)): 
        test_result = 'FAIL'
        log_file.error('IXR-S IPv6 MGT address can NOT be pinged')
    else:
        log_file.info('IXR-S IPv6 MGT address can  be pinged')

    log_file.info("")
    #log_file.info('Check all lags are still up')
    #if not check_all_lags_up(): 
    #    test_result = 'FAIL'
    #    log_file.error('All expected IXR-S lags are not up')
    #else:
    #    log_file.info('All expected IXR-S lags are up')

    log_file.info("")
    log_file.info('IXR-S version before and after test:')
    log_file.info("")
    log_file.info('Before ...... %s' %(dut_ver_b))
    log_file.info('After  ...... %s' %(dut_ver_a))

    end_time     = datetime.now()
    test_dur     = end_time - start_time
    test_dur_sec = test_dur.total_seconds()

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("Test Name %s " %(testcase_name))
    log_file.info("Duration: %s seconds" %(str(test_dur_sec)))

    if test_result == 'PASS':
        log_file.info("Result = %s " %(test_result))
    else:
        log_file.error("Result = %s " %(test_result))

    log_file.info("--------------------------------------------------")
    log_file.info("")

    test_result_list = [] 
    test_result_list.append(test_result)
    test_result_dict = {} 
    test_result_list.append(test_result_dict)

    tb.dut_a.close()
    tb.dut_b.close()
    return test_result_list

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

