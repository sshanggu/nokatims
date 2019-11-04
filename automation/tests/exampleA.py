#!/usr/bin/env python3
##############################################################################
#
# ExampleA test suite
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
#   All testcases in exampleA are implemented in main function
#   with 'if' branches. This is kind of legacy style.
#
#   Please refer to exampleB.py that implements each testcases in
#   separated function.
#
# 2019/10/29 -- sshanggu rewrote
#
##############################################################################

import os
import sys
import time
import utils
import node as nodelib
from utils import framelog

mylog = utils.get_logger(__name__)
tb = None


def main(testsuite_name='exampleA',
         testcase_name='snmp_and_ssh_classic',
         testbed_file='example.yaml'):

    global tb
    if not tb:
        tb = nodelib.Testbed(testbed_file)

    # initialize testcheck True
    testcheck = True

    # tc: snmp_and_ssh_classic
    if testcase_name == 'snmp_and_ssh_classic':
        step = 1
        for protocol in ['snmp', 'ssh']:
            framelog('STEP %d: Port shut/noshut via %s'
                     % (step, protocol), '*')
            step += 1
            for node in tb:
                framelog('Node %s port shut/noshut' % node.sysname)
                for port in node:
                    port.shutdown(opt=protocol)
                    testcheck and port.check_admin_state(state='down')
                    port.noshutdown(opt=protocol)
                    testcheck and port.check_admin_state(state='up')
    # tc: ssh_modeldriven
    elif testcase_name == 'ssh_modeldriven':
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
    # tc: netconf_cli
    elif testcase_name == 'netconf_cli':
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
    # tc: netconf_cli
    elif testcase_name == 'netconf_xml':
        framelog('STEP 1: Port shut/noshut via netconf-xml', '*')
        for node in tb:
            framelog('Node %s port shut/noshut' % node.sysname)
            for port in node:
                port.shutdown(opt='netconf')
                testcheck and port.check_admin_state(state='down')
                port.noshutdown(opt='netconf')
                testcheck and port.check_admin_state()
    else:
        mylog.error('Wrong testcase_name %s' % testcase_name)
        return ['FAIL']

    if testcheck:
        return ['PASS']
    return ['FAIL']
