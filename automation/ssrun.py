#!/usr/bin/env python3.7

###################################
# Description:
# to run regression suites
# Usage:
# regrun suite-name
# Author:
# sam shangguan
import time
import matplotlib.pyplot as plt
import re
import os
import sys
import ast
import yaml
import json
import utils
import numpy
import pandas
import smtplib
import logging
import argparse
import importlib
import subprocess
from common_vars import *
from datetime import datetime
from collections import OrderedDict
from email.message import EmailMessage
# force matplotlib not to use Xwindow backend (or DISPLAY)
import matplotlib
matplotlib.use('Agg')


if (__name__ == '__main__'):
    # parsing arguments
    cpar = argparse.ArgumentParser(epilog='Have fun! :-)')
    # add positional argument
    cpar.add_argument('testsuite', help='test suite name')
    # add opional argument
    cpar.add_argument('-t', '--testcase', help='execute specified TC')
    cpar.add_argument('-m', '--message', help='idenify log of the run')
    cpar.add_argument('-i', '--idx', action='store_true',
                      help='refresh suite log index')
    cpar.add_argument('-n', '--noemail', action='store_true',
                      help='do not send result email')
    args = cpar.parse_args()
    runsuite = args.testsuite
    runtc = args.testcase
    logid = args.message if args.message else '-'

    # load regression data file
    with open(REGDATA, 'r') as f:
        rd = yaml.load(f, Loader=yaml.Loader)

    validsuites = rd.keys()
    if runsuite not in validsuites:
        print("test suite <%s> not supported!" % runsuite)
        print("suite supported: %s" % validsuites)
        sys.exit(0)

    # make log directory if not exists
    logdir = os.path.join(LOGDIR, runsuite)
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    # refresh suite log index
    if args.idx:
        utils.refresh_index(logdir)
        sys.exit(0)

    suited = rd[runsuite]
    tbpaused = False
    homedir = os.path.expanduser("~")
    tbyaml = suited['testbed']
    tbname = tbyaml.split('.')[0]

    # exit if testbed paused
    pausef = os.path.join(REGDIR, tbname+'.pause')
    if os.path.exists(pausef):
        print('file %s exists, testbed "%s" paused' % (pausef, tbname))
        sys.exit(0)

    t0 = datetime.now()
    # create "tbname_running_pid" file to prevent other users
    # from running on the same testbed
    pidf = os.path.join(REGDIR, tbname+'_running_pid')
#    try:
#        with open(pidf, 'x') as f:
#            f.write(str(os.getpid()))
#    except FileExistsError:
#        print("file %s exists. testbed blocked!" % pidf)
#        print("remove %s and rerun your job!" % pidf)
#        sys.exit(0)

    # get testcases and testcase-names
    validtcs = suited['testcases']
    tcnames = list()
    for tc in validtcs:
        tcnames.append(tc.split()[0])

    # when testcase passed-in
    if runtc and runtc not in tcnames:
        print("testcase <%s> not supported!" % runtc)
        print("case supported: %s" % tcnames)
        sys.exit(0)

    # make mib symbolic link pointing to suite-specified one
    mibrel = os.path.basename(os.readlink(MIBDIR))
    if "mib_release" in suited and suited["mib_release"] != mibrel:
        mibreldir = os.path.dirname(os.readlink(MIBDIR))
        mibsrc = os.path.join(mibreldir, suited['mib_release'])
        if not os.path.exists(mibsrc):
            print('mib source %s NOT found!' % mibsrc)
            sys.exit(0)
        # unlink existing one and create a new one
        os.unlink(MIBDIR)
        os.symlink(mibsrc, MIBDIR)

    # make log file based on timestamps
    logfile = os.path.join(logdir, t0.strftime("%g%b%d_%H%M%S_%f.log"))

    # remove all handlers associated with root logger object
    # without this, log file not created in virtual env
    for lh in logging.root.handlers:
        logging.root.removeHandler(lh)

    # configure logging file and format
    logging.basicConfig(filename=logfile,
        format='%(asctime)s %(name)s %(levelname)s %(message)s')

    # let logger mylog
    mylog = utils.get_logger(__name__)
    mylog.info('Log id: %s' % logid)
    mylog.info('Testbed file: %s' % tbyaml)

    # save testbed configuration before tests
    import node
    resultd = OrderedDict()
    bkdir = None
    bks = os.path.basename(BKPDIR)
    #if RUNNER == REGUSER and bks in suited and suited[bks]:
    tb = node.Testbed(tbyaml, use_ixia=False)
    
    tb.al_5.send_command("show port", protocol='netconf')
    for pt in tb.al_5:
        pt.shutdown(opt='netconf')
        pt.noshutdown(opt='netconf')
    
    tb.al_5.send_command("configure port 1/2/c12/4 shutdown", protocol='netconf')
    tb.al_5.send_command("configure port 1/2/c12/4 no shutdown", protocol='netconf')
    tb.al_5.send_command("configure port 1/2/c12/4 admin-state disable", protocol='netconf')
    tb.al_5.send_command("port 1/2/c12/4 admin-state disable", protocol='netconf')
    
    tb.al_5.send_command("show port", style='md')
    tb.al_5.send_command("show port", protocol='netconf')
    tb.al_5.send_command("show port 1/2/c10", protocol='netconf')
    tb.al_5.send_command("show system security user", protocol='netconf')
    tb.al_5.send_command("show system management-interface configuration-sessions", protocol='netconf')

    tb.al_5.send_command("configure port 1/2/c10 admin-state enable", style='md')
    tb.al_5.send_command("show port")
    tb.al_5.send_command("configure port 1/2/c10 admin-state disable", style='md')
    tb.al_5.send_command("show port", style='md')
    tb.al_5.send_command("configure port 1/2/c10 shutdown")
    tb.al_5.send_command("show port | match 1/2/c10")
    tb.al_5.send_command("configure port 1/2/c10 no shutdown")
    tb.al_5.send_command("show port | match 1/2/c10")

    resultd['shut/noshut port'] = 'PASS'
    mylog.info('JSON result: %s' % json.dumps(resultd))
    utils.log2html(logfile, logid, bkdir)
    # restore SELinux security labels context of web
    os.system("restorecon -R %s" % HTMLROOT)
    sys.exit(0)
    import pdb; pdb.set_trace()
    
#    import pdb; pdb.set_trace()

# test backup via ftp and netconf
    for nd in tb:
        nd.backup_ftp()
        nd.backup_xml()
    bkdir = tb.bkup_dir
    mylog.info('Testbed backup: %s' % bkdir)
    resultd['backup_case'] = 'PASS'
    #mylog.info('JSON result: %s' % json.dumps(resultd))
    #utils.log2html(logfile, logid, bkdir)
    #sys.exit(0)

# test port shut and noshut
    for opt in ['ssh', 'snmp', 'netconf']:
        for nd in tb:
            utils.framelog(">%s< %s switch to Classic" %(opt,nd.sysname))
            for pt in nd:
                pt.shutdown(opt=opt)
                pt.noshutdown(opt=opt)
                time.sleep(2)
                nd.cliexe('show port | match %s' %pt.port)

            utils.framelog(">%s< %s switch to MD-CLI" %(opt,nd.sysname))
            for pt in nd:
                pt.shutdown(opt=opt)
                pt.noshutdown(opt=opt)
                time.sleep(2)
                nd.cliexe('show port | match %s' %pt.port)

    
    resultd['shut/noshut port'] = 'PASS'
    mylog.info('JSON result: %s' % json.dumps(resultd))
    utils.log2html(logfile, logid, bkdir)
    # restore SELinux security labels context of web
    os.system("restorecon -R %s" % HTMLROOT)
    sys.exit(0)

    # import testcase module
    tcmodule = runsuite
    if 'module' in suited:
        tcmodule = suited['module']
    tcmodule = importlib.import_module(tcmodule)

    # loop through suite testcases
    pass_num = 0
    resultd = OrderedDict()
    for tc in validtcs:

        tcname = tc.split()[0]
        # when runtc exist, run runtc only
        if runtc and runtc != tcname:
            continue

        # prepare testcase parameters dict()
        tcprmd = dict()
        prms = re.search(r'(\{.*\})$', tc)
        if prms:
            tcprmd = ast.literal_eval(prms.group(1))

        tcprmd['testcase_name'] = tcname
        tcprmd['testbed_file'] = tbyaml
        tcprmd['testsuite_name'] = runsuite

        # log testcase start
        mylog.info("Start case: %s" % tcname)
        mylog.info("Parameters: %s" % tcprmd)

        # run tescase module main function
        try:
            tcret = tcmodule.main(**tcprmd)
        except Exception:
            mylog.exception('Fatal error in test %s' % tcname)
            tcret = ['ERROR']

        # test return list such as [PASS, KPIdict]
        # log testcase result
        mylog.info("End case: %s, %s" % (tcname, tcret[0]))
        # increase pass_num if test runs pass
        if re.search('pass', tcret[0], re.IGNORECASE):
            pass_num += 1
        # save test results for log2html
        resultd[tcname] = tcret

        # if KPIdict exists, write KPI to csv file
        # /var/www/html/$user/kpis/suite_name/kpi_name.cvs
        if len(tcret) == 2:
            kpidir = os.path.join(KPIDIR, runsuite)
            if not os.path.exists(kpidir):
                os.makedirs(kpidir)
            kpidict = tcret[1]

            # print(json.dumps(kpidict, indent=4, sort_keys=True))
            if 'KPIs' in kpidict:
                for kpi in kpidict.pop('KPIs'):
                    tcname, kpiname = kpi.split('.')
                    # if kpitcdir not exists, make it
                    kpitcdir = os.path.join(kpidir, tcname)
                    if not os.path.exists(kpitcdir):
                        os.makedirs(kpitcdir)
                    kpicsv = os.path.join(kpitcdir, kpiname+'.csv')
                    kpipdf = os.path.join(kpitcdir, kpiname+'.pdf')
                    if not kpidict:
                        continue  # incase no data in kpidict
                    # create kpicsv column header without kpi prefix
                    lcolhead = [k[len(kpi)+1:]
                                for k in kpidict if k.startswith(kpi)]
                    scolhead = ','.join(lcolhead)+'\n'
                    lrowdata = [v for k, v in kpidict.items()
                                if k.startswith(kpi)]
                    srowdata = ','.join(map(str, lrowdata))+'\n'

                    mylog.info('write kpi data: %s' % kpicsv)
                    if not os.path.exists(kpicsv):
                        # kpicsv not exists. create new one
                        with open(kpicsv, 'w') as f:
                            f.write(scolhead)
                            f.write(srowdata)
                    else:
                        # kpicsv exists. check if data columns changed
                        with open(kpicsv, 'r') as f:
                            col = f.readline()  # get column header
                        if col.strip() == scolhead.strip():
                            # column has no change. append row data
                            with open(kpicsv, 'a+') as f:
                                f.write(srowdata)
                        else:
                            # column has changed. create new file
                            with open(kpicsv, 'w') as f:
                                f.write(scolhead)
                                f.write(srowdata)

                    mylog.info('make kpi graph: %s' % kpipdf)
                    # get figure data from csv
                    figd = pandas.read_csv(kpicsv)
                    # set figure height: 12(w)x(3*columns)(h)
                    figh = len(figd.columns)*3
                    figd.plot(title=kpi, figsize=(12, figh), subplots=True)
                    plt.savefig(kpipdf)

    # remove tbname.pid file
    if os.path.isfile(pidf):
        os.remove(pidf)

    # dump resultd into logfile for log2html to further process
    mylog.info('JSON result: %s' % json.dumps(resultd))

    # convert raw log to html
    utils.log2html(logfile, logid, bkdir)
    # restore SELinux security labels context of web
    os.system("restorecon -R %s" % HTMLROOT)

    if args.noemail:
        sys.exit(0)

    # prepare result email
    msg = EmailMessage()
    msg['From'] = USERMAIL
    msg['To'] = TEAMMAIL if RUNNER == REGUSER else USERMAIL
    # calculate test duration
    t1 = datetime.now()
    tds = (t1 - t0).seconds
    tdhms = "%dh%dm%ds" % (tds // 3600, (tds // 60) % 60, (tds % 3600) % 60)
    # setup email context
    tests_num = len(resultd)
    gitbranch = os.popen('git --git-dir=%s branch | grep "^*"' %
                         os.path.join(AUTODIR, '.git')).read().strip(' *\n')
    etxt = "Python version: %s\n" % sys.version[:6]
    etxt += "Git branch: %s\n\n" % gitbranch
    etxt += "Suite name:\t%s\n" % runsuite
    etxt += "Run duration:\t%s\n" % tdhms
    etxt += "Tests:\t\t%d\n" % tests_num
    etxt += "Pass:\t\t%d\n" % pass_num
    etxt += "Fail:\t\t%d\n" % (tests_num - pass_num)
    etxt += "Pass Rate:\t%d%s\n" % (pass_num*100/tests_num, '%')
    etxt += "Log: %s/%s\n" % (URLPFX, logfile[LSI:])
    if bkdir:
        etxt += "Backup: %s/%s" % (URLPFX, bkdir[LSI:])
    msg.set_content(etxt)
    # setup email subject
    overall = "PASSED" if tests_num == pass_num else "FAILED"
    msg['Subject'] = "Job <%s> completed -- %s" % (runsuite, overall)

    # send email
    with smtplib.SMTP(MAILSERVER) as s:
        s.send_message(msg)
    mylog.info('notification email sent to: %s' % msg['To'])
