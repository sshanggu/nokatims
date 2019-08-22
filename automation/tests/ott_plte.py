#!/usr/bin/python

###################################
#
# OTT-Private LTE tests
#
###################################
import os
import sys
import pdb
import json
import node
import utils
import logging
import calendar
from collections import OrderedDict
from datetime import datetime
from tabulate import tabulate
from utils import framelog

###############################################################################
# module common setup
###############################################################################
mylog=logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler())
today=calendar.day_name[datetime.today().weekday()]

def ppf(checks):
    cl=len(checks)
    if cl == 0 or checks.count(True) == cl: return 'PASS'
    if checks.count(False) == cl: return 'FAIL'
    return 'PARTIAL'

def ta_verify(nodes=None, ta=None, save=False, **args):
    logdata=[['UE','Port','Stat','Band','Channel',
        'RSSI','RSRP','TA','Cell','PDN','IP','Comment']]
    if not nodes: nodes=utils.find_nodes(_tbd.node_dict,'_SARHm')
    result=True
    # collect nodes LTE data
    for sr in nodes:
        pd=sr.cellif.getdetail(**args)
        if not pd:
            mylog.error('%s show port %s failed!' %(sr.name, sr.cellif))
            sr.close(); sr.connect()
            continue
        # set comment
        cmt='#'
        if pd['tracking_area']:
            cmt+=' TA=%s.' %pd['tracking_area']
        if ta:
            if ta in cmt:
                if ta == sr.area_code:
                    cmt+=' expected.'
                else:
                    cmt+=' changed and expected.'
            else:
                cmt+=' TA not expected.'
                result=False
        # append data for log
        logdata.append([sr.name, sr.cellif.port, pd['oper'],
            pd['band'], pd['channel'], pd['rssi'], pd['rsrp'],
            pd['tracking_area'], pd['cell_identity'],
            pd['pdn_state'], pd['ip_addr'], cmt])
        # save lte data into node
        if save:
            sr.lted=dict()
            sr.lted['ta']=pd['tracking_area']
            sr.lted['ip']=pd['ip_addr']
            sr.lted['pdn']=pd['pdn_state']
            sr.lted['stat']=pd['oper']
            sr.lted['band']=pd['band']
            sr.lted['rssi']=pd['rssi']
            sr.lted['rsrp']=pd['rsrp']
            sr.lted['cell']=pd['cell_identity']
            sr.lted['channel']=pd['channel']
            sr.lted['network']=pd['network_status']
 
    # log nodes LTE data with tabulate
    mylog.info('\n'+tabulate(logdata, headers='firstrow'))
    return result

###############################################################################
# test case functions
###############################################################################
# sanity1 function
def sanity1():
    results=list()
    sarhms7475=utils.find_nodes(_tbd.node_dict,'_SARHm02 - DC01|_SARHm07 - DC01|_SARHm02 - DC02|_SARHm07 - DC02')
    sarhms7455=utils.find_nodes(_tbd.node_dict,'_SARHm11 - DC02')
    sarhms=sarhms7475+sarhms7455
    #sarhms=utils.find_nodes(_tbd.node_dict,'_SARHm')

    srhm=utils.find_nodes(_tbd.node_dict,'_SARHm06 - DC01')
    vsrs=utils.find_nodes(_tbd.node_dict,'_vSRi')

    #bgpsum = vsrs[0].cliexe('show router bgp summary')
    ports = srhm[0].cliexe("show port")
    
    _tbd.SARHm06.sr_reboot2()
    ports = _tbd.SARHm06.cliexe("show port")
    _tbd.SARHm07.sr_reboot2()
    ports = _tbd.SARHm07.cliexe("show port")
    
    vsrs[0].sr_reboot2()
    ports = vsrs[0].cliexe("show port")
    
    vsrs[0].cellif.shutdown()
    sst = vsrs[0].cellif.getstate()

    ports = vsrs[0].cliexe("show port")
    vsrs[0].cellif.noshutdown()
    sst = vsrs[0].cellif.getstate()

    ports = vsrs[0].cliexe("show port")
    
    vsrs[0].cellif.shutdown(snmp=True)
    ports = vsrs[0].cliexe("show port")
    vsrs[0].cellif.noshutdown(snmp=True)
    ports = vsrs[0].cliexe("show port")

    log99 = vsrs[0].show_log_99()
    vsrs[0].clear_log_99()
    log99 = vsrs[0].show_log_99()
    srbof = vsrs[0].show_bof()
    vsrs[0].send_cli_command('/configure router isis area-id 49.0002')
    vsrs[0].send_cli_command('/configure router isis area-id 49.0003')
    vsrs[0].send_cli_command('/configure router isis area-id 49.0004')
    vsrs[0].send_cli_command('admin display-config | match area-id')
    vsrs[0].send_cli_command('/configure router isis no area-id 49.0002')
    vsrs[0].send_cli_command('/configure router isis no area-id 49.0003')
    vsrs[0].send_cli_command('/configure router isis no area-id 49.0004')
    vsrs[0].send_cli_command('admin display-config | match area-id')
    vsrs[0].shutdown_log_98()
    vsrs[0].no_shutdown_log_98()
    vsrs[0].close()
    vsrs[0].send_cli_command('admin display-config | match area-id')

    results.append('PASS')
    framelog('STEP 2: No shutdown SRHm LTE ports\n' +
             'step3: whatever is \n' +
             ' step4: good stuff\n  ' +
             '   step5: the end')
    framelog('STEP 2: No shutdown SRHm LTE ports','*')
    xx = vsrs[0].cliexe('show port')
    yy = vsrs[0].cliexe('admin display-config')
    vsrs[0].connect()
    vsrs[0].close()
    vsrs[0].send_cli_command('admin display-config | match area-id')
    vsrs[0].send_cli_command('show port')

    return results

    framelog('STEP 2: No shutdown SRHm LTE ports','*')
    for sr in sarhms: sr.cellif.noshutdown()

    framelog('STEP 3: Verify cellular-interfaces info','*')
    ta_verify(nodes=sarhms, save=True)

    for sr in sarhms7475:
        if not hasattr(sr,'lted'):
            mylog.error('%s failed to get LTE data')
            results.append(False); continue
        # verify LTE port status on 7475 SARHms
        check=True
        srpt=(sr.name, sr.cellif.port)
        if sr.lted['stat'] !='up':
            mylog.error('%s %s NOT up' %srpt); check=False
        if sr.lted['band'] != '125':
            mylog.error('%s %s band NOT 125' %srpt); check=False
        if sr.lted['pdn'] != 'connected':
            mylog.error('%s %s PDN NOT connected' %srpt); check=False
        if sr.lted['network'] != 'registered-home':
            mylog.error('%s %s network NOT registered-home' %srpt); check=False
        
        if check: mylog.info('%s %s in good state' %srpt)
        results.append(check)

    
    for sr in sarhms7455:
        if not hasattr(sr,'lted'):
            mylog.error('%s failed to get LTE data')
            results.append(False); continue
        # verify LTE port status on 7455 SARHms
        check=True
        srpt=(sr.name, sr.cellif.port)
        if sr.lted['stat'] !='up':
            mylog.error('%s %s NOT up' %srpt); check=False
        if sr.lted['band'] != '8':
            mylog.error('%s %s band NOT 8' %srpt); check=False
        if sr.lted['pdn'] != 'connected':
            mylog.error('%s %s PDN NOT connected' %srpt); check=False
        if sr.lted['network'] != 'registered-home':
            mylog.error('%s %s network NOT registered-home' %srpt); check=False
        
        if check: mylog.info('%s %s in good state' %srpt)
        results.append(check)

    for sr in vsrs:
        txt=sr.cliexe('show router bgp summary')
        if txt == 'ERROR':
            results.append(False); continue
        # parse bgp stats and verify up
        check=True
        bgpd=utils.parse_show_bgp(txt)
        if bgpd['operState'] == "Up":
            mylog.info('%s BGP Up. Good!' %sr.name)
        else:
            mylog.error('%s BGP NOT Up' %sr.name)
            check=False
        results.append(check)

    return [ppf(results)]

# mobility_test function
def mobility_test():
    results=list()

    ta1='0032'
    ta2='0001'
    ta3='000a'
    sarhmG1=utils.find_nodes(_tbd.node_dict,ta1,attr='area_code')
    #sarhmG2=utils.find_nodes(_tbd.node_dict,ta2,attr='area_code')
    #sarhms=utils.find_nodes(_tbd.node_dict,'_SARHm')
    #for dev in sarhmG1: dev.clear_console()
    #for dev in sarhmG1: dev.connect()

    rfsim1a=_tbd.rfsim1a
    # initialize rfsim1A
    framelog('STEP 0: Force group1 UEs to attach to cell-1')
    rfsim1a.set_rssi(mobiles=3, cells=1, rssi=0)
    rfsim1a.set_rssi(mobiles=3, cells=234, rssi=127)
    utils.poll(ta_verify, nodes=sarhmG1, log=False)

    # open cell-4 RF (TA=0001)
    framelog('STEP 1: Turn on cell-4 RF (TA=0001)')
    rfsim1a.set_rssi(mobiles=3, cells=4, rssi=0)
    
    # increase rssi and check G1-UE status
    for i in range(2,6):
        rssi=i*10
        framelog('STEP %s: Increase cell-1 RF attenuation to %s' %(i,rssi), '*')
        rfsim1a.set_rssi(mobiles=3, cells=1, rssi=rssi)

        framelog('STEP %s.1: Check UE switch to cell-4 TA' %i, '*')
        ta_verify(nodes=sarhmG1, log=False)
    
    # check TA switched
    if not ta_verify(nodes=sarhmG1, ta=ta2, log=False):
        results.append(False)
    
    framelog('STEP %s: Turn off cell-4 RF' %(i+1), '*')
    rfsim1a.set_rssi(mobiles=3, cells=1, rssi=0)
    rfsim1a.set_rssi(mobiles=3, cells=234, rssi=127)
    
    framelog('STEP %s: check UE switch back to cell-1 TA' %(i+1), '*')
    if not utils.poll(ta_verify, nodes=sarhmG1, ta=ta1, log=False):
        results.append(False)

    return [ppf(results)]

# cmuIfFailover function
def cmuIfFailover():
    results=list()
    ixia=_tbd.ixplte
    cmu_mate=_tbd.cmu_mate
    cmu_master=_tbd.cmu_master

    framelog('STEP 1: start ixia traffic')
    ixia.start_traffic()
    ixia.set_stats()

    framelog('STEP 2: CMU interface-1 failover')
    cmu_master.intf1.shutdown()

    framelog('STEP 3: stop traffic and check loss% (failover)')
    ixia.stop_traffic(btime=120)
    results += ixia.check_losspct()

    framelog('STEP 4: Start traffic and CMU interface-1 failback')
    ixia.start_traffic()
    cmu_master.intf1.noshutdown()

    framelog('STEP 5: stop traffic and check loss% (failback)')
    ixia.stop_traffic(btime=120)
    results += ixia.check_losspct()

    return [ppf(results)]

# cmuSvrFailover function
def cmuSvrFailover():
    results=list()
    boot=True
    ixia=_tbd.ixplte
    cmu_mate=_tbd.cmu_mate
    cmu_master=_tbd.cmu_master

    step=1
    for cmu in [cmu_master, cmu_mate]: 
        framelog('STEP %s: start ixia traffic' %step)
        ixia.start_traffic()
        ixia.set_stats()

        framelog('STEP %d: %s failover' %(step,cmu.name))
        if not cmu_master.reboot():
            boot=False; results.append(False)

        framelog('STEP %d: stop traffic and check loss%')
        ixia.stop_traffic(btime=120)
        results += ixia.check_losspct()

        if boot:
            framelog('STEP %d: Wait till %s comes back' %(step,cmu.name))
            utils.poll(cmu_master.connect, timeout=300, intv=20)

    return [ppf(results)]

# vsrfailover function
def vsrfailover(tc=1):
    results=list()
    ixia=_tbd.ixplte
    vsri1=[_tbd.vSRi01]
    vsri1n2=[_tbd.vSRi01, _tbd.vSRi02]
    vsra1=[_tbd.vSRa01]
    vsra1n2=[_tbd.vSRa01, _tbd.vSRa02]
    core1=[_tbd.SRa8_01]
    core1n2=[_tbd.SRa8_01, _tbd.SRa8_01]

    rtrs=vsri1
    losspct=2
    # for various test cases
    if tc == 2: rtrs=vsri1n2; losspct=5
    elif tc == 4: rtrs=core1
    elif tc == 5: rtrs=core1n2

    framelog('STEP 0: shutdown core1&2 ports')
    for sr in core1n2:
        sr.port1.shutdown()
        sr.port2.shutdown()

    framelog('STEP 1: start ixia traffic')
    ixia.start_traffic(atime=30)
    ixia.set_stats()

    framelog('STEP 2: router reboot (failover)')
    for rtr in rtrs:
        mylog.info('%s reboot' %rtr.name)
        rtr.reboot()

    framelog('STEP 3: stop traffic and check loss%')
    ixia.stop_traffic(btime=120)
    results += ixia.check_losspct(losspct)

    framelog('STEP 4: re-connect routers')
    for rtr in rtrs:
        mylog.info('%s re-connect' %rtr.name)
        utils.poll(rtr.connect,timeout=60,intv=10)

    return [ppf(results)]

###############################################################################
# main function
###############################################################################
# _tbd object keeps all testbed data
_tbd=None

def main(testsuite_name='ott_plte',
    testcase_name='sanity1', 
    testbed_file='ott_plte.yaml'):

    # initialize testbed data
    global _tbd
    #if not _tbd: _tbd=node.Testbed(testbed_file)
    if not _tbd: _tbd=node.Testbed(testbed_file, use_ixia=False)

    # run test case
    if testcase_name == 'sanity1':
        return sanity1()
    elif testcase_name == 'cmuIfFailover':
        return cmuIfFailover()
    elif testcase_name == 'cmuSvrFailover':
        if today == 'Saturday': return cmuSvrFailover()
        else: return ['SKIPPED']
    elif testcase_name == 'headEndFailover_1':
        return vsrfailover(tc=1)
    elif testcase_name == 'dataCenter01_headEndFailover':
        return vsrfailover(tc=2)
    elif testcase_name == 'aggregationFailover_1':
        return vsrfailover(tc=4)
    elif testcase_name == 'aggregationFailover_1n2':
        return vsrfailover(tc=5)
    elif testcase_name == 'mobility_test':
        return mobility_test()
    else:
        mylog.error('testcase %s NOT implemented yet!' % testcase_name)


##############################################################################
# run this file at command line
##############################################################################
if (__name__ == '__main__'):
    tcname='sanity1'; # default test
    tcprmd=dict()

    # Get command 1st argument
    if len(sys.argv)>1: tcname=sys.argv[1]

    # make log-dir if not exists
    runsuite=os.path.basename(sys.argv[0]).split('.')[0]
    logdir=os.path.join('/var/www/html/rrlogs',runsuite)
    if not os.path.exists(logdir): os.makedirs(logdir)

    # make log file as timestamps.log
    logfile=datetime.now().strftime("%g%b%d_%H%M%S_%f.log")
    logfile=os.path.join(logdir,logfile)

    # configure logging file, level and format
    logging.basicConfig(filename=logfile,level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)s %(message)s')

    # invoke function main
    mylog.info('Testbed file: %s' % runsuite)
    mylog.info("Start case: %s" % tcname)

    tcprmd['testcase_name']=tcname
    tcret=main(**tcprmd)
    mylog.info("End case: %s, %s" % (tcname,tcret[0]))

    # save test results for log2html
    resultd=OrderedDict()
    resultd[tcname]=tcret

    # dump resultd in logfile for log2html to further process  
    mylog.info('JSON result: %s' % json.dumps(resultd))

    # convert raw log to html
    utils.log2html(logfile)

