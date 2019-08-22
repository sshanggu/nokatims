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

tb  = attrdict.AttrDict()
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

def config_v4_underlay(status):

    tb.bl_1.send_cli_command('/configure router interface to-SP1 %s' %(status))
    tb.bl_1.send_cli_command('/configure router interface to-SP2 %s' %(status))

    tb.bl_2.send_cli_command('/configure router interface to-SP1 %s' %(status))
    tb.bl_2.send_cli_command('/configure router interface to-SP2 %s' %(status))

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

        tb.bl_1.send_cli_command('/configure router isis level-capability level-1/2')
        tb.bl_1.send_cli_command('/configure router isis area-id 49.0001')

        tb.bl_2.send_cli_command('/configure router isis level-capability level-1/2')
        tb.bl_2.send_cli_command('/configure router isis area-id 49.0001')

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

        tb.bl_1.send_cli_command('/configure router isis level-capability level-2')
        tb.bl_1.send_cli_command('/configure router isis area-id 49.0001')

        tb.bl_2.send_cli_command('/configure router isis level-capability level-2')
        tb.bl_2.send_cli_command('/configure router isis area-id 49.0001')

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
        tb.hub_1.ran_vprn.no_shutdown()
        tb.hub_2.ran_vprn.no_shutdown()
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
    log_file.info("Exit Leaf 1 chassis type ................ %s" %(tb.bl_1.get_chassis_type()))
    log_file.info("Exit Leaf 1 Active CPM software version . %s" %(tb.bl_1.get_active_cpm_sw_version()))
    log_file.info("Exit Leaf 2 chassis type ................ %s" %(tb.bl_2.get_chassis_type()))
    log_file.info("Exit Leaf 2 Active CPM software version . %s" %(tb.bl_2.get_active_cpm_sw_version()))
    log_file.info("--------------------------------------------------")

def show_north_traffic_util():

    bl1crstx  = round(tb.bl_1.to_ense_vxlan.get_util_perc('tx'),1)
    bl2crstx  = round(tb.bl_2.to_ense_vxlan.get_util_perc('tx'),1)

    s2bl1tx  = round(tb.spine_2.to_bl_1.get_util_perc('tx'),1)
    s2bl2tx  = round(tb.spine_2.to_bl_2.get_util_perc('tx'),1)

    s1bl1tx  = round(tb.spine_1.to_bl_1.get_util_perc('tx'),1)
    s1bl2tx  = round(tb.spine_1.to_bl_2.get_util_perc('tx'),1)

    al1s1tx  = round(tb.al_1.to_spine_1.get_util_perc('tx'),1)
    al1s2tx  = round(tb.al_1.to_spine_2.get_util_perc('tx'),1)

    al2s1tx  = round(tb.al_2.to_spine_1.get_util_perc('tx'),1)
    al2s2tx  = round(tb.al_2.to_spine_2.get_util_perc('tx'),1)

    #al3s1tx  = round(tb.al_3.to_spine_1.get_util_perc('tx'),1)
    #al3s2tx  = round(tb.al_3.to_spine_2.get_util_perc('tx'),1)


    al3s11tx  = round(tb.al_3.to_spine_1_1.get_util_perc('tx'),1)
    al3s12tx  = round(tb.al_3.to_spine_1_2.get_util_perc('tx'),1)
    al3s21tx  = round(tb.al_3.to_spine_2_1.get_util_perc('tx'),1)
    al3s22tx  = round(tb.al_3.to_spine_2_2.get_util_perc('tx'),1)

    al4s11tx  = round(tb.al_4.to_spine_1_1.get_util_perc('tx'),1)
    al4s12tx  = round(tb.al_4.to_spine_1_2.get_util_perc('tx'),1)
    al4s21tx  = round(tb.al_4.to_spine_2_1.get_util_perc('tx'),1)
    al4s22tx  = round(tb.al_4.to_spine_2_2.get_util_perc('tx'),1)

    h2al2tx = round(tb.hub_2.to_al_2.get_util_perc('tx'),1)
    h1al1tx = round(tb.hub_1.to_al_1.get_util_perc('tx'),1)

    h1ca1rx  = round(tb.hub_1.to_ca_1.get_util_perc('rx'),1)
    h2ca1rx  = round(tb.hub_2.to_ca_1.get_util_perc('rx'),1)
    al3vc1rx  = round(tb.al_3.to_vc_1_1.get_util_perc('rx'),1)
    al4vc1rx  = round(tb.al_4.to_vc_1_1.get_util_perc('rx'),1)

    log_fmt_a = ' ||{:>27}{:>5}'
    log_fmt_b = ' ||{:>22}    \  /{:>7}'
    log_fmt_c = ' ||                    |{:>6}{:>5}   |'
    log_fmt_d = ' ||{:>7}{:>15}{:>14}{:>15}'
    log_fmt_x = ' ||{:>7}{:>5}{:>10}{:>5}{:>5}{:>5}{:>7}{:>4}{:>4}{:>4}'
    #log_fmt_e = ' ||  |   Tx+{:>4}----+     |'
    #log_fmt_f = ' ||  |   Rx+{:>4}----+     |'
    #log_fmt_g = ' ||  |     +----{:<4}+Tx   |'
    #log_fmt_h = ' ||  |     +----{:<4}+Rx   |'
    log_fmt_e = ' ||{:>12}{:>5}'


    log_file.info(" Northbound traffic flow" )
    log_file.info(" Percent link utilization" )
    log_file.info("")
    log_file.info("------------------------" )
    log_file.info("" )
    log_file.info(" /\\                                       " )
    log_file.info(" ||                            |           " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                        |  SAP  |       " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                          /  \          " )
    log_file.info(log_fmt_a.format(bl1crstx,bl2crstx))
    log_file.info(" ||                        /      \        " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||                 | BL1 |        | BL2 | " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||                    |   \      /   |    " )
    log_file.info(" ||                    |    \    /    |    " )
    log_file.info(log_fmt_b.format(s1bl1tx,s2bl2tx))
    log_file.info(" ||                    |      \/      |    " )
    log_file.info(" ||                    |      /\      |    " )
    log_file.info(" ||                    |     /  \     |    " )
    log_file.info(log_fmt_c.format(s1bl2tx,s2bl1tx))
    log_file.info(" ||                    |   /      \   |    " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||     +---------- | SP1 |--+  +--| SP2 | ----------+    " )
    log_file.info(" ||     |           +-----+   \/   +-----+           |    " )
    log_file.info(" ||     |              |   \  /\  /   |              |    " )
    log_file.info(" ||     |              |    \/  \/    |              |    " )
    log_file.info(" ||     |              |    /\  /\    |              |    " )
    log_file.info(" ||     |              |   /  \/  \   |              |    " )
    log_file.info(" ||     |      +-------|--+   /\   +--|-------+      |    " )
    log_file.info(" ||     |     /        |     /  \     |        \     |    " )
    log_file.info(log_fmt_x.format(al1s1tx,al1s2tx,al2s1tx,al2s2tx,al3s11tx,al3s21tx,al4s11tx,al4s12tx,al4s21tx,al4s22tx))               
    log_file.info(" ||     |   /          |   /      \   |          \   |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  | AL1 |        | AL2 |        | AL3 |        | AL4 | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(log_fmt_d.format(h1al1tx,h2al2tx,al3vc1rx,al4vc1rx))
    log_file.info(" ||     |              |             |               |    " )
    log_file.info(" ||  +-----+        +-----+       +-----+         +-----+ " )
    log_file.info(" ||  |     |        |     |       |     |         |     | " )
    log_file.info(" ||  | CBL |        | CBL |       | VC1 |         | VC1 | " )
    log_file.info(" ||  |  1  |        |  2  |       | IM1 |         | IMM | " )
    log_file.info(" ||  |     |        |     |       |  1  |         |  2  | " )
    log_file.info(" ||  +-----+        +-----+       +-----+         +-----+ " )
    log_file.info(" ||         \      /               |||||           |||||  " )
    log_file.info(log_fmt_e.format(h1ca1rx,h2ca1rx))
    log_file.info(" ||           \  /          " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||         |  IXR  |       " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||             |           " )
    log_file.info("" )

def show_south_traffic_util():

    bl1crsrx  = round(tb.bl_1.to_ense_vxlan.get_util_perc('rx'),1)
    bl2crsrx  = round(tb.bl_2.to_ense_vxlan.get_util_perc('rx'),1)

    s2bl1rx  = round(tb.spine_2.to_bl_1.get_util_perc('rx'),1)
    s2bl2rx  = round(tb.spine_2.to_bl_2.get_util_perc('rx'),1)

    s1bl1rx  = round(tb.spine_1.to_bl_1.get_util_perc('rx'),1)
    s1bl2rx  = round(tb.spine_1.to_bl_2.get_util_perc('rx'),1)

    al1s1rx  = round(tb.al_1.to_spine_1.get_util_perc('rx'),1)
    al1s2rx  = round(tb.al_1.to_spine_2.get_util_perc('rx'),1)

    al2s1rx  = round(tb.al_2.to_spine_1.get_util_perc('rx'),1)
    al2s2rx  = round(tb.al_2.to_spine_2.get_util_perc('rx'),1)

    #al3s1tx  = round(tb.al_3.to_spine_1.get_util_perc('tx'),1)
    #al3s2tx  = round(tb.al_3.to_spine_2.get_util_perc('tx'),1)

    al3s11rx  = round(tb.al_3.to_spine_1_1.get_util_perc('rx'),1)
    al3s12rx  = round(tb.al_3.to_spine_1_2.get_util_perc('rx'),1)
    al3s21rx  = round(tb.al_3.to_spine_2_1.get_util_perc('rx'),1)
    al3s22rx  = round(tb.al_3.to_spine_2_2.get_util_perc('rx'),1)

    al4s11rx  = round(tb.al_4.to_spine_1_1.get_util_perc('rx'),1)
    al4s12rx  = round(tb.al_4.to_spine_1_2.get_util_perc('rx'),1)
    al4s21rx  = round(tb.al_4.to_spine_2_1.get_util_perc('rx'),1)
    al4s22rx  = round(tb.al_4.to_spine_2_2.get_util_perc('rx'),1)

    h2al2rx = round(tb.hub_2.to_al_2.get_util_perc('rx'),1)
    h1al1rx = round(tb.hub_1.to_al_1.get_util_perc('rx'),1)

    h1ca1tx  = round(tb.hub_1.to_ca_1.get_util_perc('tx'),1)
    h2ca1tx  = round(tb.hub_2.to_ca_1.get_util_perc('tx'),1)

    al3vc1tx  = round(tb.al_3.to_vc_1_1.get_util_perc('tx'),1)
    al4vc1tx  = round(tb.al_4.to_vc_1_1.get_util_perc('tx'),1)

    log_fmt_a = ' ||{:>27}{:>5}'
    log_fmt_b = ' ||{:>22}    \  /{:>7}'
    log_fmt_c = ' ||                    |{:>6}{:>5}   |'
    log_fmt_d = ' ||{:>7}{:>15}{:>14}{:>15}'
    #log_fmt_x = ' ||{:>7}{:>5}{:>10}{:>5}{:>5}{:>5}{:>10}{:>5}'
    log_fmt_x = ' ||{:>7}{:>5}{:>10}{:>5}{:>5}{:>5}{:>7}{:>4}{:>5}{:>5}'
    #log_fmt_e = ' ||  |   Tx+{:>4}----+     |'
    #log_fmt_f = ' ||  |   Rx+{:>4}----+     |'
    #log_fmt_g = ' ||  |     +----{:<4}+Tx   |'
    #log_fmt_h = ' ||  |     +----{:<4}+Rx   |'
    log_fmt_e = ' ||{:>12}{:>5}'


    log_file.info(" Southbound traffic flow" )
    log_file.info(" Percent link utilization" )
    log_file.info("")
    log_file.info("------------------------" )
    log_file.info("" )
    log_file.info(" ||                            |           " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                        |  SAP  |       " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                          /  \          " )
    log_file.info(log_fmt_a.format(bl1crsrx,bl2crsrx))
    log_file.info(" ||                        /      \        " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||                 | BL1 |        | BL2 | " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||                    |   \      /   |    " )
    log_file.info(" ||                    |    \    /    |    " )
    log_file.info(log_fmt_b.format(s1bl1rx,s2bl2rx))
    log_file.info(" ||                    |      \/      |    " )
    log_file.info(" ||                    |      /\      |    " )
    log_file.info(" ||                    |     /  \     |    " )
    log_file.info(log_fmt_c.format(s1bl2rx,s2bl1rx))
    log_file.info(" ||                    |   /      \   |    " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||     +---------- | SP1 |--+  +--| SP2 | ----------+    " )
    log_file.info(" ||     |           +-----+   \/   +-----+           |    " )
    log_file.info(" ||     |              |   \  /\  /   |              |    " )
    log_file.info(" ||     |              |    \/  \/    |              |    " )
    log_file.info(" ||     |              |    /\  /\    |              |    " )
    log_file.info(" ||     |              |   /  \/  \   |              |    " )
    log_file.info(" ||     |      +-------|--+   /\   +--|-------+      |    " )
    log_file.info(" ||     |     /        |     /  \     |        \     |    " )
    log_file.info(log_fmt_x.format(al1s1rx,al1s2rx,al2s1rx,al2s2rx,al3s11rx,al3s21rx,al4s11rx,al4s12rx,al4s21rx,al4s22rx))               
    log_file.info(" ||     |   /          |   /      \   |          \   |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  | AL1 |        | AL2 |        | AL3 |        | AL4 | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||     |              |              |              |    " )
    log_file.info(" ||     |              |              |              |    " )
    log_file.info(" ||     |              |              |              |    " )
    log_file.info(log_fmt_d.format(h1al1rx,h2al2rx,al3vc1tx,al4vc1tx))
    log_file.info(" ||     |              |              |              |    " )
    log_file.info(" ||     |              |              |              |    " )
    log_file.info(" ||     |              |              |              |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  |     |        |     |        |     |        |     | " )
    log_file.info(" ||  | CBL |        | CBL |        | VC1 |        | VC1 | " )
    log_file.info(" ||  |  1  |        |  2  |        | IM1 |        | IMM | " )
    log_file.info(" ||  |     |        |     |        |  1  |        |  2  | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||         \      /                |||||          |||||  " )
    log_file.info(log_fmt_e.format(h1ca1tx,h2ca1tx))
    log_file.info(" ||           \  /          " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||         |  IXR  |       " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||             |           " )
    log_file.info(" \/             |           " )
    log_file.info("" )

def show_north_traffic_util_vx():

    bl1crstx  = round(tb.bl_1.to_ense_vxlan.get_util_perc('tx'),1)
    bl2crstx  = round(tb.bl_2.to_ense_vxlan.get_util_perc('tx'),1)

    s2bl1tx  = round(tb.spine_2.to_bl_1.get_util_perc('tx'),1)
    s2bl2tx  = round(tb.spine_2.to_bl_2.get_util_perc('tx'),1)

    s1bl1tx  = round(tb.spine_1.to_bl_1.get_util_perc('tx'),1)
    s1bl2tx  = round(tb.spine_1.to_bl_2.get_util_perc('tx'),1)

    vs1bl1tx  = round(tb.vxlan_spine_1.to_bl_1.get_util_perc('tx'),1)
    vs1bl2tx  = round(tb.vxlan_spine_1.to_bl_2.get_util_perc('tx'),1)

    vs2bl1tx  = round(tb.vxlan_spine_2.to_bl_1.get_util_perc('tx'),1)
    vs2bl2tx  = round(tb.vxlan_spine_2.to_bl_2.get_util_perc('tx'),1)

    al1s1tx  = round(tb.al_1.to_spine_1.get_util_perc('tx'),1)
    al1s2tx  = round(tb.al_1.to_spine_2.get_util_perc('tx'),1)

    al2s1tx  = round(tb.al_2.to_spine_1.get_util_perc('tx'),1)
    al2s2tx  = round(tb.al_2.to_spine_2.get_util_perc('tx'),1)

    val1s1tx  = round(tb.vxlan_al_1.to_vxlan_spine_1.get_util_perc('tx'),1)
    val1s2tx  = round(tb.vxlan_al_1.to_vxlan_spine_2.get_util_perc('tx'),1)

    #val2s1tx  = round(tb.vxlan_al_2.to_spine_1.get_util_perc('tx'),1)
    #val2s2tx  = round(tb.vxlan_al_2.to_spine_2.get_util_perc('tx'),1)
    val2s1tx = 0.0
    val2s2tx = 0.0

    h2al2tx = round(tb.hub_2.to_al_2.get_util_perc('tx'),1)
    h1al1tx = round(tb.hub_1.to_al_1.get_util_perc('tx'),1)

    val1ixrx = round(tb.vxlan_al_1.to_ixia.get_util_perc('tx'),1)
    #val2ixrx = round(tb.vxlan_al_2.to_ixia.get_util_perc('tx'),1)
    val2ixrx = 0.0
    h1ca1rx  = round(tb.hub_1.to_ca_1.get_util_perc('rx'),1)
    h2ca1rx  = round(tb.hub_2.to_ca_1.get_util_perc('rx'),1)
    al3vc1rx  = round(tb.al_3.to_vc_1_1.get_util_perc('rx'),1)
    al4vc1rx  = round(tb.al_4.to_vc_1_1.get_util_perc('rx'),1)

    log_fmt_a = ' ||{:>27}{:>5}'
    log_fmt_b = ' ||{:>22}    \  /{:>7}'
    log_fmt_c = ' ||                    |{:>6}{:>5}   |'
    log_fmt_d = ' ||{:>7}{:>14}{:>16}{:>15}'
    #log_fmt_x = ' ||{:>7}{:>5}{:>10}{:>5}{:>5}{:>5}{:>7}{:>4}{:>4}{:>4}'
    log_fmt_x = ' ||{:>7}{:>5}{:>10}{:>5}{:>5}{:>5}{:>10}{:>5}'
    log_fmt_y = ' ||{:>7}{:>5}{:>5}{:>5}{:>15}{:>5}{:>5}{:>5}'
    #log_fmt_e = ' ||  |   Tx+{:>4}----+     |'
    #log_fmt_f = ' ||  |   Rx+{:>4}----+     |'
    #log_fmt_g = ' ||  |     +----{:<4}+Tx   |'
    #log_fmt_h = ' ||  |     +----{:<4}+Rx   |'
    log_fmt_e = ' ||{:>12}{:>5}'

    #log_file.info(log_fmt_x.format(al1s1tx,al1s2tx,al2s1tx,al2s2tx,al3s11tx,al3s21tx,al4s11tx,al4s12tx,al4s21tx,al4s22tx))               

    log_file.info(" Northbound traffic flow" )
    log_file.info(" Percent link utilization" )
    log_file.info("")
    log_file.info("------------------------" )
    log_file.info("" )
    log_file.info(" /\\                                       " )
    log_file.info(" ||                            |           " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                        |  P E  |       " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                          /  \          " )
    log_file.info(log_fmt_a.format(bl1crstx,bl2crstx))
    log_file.info(" ||                        /      \        " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||     +---------- | BL1 |--+  +--| BL2 | ----------+    " )
    log_file.info(" ||     |           +-----+   \/   +-----+           |    " )
    log_file.info(" ||     |              |   \  /\  /   |              |    " )
    log_file.info(" ||     |              |    \/  \/    |              |    " )
    log_file.info(" ||     |              |    /\  /\    |              |    " )
    log_file.info(" ||     |              |   /  \/  \   |              |    " )
    log_file.info(" ||     |      +-------|--+   /\   +--|-------+      |    " )
    log_file.info(" ||     |     /        |     /  \     |        \     |    " )
    log_file.info(log_fmt_x.format(s1bl1tx,s1bl2tx,s2bl1tx,s2bl2tx,vs1bl1tx,vs1bl2tx,vs2bl1tx,vs2bl2tx))               
    log_file.info(" ||     |   /          |   /      \   |          \   |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  | S R |        | S R |        | V X |        | V X | " )
    log_file.info(" ||  | SP1 |        | SP2 |        | SP3 |        | SP4 | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||     |   \      /   |              |   \      /   |    " )
    log_file.info(" ||     |    \    /    |              |    \    /    |    " )
    log_file.info(" ||     |     \  /     |              |     \  /     |    " )
    log_file.info(" ||     |      \/      |              |      \/      |    " )
    log_file.info(" ||     |      /\      |              |      /\      |    " )
    log_file.info(" ||     |     /  \     |              |     /  \     |    " )
    log_file.info(log_fmt_y.format(al1s1tx,al1s2tx,al2s1tx,al2s2tx,val1s1tx,val1s2tx,val2s1tx,val2s2tx))               
    log_file.info(" ||     |   /      \   |              |   /      \   |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  | S R |        | S R |        | V X |        | V X | " )
    log_file.info(" ||  | AL1 |        | AL2 |        | AL1 |        | AL2 | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(log_fmt_d.format(h1al1tx,h2al2tx,val1ixrx,val2ixrx))
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||  +-----+       +-----+         +-----+        +-----+ " )
    log_file.info(" ||  |     |       |     |         |  I  |        |  I  | " )
    log_file.info(" ||  | CBL |       | CBL |         |  X  |        |  X  | " )
    log_file.info(" ||  |  1  |       |  2  |         |  I  |        |  I  | " )
    log_file.info(" ||  |     |       |     |         |  A  |        |  A  | " )
    log_file.info(" ||  +-----+       +-----+         +-----+        +-----+ " )
    log_file.info(" ||         \      /                                      " )
    log_file.info(log_fmt_e.format(h1ca1rx,h2ca1rx))
    log_file.info(" ||           \  /          " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||         |  IXR  |       " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||             |           " )
    log_file.info("" )

def show_south_traffic_util_vx():

    bl1crsrx  = round(tb.bl_1.to_ense_vxlan.get_util_perc('rx'),1)
    bl2crsrx  = round(tb.bl_2.to_ense_vxlan.get_util_perc('rx'),1)


    s2bl1rx  = round(tb.spine_2.to_bl_1.get_util_perc('rx'),1)
    s2bl2rx  = round(tb.spine_2.to_bl_2.get_util_perc('rx'),1)

    s1bl1rx  = round(tb.spine_1.to_bl_1.get_util_perc('rx'),1)
    s1bl2rx  = round(tb.spine_1.to_bl_2.get_util_perc('rx'),1)

    vs1bl1rx  = round(tb.vxlan_spine_1.to_bl_1.get_util_perc('rx'),1)
    vs1bl2rx  = round(tb.vxlan_spine_1.to_bl_2.get_util_perc('rx'),1)

    vs2bl1rx  = round(tb.vxlan_spine_2.to_bl_1.get_util_perc('rx'),1)
    vs2bl2rx  = round(tb.vxlan_spine_2.to_bl_2.get_util_perc('rx'),1)

    al1s1rx  = round(tb.al_1.to_spine_1.get_util_perc('rx'),1)
    al1s2rx  = round(tb.al_1.to_spine_2.get_util_perc('rx'),1)

    al2s1rx  = round(tb.al_2.to_spine_1.get_util_perc('rx'),1)
    al2s2rx  = round(tb.al_2.to_spine_2.get_util_perc('rx'),1)

    val1s1rx  = round(tb.vxlan_al_1.to_vxlan_spine_1.get_util_perc('rx'),1)
    val1s2rx  = round(tb.vxlan_al_1.to_vxlan_spine_2.get_util_perc('rx'),1)

    #val2s1rx  = round(tb.vxlan_al_2.to_spine_1.get_util_perc('rx'),1)
    #val2s2rx  = round(tb.vxlan_al_2.to_spine_2.get_util_perc('rx'),1)
    val2s1rx = 0.0
    val2s2rx = 0.0

    val1ixtx = round(tb.vxlan_al_1.to_ixia.get_util_perc('tx'),1)
    #val2ixtx = round(tb.vxlan_al_2.to_ixia.get_util_perc('tx'),1)
    val2ixtx = 0.0

    h2al2rx = round(tb.hub_2.to_al_2.get_util_perc('rx'),1)
    h1al1rx = round(tb.hub_1.to_al_1.get_util_perc('rx'),1)

    h1ca1tx  = round(tb.hub_1.to_ca_1.get_util_perc('tx'),1)
    h2ca1tx  = round(tb.hub_2.to_ca_1.get_util_perc('tx'),1)


    log_fmt_a = ' ||{:>27}{:>5}'
    log_fmt_b = ' ||{:>22}    \  /{:>7}'
    log_fmt_c = ' ||                    |{:>6}{:>5}   |'
    log_fmt_d = ' ||{:>7}{:>14}{:>16}{:>15}'
    log_fmt_e = ' ||{:>12}{:>5}'

    log_fmt_x = ' ||{:>7}{:>5}{:>10}{:>5}{:>5}{:>5}{:>10}{:>5}'
    log_fmt_y = ' ||{:>7}{:>5}{:>5}{:>5}{:>15}{:>5}{:>5}{:>5}'

    log_file.info(" Southbound traffic flow" )
    log_file.info(" Percent link utilization" )
    log_file.info("")
    log_file.info("------------------------" )
    log_file.info("" )
    log_file.info(" ||                            |           " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                        |  P E  |       " )
    log_file.info(" ||                        +-------+       " )
    log_file.info(" ||                          /  \          " )
    log_file.info(log_fmt_a.format(bl1crsrx,bl2crsrx))
    log_file.info(" ||                        /      \        " )
    log_file.info(" ||                 +-----+        +-----+ " )
    log_file.info(" ||     +---------- | BL1 |--+  +--| BL2 | ----------+    " )
    log_file.info(" ||     |           +-----+   \/   +-----+           |    " )
    log_file.info(" ||     |              |   \  /\  /   |              |    " )
    log_file.info(" ||     |              |    \/  \/    |              |    " )
    log_file.info(" ||     |              |    /\  /\    |              |    " )
    log_file.info(" ||     |              |   /  \/  \   |              |    " )
    log_file.info(" ||     |      +-------|--+   /\   +--|-------+      |    " )
    log_file.info(" ||     |     /        |     /  \     |        \     |    " )
    log_file.info(log_fmt_x.format(s1bl1rx,s1bl2rx,s2bl1rx,s2bl2rx,vs1bl1rx,vs1bl2rx,vs2bl1rx,vs2bl2rx))               
    log_file.info(" ||     |   /          |   /      \   |          \   |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  | S R |        | S R |        | V X |        | V X | " )
    log_file.info(" ||  | SP1 |        | SP2 |        | SP3 |        | SP4 | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||     |   \      /   |              |   \      /   |    " )
    log_file.info(" ||     |    \    /    |              |    \    /    |    " )
    log_file.info(" ||     |     \  /     |              |     \  /     |    " )
    log_file.info(" ||     |      \/      |              |      \/      |    " )
    log_file.info(" ||     |      /\      |              |      /\      |    " )
    log_file.info(" ||     |     /  \     |              |     /  \     |    " )
    log_file.info(log_fmt_y.format(al1s1rx,al1s2rx,al2s1rx,al2s2rx,val1s1rx,val1s2rx,val2s1rx,val2s2rx))               
    log_file.info(" ||     |   /      \   |              |   /      \   |    " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||  | S R |        | S R |        | V X |        | V X | " )
    log_file.info(" ||  | AL1 |        | AL2 |        | AL1 |        | AL2 | " )
    log_file.info(" ||  +-----+        +-----+        +-----+        +-----+ " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(log_fmt_d.format(h1al1rx,h2al2rx,val1ixtx,val2ixtx))
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||     |             |               |              |    " )
    log_file.info(" ||  +-----+       +-----+         +-----+        +-----+ " )
    log_file.info(" ||  |     |       |     |         |  I  |        |  I  | " )
    log_file.info(" ||  | CBL |       | CBL |         |  X  |        |  X  | " )
    log_file.info(" ||  |  1  |       |  2  |         |  I  |        |  I  | " )
    log_file.info(" ||  |     |       |     |         |  A  |        |  A  | " )
    log_file.info(" ||  +-----+       +-----+         +-----+        +-----+ " )
    log_file.info(" ||         \      /                                      " )
    log_file.info(log_fmt_e.format(h1ca1tx,h2ca1tx))
    log_file.info(" ||           \  /          " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||         |  IXR  |       " )
    log_file.info(" ||         +-------+       " )
    log_file.info(" ||             |           " )
    log_file.info(" \/             |           " )
    log_file.info("" )

def show_north_visp_fw_usage():


    # Northbound
    visp_1_inside_ingress  = tb.vxlan_al_1.visp_1.inside.get_ingress_packets()
    visp_1_outside_egress  = tb.vxlan_al_1.visp_1.outside.get_egress_packets()

    visp_2_inside_ingress  = tb.vxlan_al_1.visp_2.inside.get_ingress_packets()
    visp_2_outside_egress  = tb.vxlan_al_1.visp_2.outside.get_egress_packets()

    fw_1_inside_ingress    = tb.vxlan_al_1.fw_1.inside.get_ingress_packets()
    fw_1_outside_egress    = tb.vxlan_al_1.fw_1.outside.get_egress_packets()

    fw_2_inside_ingress    = tb.vxlan_al_1.fw_2.inside.get_ingress_packets()
    fw_2_outside_egress    = tb.vxlan_al_1.fw_2.outside.get_egress_packets()

    # Southbound
    fw_1_outside_ingress   = tb.vxlan_al_1.fw_1.outside.get_ingress_packets()
    fw_1_inside_egress     = tb.vxlan_al_1.fw_1.inside.get_egress_packets()

    fw_2_outside_ingress   = tb.vxlan_al_1.fw_2.outside.get_ingress_packets()
    fw_2_inside_egress     = tb.vxlan_al_1.fw_2.inside.get_egress_packets()

    visp_1_outside_ingress = tb.vxlan_al_1.visp_1.outside.get_ingress_packets()
    visp_1_inside_egress   = tb.vxlan_al_1.visp_1.inside.get_egress_packets()

    visp_2_outside_ingress = tb.vxlan_al_1.visp_2.outside.get_ingress_packets()
    visp_2_inside_egress   = tb.vxlan_al_1.visp_2.inside.get_egress_packets()

    log_fmt_a = ' ||      |       |{:>11}    |       |          |       | {:>10}    |       |'

    log_file.info("  VISP & FW Northbound" )
    log_file.info("    " )
    log_file.info(" /\ " )
    log_file.info(" || " )
    log_file.info(" ||      fw1                     bl1                      bl2                     fw2" )
    log_file.info(" ||      +-------+               +-------+          +-------+               +-------+")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |-------------->|       |          |       |<--------------|       |")
    log_file.info(log_fmt_a.format(fw_1_outside_egress, fw_2_outside_egress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |<--------------|       |          |       |-------------->|       |")
    log_file.info(log_fmt_a.format(fw_1_inside_ingress, fw_2_inside_ingress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      +-------+               |       |          |       |               +-------+")
    log_file.info(" ||                              |       |          |       |" )
    log_file.info(" ||      visp1                   |       |          |       |                   visp2" )
    log_file.info(" ||      +-------+               |       |          |       |               +-------+")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |-------------->|       |          |       |<--------------|       |")
    log_file.info(log_fmt_a.format(visp_1_outside_egress,visp_2_outside_egress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |<--------------|       |          |       |-------------->|       |")
    log_file.info(log_fmt_a.format(visp_1_inside_ingress,visp_2_inside_ingress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      +-------+               +-------+          +-------+               +-------+")
    log_file.info(" || " )

def show_south_visp_fw_usage():


    # Northbound
    visp_1_inside_ingress  = tb.vxlan_al_1.visp_1.inside.get_ingress_packets()
    visp_1_outside_egress  = tb.vxlan_al_1.visp_1.outside.get_egress_packets()

    visp_2_inside_ingress  = tb.vxlan_al_1.visp_2.inside.get_ingress_packets()
    visp_2_outside_egress  = tb.vxlan_al_1.visp_2.outside.get_egress_packets()

    fw_1_inside_ingress    = tb.vxlan_al_1.fw_1.inside.get_ingress_packets()
    fw_1_outside_egress    = tb.vxlan_al_1.fw_1.outside.get_egress_packets()

    fw_2_inside_ingress    = tb.vxlan_al_1.fw_2.inside.get_ingress_packets()
    fw_2_outside_egress    = tb.vxlan_al_1.fw_2.outside.get_egress_packets()

    # Southbound
    fw_1_outside_ingress   = tb.vxlan_al_1.fw_1.outside.get_ingress_packets()
    fw_1_inside_egress     = tb.vxlan_al_1.fw_1.inside.get_egress_packets()

    fw_2_outside_ingress   = tb.vxlan_al_1.fw_2.outside.get_ingress_packets()
    fw_2_inside_egress     = tb.vxlan_al_1.fw_2.inside.get_egress_packets()

    visp_1_outside_ingress = tb.vxlan_al_1.visp_1.outside.get_ingress_packets()
    visp_1_inside_egress   = tb.vxlan_al_1.visp_1.inside.get_egress_packets()

    visp_2_outside_ingress = tb.vxlan_al_1.visp_2.outside.get_ingress_packets()
    visp_2_inside_egress   = tb.vxlan_al_1.visp_2.inside.get_egress_packets()

    log_fmt_a = ' ||      |       |{:>11}    |       |          |       | {:>10}    |       |'

    log_file.info("  VISP & FW Southbound" )
    log_file.info("    " )
    log_file.info(" || " )
    log_file.info(" ||      fw1                     bl1                      bl2                     fw2" )
    log_file.info(" ||      +-------+               +-------+          +-------+               +-------+")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |<--------------|       |          |       |-------------->|       |")
    log_file.info(log_fmt_a.format(fw_1_outside_ingress, fw_2_outside_ingress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |-------------->|       |          |       |<--------------|       |")
    log_file.info(log_fmt_a.format(fw_1_inside_egress, fw_2_inside_egress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      +-------+               |       |          |       |               +-------+")
    log_file.info(" ||                              |       |          |       |" )
    log_file.info(" ||      visp1                   |       |          |       |                   visp2" )
    log_file.info(" ||      +-------+               |       |          |       |               +-------+")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |<--------------|       |          |       |-------------->|       |")
    log_file.info(log_fmt_a.format(visp_1_outside_ingress,visp_2_outside_ingress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      |       |-------------->|       |          |       |<--------------|       |")
    log_file.info(log_fmt_a.format(visp_1_inside_egress,visp_2_inside_egress))
    log_file.info(" ||      |       |               |       |          |       |               |       |")
    log_file.info(" ||      +-------+               +-------+          +-------+               +-------+")
    log_file.info(" || " )
    log_file.info(" \/ " )

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
    for traffic_item in tb.ixia_poc.traffic_names:
        if 'Multicast' in traffic_item:
            log_file.info("Skip Multicast loss ms plot")
        else:
            loss_ms = tb.ixia_poc.get_stats(traffic_item,'loss_ms')
            kpidict['.'.join([kpi,traffic_item])] = loss_ms

    test_result_list.append(kpidict)

    return test_result_list

def sanity():

    result = True
    return result


def fail_hub_1_to_access_1():

    result = True

    tb.hub_1.to_al_1.shutdown(snmp=True)
    return result

def fail_hub_2_to_access_2():

    result = True

    tb.hub_2.to_al_2.shutdown(snmp=True)
    return result

def fail_access_1_to_spine_1():

    result = True

    tb.al_1.to_spine_1.shutdown(snmp=True)
    return result


def fail_access_1_to_spine_2():

    result = True

    tb.al_1.to_spine_2.shutdown(snmp=True)
    return result


def fail_access_2_to_spine_1():

    result = True

    tb.al_2.to_spine_1.shutdown(snmp=True)
    return result


def fail_access_2_to_spine_2():

    result = True

    tb.al_2.to_spine_2.shutdown(snmp=True)
    return result


def fail_access_3_to_spine_1_1():

    result = True

    tb.al_3.to_spine_1_1.shutdown(snmp=True)
    return result

def fail_access_3_to_spine_1_2():

    result = True

    tb.al_4.to_spine_1_2.shutdown(snmp=True)
    return result

def fail_access_3_to_spine_2_1():

    result = True

    tb.al_3.to_spine_2_1.shutdown(snmp=True)
    return result

def fail_access_3_to_spine_2_2():

    result = True

    tb.al_3.to_spine_2_1.shutdown(snmp=True)
    return result

def fail_access_4_to_spine_1_1():

    result = True

    tb.al_4.to_spine_1_1.shutdown(snmp=True)
    return result

def fail_access_4_to_spine_1_2():

    result = True

    tb.al_4.to_spine_1_2.shutdown(snmp=True)
    return result

def fail_access_4_to_spine_2_1():

    result = True

    tb.al_4.to_spine_2_1.shutdown(snmp=True)
    return result

def fail_access_4_to_spine_2_2():

    result = True

    tb.al_4.to_spine_2_1.shutdown(snmp=True)
    return result

def fail_exit_1_to_spine_1():

    result = True

    tb.bl_1.to_spine_1.shutdown(snmp=True)
    return result


def fail_exit_1_to_spine_2():

    result = True

    tb.bl_1.to_spine_2.shutdown(snmp=True)
    return result


def fail_exit_2_to_spine_1():

    result = True

    tb.bl_2.to_spine_1.shutdown(snmp=True)
    return result


def fail_exit_2_to_spine_2():

    result = True

    tb.bl_2.to_spine_2.shutdown(snmp=True)
    return result


def fail_exit_1_to_ense_vxlan():

    result = True

    tb.bl_1.to_ense_vxlan.shutdown(snmp=True)
    return result


def fail_exit_2_to_ense_vxlan():

    result = True

    tb.bl_2.to_ense_vxlan.shutdown(snmp=True)
    return result

def fail_ixr_to_hub_1():

    result = True

    tb.ca_1.to_hub_1.shutdown(snmp=True)

    return result

def fail_ixr_to_hub_2():

    result = True

    tb.ca_1.to_hub_2.shutdown(snmp=True)

    return result

def ran_vrrp_switch_and_recover():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Switch VRRP from Hub 1 to Hub 2")
    log_file.info("-----------------------------------")

    tb.ca_1.to_hub_1.shutdown(snmp=True)
    time.sleep(5)

    log_file.info("-----------------------------------")
    log_file.info("Switch VRRP from Hub 2 to Hub 1")
    log_file.info("-----------------------------------")

    tb.ca_1.to_hub_1.no_shutdown(snmp=True)
    time.sleep(5)
    tb.ca_1.to_hub_2.shutdown(snmp=True)
    time.sleep(5)
    tb.ca_1.to_hub_2.no_shutdown(snmp=True)

    return result

def fail_vc_uplink_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Fail EDN VC Uplink 1 ")
    log_file.info("-----------------------------------")

    tb.vc.uplink_1.shutdown(snmp=True)

    return result

def fail_vc_uplink_2():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Fail EDN VC Uplink 2 ")
    log_file.info("-----------------------------------")

    tb.vc.uplink_2.shutdown(snmp=True)

    return result

def reboot_exit_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Border Leaf 1")
    log_file.info("-----------------------------------")

    tb.bl_1.sr_reboot()
    tb.bl_1.close()
    return result

def reboot_exit_2():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Border Leaf 2")
    log_file.info("-----------------------------------")

    tb.bl_2.sr_reboot()
    return result

def reboot_spine_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Spine 1")
    log_file.info("-----------------------------------")

    tb.spine_1.sr_reboot()
    tb.spine_1.close()
    return result

def reboot_vxlan_spine_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Spine 1")
    log_file.info("-----------------------------------")

    tb.vxlan_spine_1.sr_reboot()
    return result

def reboot_access_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Access 1")
    log_file.info("-----------------------------------")

    tb.al_1.sr_reboot()
    tb.al_1.close()
    return result

def reboot_access_3():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Access 3")
    log_file.info("-----------------------------------")

    tb.al_3.sr_reboot()
    tb.al_3.close()

    log_file.info("--------------------------------------------------")
    log_file.info("Simulate Host Losing GW & Switching To Its Standby")
    log_file.info("--------------------------------------------------")

    tb.ixr6.to_vc_imm_1.shutdown(snmp=True)
    tb.ixr6.to_vc_imm_2.no_shutdown(snmp=True)
    tb.ixr6.send_cli_command('/clear service id %s fdb all' %(tb.ixr6.edn_vpls_411.id)) 
    tb.wbx32.send_cli_command('/clear service id %s fdb all' %(tb.wbx32.edn_vpls_411.id)) 

    return result

def reboot_hub_1():

    result = True

    log_file.info("-----------------------------------")
    log_file.info("Reboot Hub 1")
    log_file.info("-----------------------------------")

    tb.hub_1.sr_reboot()
    tb.hub_1.close()
    return result

def isolate_exit_1():
    tb.bl_1.to_ense_vxlan.shutdown(snmp=True)
    tb.bl_1.to_spine_1.shutdown(snmp=True)
    tb.bl_1.to_spine_2.shutdown(snmp=True)
    result = True
    return result

def isolate_exit_2():
    tb.bl_2.to_ense_vxlan.shutdown(snmp=True)
    tb.bl_2.to_spine_1.shutdown(snmp=True)
    tb.bl_2.to_spine_2.shutdown(snmp=True)
    result = True
    return result

def isolate_spine_1():
    tb.spine_1.to_bl_1.shutdown(snmp=True)
    tb.spine_1.to_bl_2.shutdown(snmp=True)
    tb.spine_1.to_al_1.shutdown(snmp=True)
    tb.spine_1.to_al_2.shutdown(snmp=True)
    result = True
    return result

def isolate_spine_2():
    tb.spine_2.to_bl_1.shutdown(snmp=True)
    tb.spine_2.to_bl_2.shutdown(snmp=True)
    tb.spine_2.to_al_1.shutdown(snmp=True)
    tb.spine_2.to_al_2.shutdown(snmp=True)
    result = True
    return result

def isolate_access_1():
    tb.al_1.to_spine_1.shutdown(snmp=True)
    tb.al_1.to_spine_2.shutdown(snmp=True)
    tb.al_1.to_hub_1.shutdown(snmp=True)
    result = True
    return result

def isolate_access_2():
    tb.al_2.to_spine_1.shutdown(snmp=True)
    tb.al_2.to_spine_2.shutdown(snmp=True)
    tb.al_2.to_hub_2.shutdown(snmp=True)
    result = True
    return result

def isolate_hub_1():
    tb.hub_1.to_al_1.shutdown(snmp=True)
    #tb.hub_1.to_hub_2.shutdown(snmp=True)
    tb.hub_1.to_wbx.shutdown(snmp=True)
    result = True
    return result

def isolate_hub_2():
    tb.hub_2.to_al_2.shutdown(snmp=True)
    #tb.hub_2.to_hub_1.shutdown(snmp=True)
    tb.hub_2.to_wbx.shutdown(snmp=True)
    result = True
    return result

def edn_host_switch_active_to_standby():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Simulate an EDN host activity switch - active to standby")
    log_file.info("--------------------------------------------------------")
    tb.ixr6.to_vc_imm_1.shutdown(snmp=True)
    tb.ixr6.to_vc_imm_2.no_shutdown(snmp=True)
    tb.ixr6.send_cli_command('/clear service id %s fdb all' %(tb.ixr6.edn_vpls_411.id)) 
    tb.wbx32.send_cli_command('/clear service id %s fdb all' %(tb.wbx32.edn_vpls_411.id)) 
    if not tb.al_4.wait_arp_nd('12:1:74:1:1:1:1:11',4,'"Remote  ARP-ND"',61):
        result = False
    if not tb.al_3.wait_arp_nd('12:1:74:1:1:1:1:11',4,'"Remote  EVPN"',61):
        result = False
    return result

def edn_host_switch_standby_to_active():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Simulate an EDN host activity switch - standby to active")
    log_file.info("--------------------------------------------------------")
    tb.ixr6.to_vc_imm_2.shutdown(snmp=True)
    tb.ixr6.to_vc_imm_1.no_shutdown(snmp=True)
    tb.ixr6.send_cli_command('/clear service id %s fdb all' %(tb.ixr6.edn_vpls_411.id)) 
    tb.wbx32.send_cli_command('/clear service id %s fdb all' %(tb.wbx32.edn_vpls_411.id)) 
    if not tb.al_3.wait_arp_nd('12:1:74:1:1:1:1:11',4,'"Remote  ARP-ND"',61):
        result = False
    if not tb.al_4.wait_arp_nd('12:1:74:1:1:1:1:11',4,'"Remote  EVPN"',61):
        result = False
    return result

def edn_vc_uplink_1_fail():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Fail VC uplink #1")
    log_file.info("--------------------------------------------------------")
    tb.vc.uplink_1.shutdown(snmp=True)
    return result

def edn_vc_uplink_2_fail():
    result = True
    log_file.info("")
    log_file.info("--------------------------------------------------------")
    log_file.info("Fail VC uplink #2")
    log_file.info("--------------------------------------------------------")
    tb.vc.uplink_2.shutdown(snmp=True)
    return result

def fail_vxlan_access_1_to_vxlan_spine_1():

    result = True

    tb.vxlan_al_1.to_vxlan_spine_1.shutdown(snmp=True)
    return result

def fail_vxlan_access_1_to_vxlan_spine_2():

    result = True

    tb.vxlan_al_1.to_vxlan_spine_2.shutdown(snmp=True)
    return result

def fail_vxlan_access_2_to_vxlan_spine_1():

    result = True

    tb.vxlan_al_2.to_vxlan_spine_1.shutdown(snmp=True)
    return result

def fail_vxlan_access_2_to_vxlan_spine_2():

    result = True

    tb.vxlan_al_2.to_vxlan_spine_2.shutdown(snmp=True)
    return result

def fail_exit_1_to_vxlan_spine_1():

    result = True

    tb.bl_1.to_vxlan_spine_1.shutdown(snmp=True)
    return result

def fail_exit_1_to_vxlan_spine_2():

    result = True

    tb.bl_1.to_vxlan_spine_2.shutdown(snmp=True)
    return result

def fail_exit_2_to_vxlan_spine_1():

    result = True

    tb.bl_2.to_vxlan_spine_1.shutdown(snmp=True)
    return result

def fail_exit_2_to_vxlan_spine_2():

    result = True

    tb.bl_2.to_vxlan_spine_2.shutdown(snmp=True)
    return result


def fail_visp_1():

    result = True
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Fail VISP 1")
    log_file.info("-----------------------------------")   
    tb.vxlan_al_1.visp_1.shutdown()
    return result

def fail_visp_2():

    result = True
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Fail VISP 2")
    log_file.info("-----------------------------------")   
    tb.vxlan_al_1.visp_2.shutdown()
    return result

def fail_both_visp():

    result = True
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Fail VISP 1 and VISP 2")
    log_file.info("-----------------------------------")   
    tb.vxlan_al_1.visp_1.shutdown()
    tb.vxlan_al_1.visp_2.shutdown()
    return result

def fail_fw_1():

    result = True
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Fail FW 1")
    log_file.info("-----------------------------------")   
    tb.vxlan_al_1.fw_1.shutdown()
    return result

def fail_fw_2():

    result = True
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Fail FW 2")
    log_file.info("-----------------------------------")   
    tb.vxlan_al_1.fw_2.shutdown()
    return result

def restore_visp_1():

    result = True
    tb.vxlan_al_1.visp_1.no_shutdown()
    return result

def restore_visp_2():

    result = True
    tb.vxlan_al_1.visp_2.no_shutdown()
    return result

def restore_both_visp():

    result = True
    tb.vxlan_al_1.visp_1.no_shutdown()
    tb.vxlan_al_1.visp_2.no_shutdown()
    return result

def restore_fw_1():

    result = True
    tb.vxlan_al_1.fw_1.no_shutdown()
    return result

def restore_fw_2():

    result = True
    tb.vxlan_al_1.fw_2.no_shutdown()
    return result

def fail_exit_1_to_pe():

    result = True

    tb.bl_1.to_ense_vxlan.shutdown(snmp=True)
    return result

def fail_exit_2_to_pe():

    result = True

    tb.bl_2.to_ense_vxlan.shutdown(snmp=True)
    return result

def restore_base_set_up(mode):

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("No shutdown all ports")
    log_file.info("-----------------------------------")
    for nx in tb.node_dict.values():
        for px in nx.port_dict.values() :
            px.no_shutdown(snmp=True,verbose=False)
    tb.ixr6.to_vc_imm_2.shutdown(snmp=True)
    tb.ixr6.to_vc_imm_1.no_shutdown(snmp=True)
    tb.ixr6.send_cli_command('/clear service id %s fdb all' %(tb.ixr6.edn_vpls_411.id)) 
    tb.wbx32.send_cli_command('/clear service id %s fdb all' %(tb.wbx32.edn_vpls_411.id)) 

    #Allan
    restore_visp_1()
    restore_visp_2()
    restore_fw_1()
    restore_fw_2()


def check_base_set_up(wait):

    result = True
    count = 0

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Check ports")
    log_file.info("-----------------------------------")
    log_file.info("Wait up to %s seconds for all testbed ports to come oper up" %(wait))
    while count <= wait:
        # Allan
        # I think line below has to go
        # Do post poc
        result = True 
        for nx in tb.node_dict.values():
            for px in nx.port_dict.values() :
                port_oper_status  = px.get_port_info('oper', verbose=True)
                if port_oper_status == 'down':
                    if 'to_vc_imm_' in px.name:
                        log_file.info("-----------------------------------------------")
                        log_file.info("IXR to VC IMM port is down - OK - it's expected")
                        log_file.info("-----------------------------------------------")
                        result = True
                    elif 'to_mls' in px.name:
                        log_file.info("-----------------------------------------------")
                        log_file.info("BL to MLS port is down     - OK - it's expected")
                        log_file.info("-----------------------------------------------")
                        result = True
                    else:
                        result = False 
        if result:
            log_file.info("All Port Oper Up After %s seconds" %(count))
            break
        else:
            count +=1
            time.sleep(1)
            log_file.info("")

    return result


def check_stats(max_outage,testcase_name):

    result = True

    log_file.info("")
    log_file.info("--------------------------------------------------")
    log_file.info("Get stats for all traffic items")
    log_file.info("--------------------------------------------------")

    tb.ixia_poc.set_stats()

    for traffic_item in tb.ixia_poc.traffic_names:
        if tb.ixia_poc.get_stats(traffic_item,'rx') > tb.ixia_poc.get_stats(traffic_item,'tx'):
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
            loss_ms = tb.ixia_poc.get_stats(traffic_item,'loss_ms')
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
            
def check_imn_inband_mgt():

    ping_result = True
    
    if not tb.imn_102.ping():
        ping_result = False
    if not tb.imn_105.ping():
        ping_result = False
    if not tb.al_4.ping():
        ping_result = False
    if not tb.vc.ping():
        ping_result = False

    return ping_result

def ping_all_nodes():

    ping_result = True
    for nx in tb.node_dict.values():
        if not nx.ping():
            log_file.error("Ping to %s failed" %(nx.name))
            ping_result = False

    return ping_result

def main(testcase_name='',testsuite_name='vzw_5g_poc',csv='false',testbed_file='vzw_5g_poc.yaml'):

    test_pass                  = True 
    #test_path                 = '/automation/python/tests/'
    #testbed_file              = test_path+testbed_file
    port_wait                  = 120
    underlay                   = 'v4'
    max_outage_sanity          = 0
    max_outage_default         = 250
    max_outage_reboot          = 2000
    max_outage_vrrp            = 4000
    max_outage_edn_host_switch = 2000
    max_outage_visp_fail       = 4500
    max_outage_fw_fail         = 4500


    # Initialize the testbed
    testbed_init(testbed_file)

    # Shutdown links to MLS1 and MLS2
    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info("Shutdown links to MLS1 and MLS2")
    log_file.info("Offload Project")
    log_file.info("-----------------------------------")
    tb.bl_1.to_mls_1.shutdown(snmp=True)
    tb.bl_2.to_mls_2.shutdown(snmp=True)

    # Print testbed info
    print_testbed_info()

    
    # Set testbed mode based on testcase name
    if 'access_no_vprn' in testcase_name:
        mode = 'access_no_vprn'
    elif 'access_vprn' in testcase_name:
        mode = 'access_vprn'
    else:
        log_file.error("Can't find testbed mode .. assume no VPRNs on access nodes")
        mode = 'access_no_vprn'

    testbed_config(mode,underlay)
    set_all_port_ether_stats_itvl(30)

    if 'reboot' in testcase_name:
        log_file.info("")
        log_file.info("----------------------------------------------------")
        log_file.info("Reboot Test Detected: Perform admin save on all node")
        log_file.info("----------------------------------------------------")
        tb.bl_1.admin_save()
        tb.bl_2.admin_save()
        tb.spine_1.admin_save()
        tb.spine_2.admin_save()
        tb.al_1.admin_save()
        tb.al_2.admin_save()
        tb.al_3.admin_save()
        tb.al_4.admin_save()
        tb.hub_1.admin_save()
        tb.hub_2.admin_save()
        tb.ca_1.admin_save()
        tb.imn_102.admin_save()
        tb.imn_105.admin_save()
        tb.vc.admin_save()
        tb.vxlan_al_1.admin_save()
    else:
        log_file.info("")
        log_file.info("-------------------------------------")
        log_file.info("Not a Reboot Test: Skip admin saves ")
        log_file.info("-------------------------------------")


    if 'ran' in testcase_name:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("RAN detected in testcase name")
        log_file.info("Enable EVPN SR RAN Ixia streams")
        log_file.info("-----------------------------------")
        log_file.info("")
        ixia_pattern = 'SR-RAN' 
    elif 'edn' in testcase_name:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Enable EVPN SR EDN Ixia streams")
        log_file.info("-----------------------------------")
        ixia_pattern = 'SR-EDN' 
    elif 'vxlan_' in testcase_name:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Enable EVPN VXLAN RAN Ixia streams")
        log_file.info("-----------------------------------")
        ixia_pattern = 'a-' 
    elif 'vxlansr' in testcase_name:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Enable EVPN VXLAN To RAN Ixia streams")
        log_file.info("-----------------------------------")
        ixia_pattern = 'a-' 
    else:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Enable RAN and EDN Ixia streams")
        log_file.info("-----------------------------------")
        ixia_pattern = '-v' 

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
    restore_base_set_up 

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info('Check all expected ports are up')
    log_file.info("-----------------------------------")
    if not check_base_set_up(30): 
        test_pass = False
        log_file.error("")
        log_file.error("-----------------------------------")
        log_file.error('Base set up check failed - ports down')
        log_file.error("-----------------------------------")

    log_file.info("")
    log_file.info("-----------------------------------")
    log_file.info('Check all nodes for hw errors')
    log_file.info("-----------------------------------")

    for error_node in tb.node_dict.values():
        error_node.check_for_hw_errors()
            
    #Put this back in once design has been fixed
    #log_file.info("")
    #log_file.info("------------------------------------------")
    #log_file.info('Check all expected ISIS adjacencies are up')
    #log_file.info("------------------------------------------")

    log_file.info("")
    log_file.info("------------------------------------------")
    log_file.info('Check PIM has been resolved')
    log_file.info("------------------------------------------")
    if not tb.hub_1.wait_pim_resolved(tb.hub_1.ran_vprn.id,'ipv6',60): test_pass = False
    else:
        log_file.info('PIM resolved.  Look at details on Hub 1')
        tb.hub_1.send_cli_command('show router %s pim group %s' %(tb.hub_1.ran_vprn.id,'ipv6'), see_return=True)

    log_file.info("")
    log_file.info("------------------------------------------")
    log_file.info('Look at the number of BGP routes')
    log_file.info("------------------------------------------")
    tb.bl_1.send_cli_command('show router bgp summary neighbor 1.1.1.113 |  match Summary post-lines 13' , see_return=True)

    log_file.info("------------------------------------------")
    log_file.info('Ping all nodes ')
    log_file.info("------------------------------------------")
    if not ping_all_nodes(): 
        test_pass = False

    log_file.info("")
    log_file.info("------------------------------------------")
    log_file.info('Check inband management of IMN switches ')
    log_file.info("------------------------------------------")
    if not check_imn_inband_mgt(): 
        test_pass = False

    if not test_pass:
        log_file.info("")
        log_file.info("----------------------------------------")
        log_file.info("Initial checks did not pass.  Skip test.")
        log_file.info("----------------------------------------")

        test_result_list = [] 
        if test_pass:
            test_result = 'PASS'
        else:
            test_result = 'FAIL'

        test_result_list.append(test_result)

        # Stop the clock 
        end_time = datetime.now()
        test_dur = end_time - start_time
        duration = test_dur.total_seconds()

        # Print test result
        print_test_result(testcase_name,test_pass, duration)

    else:
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Force Hub 1 to be RAN VRRP Master ")
        log_file.info("-----------------------------------")
        tb.ca_1.to_hub_2.shutdown(snmp=True)
        time.sleep(5)
        tb.ca_1.to_hub_2.no_shutdown(snmp=True)
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Force the EDN ALs to initiate a gratuitous ARP ")
        log_file.info("-----------------------------------")
        tb.vc.uplink_1.shutdown(snmp=True)
        tb.vc.uplink_2.shutdown(snmp=True)
        time.sleep(2)
        tb.vc.uplink_1.no_shutdown(snmp=True)
        tb.vc.uplink_2.no_shutdown(snmp=True)
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Enable Ixia streams")
        log_file.info("-----------------------------------")
        if "e_w_local_hub" in testcase_name:
            tb.ixia_poc.set_traffic(pattern='East-West-Hub-2-Hub-3', commit=True)
        elif "e_w_remote_hub" in testcase_name:
            log_file.info("")
            log_file.info("-----------------------------------")
            log_file.info("Simulate remote hubs")
            log_file.info("-----------------------------------")
            tb.hub_1.to_hub_2.shutdown(snmp=True)
            tb.hub_2.to_hub_1.shutdown(snmp=True)
            tb.ixia_poc.set_traffic(pattern='East-West-Hub-1-Hub-3', commit=True)
        else:
            tb.ixia_poc.set_traffic(pattern=ixia_pattern, commit=True)


        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("Start Ixia streams")
        log_file.info("-----------------------------------")
        tb.ixia_poc.start_traffic()

        utils.countdown(10)

        # Clear Ixia stats  
        tb.ixia_poc.clear_stats()
        tb.vxlan_al_1.send_cli_command("/clear service statistics id [1000,2000,1100,2100] counters")
        utils.countdown(10)

        # Show initial traffic flow 
        if 'vxlan' in testcase_name:
            show_north_traffic_util_vx()
            show_north_visp_fw_usage()
            show_south_traffic_util_vx()
            show_south_visp_fw_usage()
        else:
            show_north_traffic_util()
            show_south_traffic_util()

        # Run the testcase 
        tmp_pattern = tb.ixia_poc.pattern
        max_outage = max_outage_default
        
        # TODO - Change this to if 'xxx' in yyy
        if 'testbed_setup' in testcase_name:
            if not testbed_setup():  test_pass = False
        elif 'testbed_teardown' in testcase_name:
            if not testbed_teardown():  test_pass = False
        elif 'sanity_access' in testcase_name:
            max_outage = max_outage_sanity 
        elif 'e_w_local_hub_sanity_access' in testcase_name:
            max_outage = max_outage_sanity 
        elif 'e_w_remote_hub_sanity_access' in testcase_name:
            max_outage = max_outage_sanity 
            tb.hub_1.to_hub_2.shutdown(snmp=True)
            tb.hub_2.to_hub_1.shutdown(snmp=True)
        elif 'fail_hub_1_to_access_1' in testcase_name:
            if not fail_hub_1_to_access_1(): test_pass = False 
        elif 'fail_hub_2_to_access_2' in testcase_name:
            if not fail_hub_2_to_access_2(): test_pass = False 
        elif 'fail_access_1_to_spine_1' in testcase_name:
            if not fail_access_1_to_spine_1(): test_pass = False 
        elif 'fail_access_1_to_spine_2' in testcase_name:
            if not fail_access_1_to_spine_2(): test_pass = False 
        elif 'fail_access_2_to_spine_1' in testcase_name:
            if not fail_access_2_to_spine_1(): test_pass = False 
        elif 'fail_access_2_to_spine_2' in testcase_name:
            if not fail_access_2_to_spine_2(): test_pass = False 
        elif 'fail_access_3_to_spine_1_1' in testcase_name:
            if not fail_access_3_to_spine_1_1(): test_pass = False 
        elif 'fail_access_3_to_spine_1_2' in testcase_name:
            if not fail_access_3_to_spine_1_2(): test_pass = False 
        elif 'fail_access_3_to_spine_2_1' in testcase_name:
            if not fail_access_3_to_spine_2_1(): test_pass = False 
        elif 'fail_access_3_to_spine_2_2' in testcase_name:
            if not fail_access_3_to_spine_2_2(): test_pass = False 
        elif 'fail_access_4_to_spine_1_1' in testcase_name:
            if not fail_access_4_to_spine_1_1(): test_pass = False 
        elif 'fail_access_4_to_spine_1_2' in testcase_name:
            if not fail_access_4_to_spine_1_2(): test_pass = False 
        elif 'fail_access_4_to_spine_2_1' in testcase_name:
            if not fail_access_4_to_spine_2_1(): test_pass = False 
        elif 'fail_access_4_to_spine_2_2' in testcase_name:
            if not fail_access_4_to_spine_2_2(): test_pass = False 
        elif 'fail_exit_1_to_spine_1' in testcase_name:
            if not fail_exit_1_to_spine_1(): test_pass = False 
        elif 'fail_exit_1_to_spine_2' in testcase_name:
            if not fail_exit_1_to_spine_2(): test_pass = False 
        elif 'fail_exit_2_to_spine_1' in testcase_name:
            if not fail_exit_2_to_spine_1(): test_pass = False 
        elif 'fail_exit_2_to_spine_2' in testcase_name:
            if not fail_exit_2_to_spine_2(): test_pass = False 
        elif 'fail_exit_1_to_ense_vxlan' in testcase_name:
            if not fail_exit_1_to_ense_vxlan(): test_pass = False 
        elif 'fail_exit_2_to_ense_vxlan_access' in testcase_name:
            if not fail_exit_2_to_ense_vxlan(): test_pass = False 
        elif 'isolate_exit_1' in testcase_name:
            max_outage = max_outage_reboot 
            if not isolate_exit_1(): test_pass = False 
        elif 'isolate_spine_1' in testcase_name:
            max_outage = max_outage_reboot 
            if not isolate_spine_1(): test_pass = False 
        elif 'isolate_access_1' in testcase_name:
            max_outage = max_outage_reboot 
            if not isolate_access_1(): test_pass = False 
        elif 'isolate_hub_1' in testcase_name:
            if not isolate_hub_1(): test_pass = False 
        elif 'reboot_exit_1' in testcase_name:
            max_outage = max_outage_reboot 
            if not reboot_exit_1(): test_pass = False 
        elif 'reboot_spine_1' in testcase_name:
            if not reboot_spine_1(): test_pass = False 
        elif 'reboot_access_1' in testcase_name:
            if not reboot_access_1(): test_pass = False 
        elif 'reboot_hub_1' in testcase_name:
            if not reboot_hub_1(): test_pass = False 
        elif 'reboot_access_3' in testcase_name:
            if not reboot_access_3(): test_pass = False 
        elif 'edn_host_switch_active_to_standby' in testcase_name:
            max_outage = max_outage_edn_host_switch
            if not edn_host_switch_active_to_standby(): test_pass = False 
        elif 'edn_host_switch_standby_to_active' in testcase_name:
            max_outage = max_outage_edn_host_switch
            if not edn_host_switch_standby_to_active(): test_pass = False 
        elif 'edn_vc_uplink_1_fail' in testcase_name:
            max_outage = max_outage_edn_host_switch
            if not edn_vc_uplink_1_fail(): test_pass = False 
        elif 'edn_vc_uplink_2_fail' in testcase_name:
            max_outage = max_outage_edn_host_switch
            if not edn_vc_uplink_2_fail(): test_pass = False 
        elif 'vxlan_fail_vxlan_access_1_to_vxlan_spine_1' in testcase_name:
            if not fail_vxlan_access_1_to_vxlan_spine_1(): test_pass = False 
        elif 'vxlan_fail_vxlan_access_1_to_vxlan_spine_2' in testcase_name:
            if not fail_vxlan_access_1_to_vxlan_spine_2(): test_pass = False 
        elif 'vxlan_fail_vxlan_access_2_to_vxlan_spine_2' in testcase_name:
            if not fail_vxlan_access_2_to_vxlan_spine_2(): test_pass = False 
        elif 'vxlan_fail_vxlan_access_2_to_vxlan_spine_2' in testcase_name:
            if not fail_vxlan_access_2_to_vxlan_spine_2(): test_pass = False 
        elif 'vxlan_fail_exit_1_to_vxlan_spine_1' in testcase_name:
            if not fail_exit_1_to_vxlan_spine_1(): test_pass = False 
        elif 'vxlan_fail_exit_1_to_vxlan_spine_2' in testcase_name:
            if not fail_exit_1_to_vxlan_spine_2(): test_pass = False 
        elif 'vxlan_fail_exit_2_to_vxlan_spine_1' in testcase_name:
            if not fail_exit_2_to_vxlan_spine_1(): test_pass = False 
        elif 'vxlan_fail_exit_2_to_vxlan_spine_2' in testcase_name:
            if not fail_exit_2_to_vxlan_spine_2(): test_pass = False 
        elif 'vxlan_fail_exit_1_to_pe' in testcase_name:
            if not fail_exit_1_to_pe(): test_pass = False 
        elif 'vxlan_fail_exit_2_to_pe' in testcase_name:
            if not fail_exit_2_to_pe(): test_pass = False 
        elif 'vxlan_fail_visp_1' in testcase_name:
            max_outage = max_outage_visp_fail
            if not fail_visp_1(): test_pass = False 
        elif 'vxlan_fail_visp_2' in testcase_name:
            max_outage = max_outage_visp_fail
            if not fail_visp_2(): test_pass = False 
        elif 'vxlan_fail_both_visp' in testcase_name:
            max_outage = max_outage_visp_fail
            if not fail_both_visp(): test_pass = False 
        elif 'vxlan_fail_fw_1' in testcase_name:
            max_outage = max_outage_fw_fail
            if not fail_fw_1(): test_pass = False 
        elif 'vxlan_fail_fw_2' in testcase_name:
            max_outage = max_outage_fw_fail
            if not fail_fw_2(): test_pass = False 
        elif 'vxlan_reboot_vxlan_spine_1' in testcase_name:
            if not reboot_vxlan_spine_1(): test_pass = False 
        elif 'vxlan_reboot_exit_2' in testcase_name:
            max_outage = max_outage_reboot 
            if not reboot_exit_2(): test_pass = False 
        elif 'ran_vrrp_fail_and_recover' in testcase_name:
            max_outage = max_outage_vrrp 
            if not ran_vrrp_switch_and_recover():  test_pass = False
        elif 'fail_vc_uplink_1' in testcase_name:
            max_outage = max_outage_vrrp 
            if not fail_vc_uplink_1():  test_pass = False
        elif 'fail_vc_uplink_2' in testcase_name:
            max_outage = max_outage_vrrp 
            if not fail_vc_uplink_2():  test_pass = False
        else:
            log_file.error("Testcase %s does not exist" %(testcase_name))

        # If a failure has been triggered - show resulting traffic flow 
        if 'reboot' not in testcase_name:
            if 'sanity' not in testcase_name:
                utils.countdown(30)
                if 'vxlan' in testcase_name:
                    #tb.vxlan_al_1.sshcon.cmdline("/clear service statistics id %s counters" %(tb.vxlan_al_1.visp_1.id), timeout=0)
                    #tb.vxlan_al_1.sshcon.cmdline("/clear service statistics id %s counters" %(tb.vxlan_al_1.visp_2.id), timeout=0)
                    #tb.vxlan_al_1.sshcon.cmdline("/clear service statistics id %s counters" %(tb.vxlan_al_1.fw_1.id), timeout=0)
                    #tb.vxlan_al_1.sshcon.cmdline("/clear service statistics id %s counters" %(tb.vxlan_al_1.fw_2.id), timeout=0)
                    #tb.vxlan_al_1.send_cli_command("/clear service statistics id %s counters" %(tb.vxlan_al_1.visp_1.id))
                    #tb.vxlan_al_1.send_cli_command("/clear service statistics id %s counters" %(tb.vxlan_al_1.visp_2.id))
                    #tb.vxlan_al_1.send_cli_command("/clear service statistics id %s counters" %(tb.vxlan_al_1.fw_1.id))
                    #tb.vxlan_al_1.send_cli_command("/clear service statistics id %s counters" %(tb.vxlan_al_1.fw_2.id))
                    tb.vxlan_al_1.send_cli_command("/clear service statistics id [1000,2000,1100,2100] counters")
                utils.countdown(30)
                log_file.info("")
                log_file.info("------------------------------------------")
                log_file.info('Traffic flow after network failure')
                log_file.info("------------------------------------------")
                # Show initial traffic flow 
                if 'vxlan' in testcase_name:
                    show_north_traffic_util_vx()
                    show_north_visp_fw_usage()
                    show_south_traffic_util_vx()
                    show_south_visp_fw_usage()
                else:
                    show_north_traffic_util()
                    show_south_traffic_util()


                # Check PIM again 
                log_file.info("")
                log_file.info("------------------------------------------")
                log_file.info('Check PIM is still resolved')
                log_file.info("------------------------------------------")
                if not tb.hub_1.wait_pim_resolved(tb.hub_1.ran_vprn.id,'ipv6',60): test_pass = False
                else:
                    log_file.info('PIM resolved.  Look at details on Hub 1')
                    tb.hub_1.send_cli_command('show router %s pim group %s' %(tb.hub_1.ran_vprn.id,'ipv6'), see_return=True)

        # Stop the Ixia streams
        tb.ixia_poc.stop_traffic()

        log_file.info("")
        log_file.info("------------------------------------------")
        log_file.info('Check inband management of IMN switches ')
        log_file.info("------------------------------------------")
        if 'reboot_access_3' in testcase_name:
            # Rebooting access leaf 3 isolates the IMNs
            # So let the ping fail slide for now
            # It's checked again in the reboot case below
            log_file.info('Rebooting access leaf 3 isolates IMNs - lab infra ')
            log_file.info('So do not run IMN ping test ')
            test_pass = True
        else:
            if not check_imn_inband_mgt(): 
                test_pass = False

        if 'reboot' in testcase_name:
            log_file.info('Reboot case')
            for nx in tb.node_dict.values():
               if not nx.wait_node_up(300):
                   log_file.error ("Node %s ip %s not up after 300s" %(nx.sysname, nx.ip))
            log_file.info("Nodes are back up.  But wont take CLI/SNMP commands for a while.  So wait.")    
            utils.countdown(240)

            if not check_imn_inband_mgt(): 
                test_pass = False

        # Restore all testcase failures 
        restore_base_set_up(mode)
        if testcase_name == 'fail_exit_1_to_ense_vxlan_access_no_vprn' or testcase_name == 'fail_exit_1_to_ense_vxlan_access_vprn' \
            or testcase_name == 'fail_exit_2_to_ense_vxlan_access_no_vprn' or testcase_name == 'fail_exit_2_to_ense_vxlan_access_vprn' \
            or testcase_name == 'isolate_exit_1_access_no_vprn' :
            log_file.info('BL to VXLAN SAP ports have a hold time of 120s')
            log_file.info('Wait for 120s before checking port status')
            utils.countdown(120)

        if not check_base_set_up(30): test_pass = False

        # Wait for both hubs to see the default route 
        # from both exit leaves
        if not tb.bl_1.wait_route_match('1','::/0',tb.bl_1.ran_vprn.def_nh,120): test_pass = False
        if not tb.bl_2.wait_route_match('1','::/0',tb.bl_2.ran_vprn.def_nh,120): test_pass = False

        # Wait for both hubs to see the default route 
        # from both exit leaves
        if underlay == 'v4':
            # evpn with SR
            if not tb.hub_1.wait_route_match('1','::/0',tb.hub_1.ran_vprn.def_nh,90): test_pass = False
            if not tb.hub_2.wait_route_match('1','::/0',tb.hub_2.ran_vprn.def_nh,90): test_pass = False
        else:
            if not tb.hub_1.wait_route_match('1','::/0','1:1:1:111',90): test_pass = False
            if not tb.hub_1.wait_route_match('1','::/0','1:1:1:112',90): test_pass = False
            if not tb.hub_2.wait_route_match('1','::/0','1:1:1:111',90): test_pass = False
            if not tb.hub_2.wait_route_match('1','::/0','1:1:1:112',90): test_pass = False

        # Check the Ixia stats 
        if not check_stats(max_outage,testcase_name): test_pass = False 

        # Stop the clock 
        end_time = datetime.now()
        test_dur = end_time - start_time
        duration = test_dur.total_seconds()

        # Print test result
        print_test_result(testcase_name,test_pass, duration)

        # Generate testlist
        test_result_list = generate_test_result_list(testcase_name,test_pass)

        # No Shutdown links to MLS1 and MLS2
        log_file.info("")
        log_file.info("-----------------------------------")
        log_file.info("No Shutdown links to MLS1 and MLS2")
        log_file.info("Offload Project")
        log_file.info("-----------------------------------")
        #tb.bl_1.to_mls_1.no_shutdown(snmp=True)
        #tb.bl_2.to_mls_2.no_shutdown(snmp=True)
        utils.countdown(5)

    # close ssh connections
    for nx in tb.node_dict.values():
       nx.close()

    return test_result_list


if (__name__ == '__main__'):

    print("here")
    print("here")
    print("here")
    print("here")
    print("here")
    # Get all user input command options
    try:
        optlist, args = getopt.getopt(sys.argv[1:],"t:s:c:h")
    except getopt.GetoptError as err:
        print("\nERROR: %s" %(err))
        sys.exit(0)

    test_params=dict()
    test_params['testbed_mode'] = ''
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
            print("option: %s a is not implemented yet!!"%(opt,val))
            sys.exit() 
    # Check for mandatory arguements
    if test_params['testcase_name'] == '':
        print("\nERROR: Option -t (testcase) is mandatory")
        sys.exit()

