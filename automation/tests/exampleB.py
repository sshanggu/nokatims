#!/usr/bin/env python3
##############################################################################
#
# exampleB test suite
#   It runs on testbed, example.yaml, which has one SR node.
#   Tests send commands through ssh and netconf session.
#   For ssh session, both classic and model-driven modes are covered
#   For netconf session, both cli and xml styles are covered.
#
#   It includus testcase as below:
#       snmp_and_ssh_classic
#       ssh_modeldriven
#       netconf_cli
#       netconf_xml
#
#   Each testcase is implemented as separated function.
#   One testcase changes will not affect others.
#   The main function is simple and needs not change at all.
#
# 2019/10/25 -- sshanggu rewrote
#
##############################################################################
import os
import sys
import json
import utils
import node as nodelib
from utils import framelog

###############################################################################
# suite common setup and utils
###############################################################################
mylog = utils.get_logger(__name__)


###############################################################################
# test case functions
###############################################################################

# snmp_and_ssh_classic
#   verify simple show/config command through snmp and ssh session
def snmp_and_ssh_classic():
    testcheck = True

    step = 1
    for protocol in ['snmp', 'ssh']:
        framelog('STEP %d: Port shut/noshut via %s' % (step, protocol), '*')
        step += 1
        for node in tb:
            framelog('Node %s port shut/noshut' % node.sysname)
            for port in node:
                port.shutdown(opt=protocol)
                testcheck and port.check_admin_state(state='down')
                port.noshutdown(opt=protocol)
                testcheck and port.check_admin_state(state='up')

    # return result list
    # 1st element must present. -- PASS|FAIL
    # 2nd element is optional. -- KPI dictionary for regression kpi diagram
    if testcheck:
        return ['PASS']
    return ['FAIL']


# ssh_modeldriven
# verify show/config command through ssh session with model-driven mode
def ssh_modeldriven():
    testcheck = True

    framelog('STEP 1: Port shut/noshut via ssh/model-driven', '*')
    for node in tb:
        framelog('Node %s port shut/noshut' % node.sysname)
        for port in node:
            cmd = 'config port %s admin-state disable' % port.port
            port.node.send_command(cmd, style='md')
            testcheck and port.check_admin_state(state='down', style='md')
            cmd = 'config port %s admin-state enable' % port.port
            port.node.send_command(cmd, style='md')
            testcheck and port.check_admin_state(style='md')

    if testcheck:
        return ['PASS']
    return ['FAIL']


# netconf_cli
# verify show/config command through netconf session with cli mode
def netconf_cli():
    testcheck = True

    framelog('STEP 1: Port shut/noshut via netconf-cli', '*')
    for node in tb:
        framelog('Node %s port shut/noshut' % node.sysname)
        for port in node:
            cmd = 'config port %s shutdown' % port.port
            port.node.send_command(cmd, protocol='netconf')
            testcheck and port.check_admin_state(state='down')
            cmd = 'config port %s no shutdown' % port.port
            port.node.send_command(cmd, protocol='netconf')
            testcheck and port.check_admin_state()

    if testcheck:
        return ['PASS']
    return ['FAIL']


# netconf_xml
# verify show/config command through netconf session with xml mode
def netconf_xml():
    testcheck = True

    framelog('STEP 1: Port shut/noshut via netconf-xml', '*')
    for node in tb:
        framelog('Node %s port shut/noshut' % node.sysname)
        for port in node:
            port.shutdown(opt='netconf')
            testcheck and port.check_admin_state(state='down')
            port.noshutdown(opt='netconf')
            testcheck and port.check_admin_state()

    if testcheck:
        return ['PASS']
    return ['FAIL']


###############################################################################
# main function
###############################################################################
tb = None  # global tb initialized to None


def main(testsuite_name='exampleB',
         testcase_name='snmp_and_ssh_classic',
         testbed_file='example.yaml'):

    global tb
    # tb is instantiated only once
    if not tb:
        tb = nodelib.Testbed(testbed_file)

    # run test based on passed-in testcase_name
    return globals()[testcase_name]()
