#!/usr/bin/python

###############################################################################
###
# Created by: Allan Phoenix
###
# Last Update: 2017-12-13
###
# Description:
###
# Utility functions:
###
###
# Version control:
###
# v1:
# - Creation.
###
###

import os
import re
import sys
import glob
import time
import node
import json
import shutil
import getpass
import logging
import subprocess
from datetime import datetime
from collections import OrderedDict
from common_vars import *

mylog = logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler(sys.stdout))
TF1 = "%Y-%m-%d %H:%M:%S"


def countdown(t):  # in seconds
    # Use for interactive test scripts
    # places a '.' every second in the terminal window
    # while you are waiting for something to happen
    # Better than dead air :)
    for i in range(t, 0, -1):
        print("."),
        sys.stdout.flush()
        time.sleep(1)
    print("\n")


def ns_to_us(ns):
    """ convert ns to us """
    us = float(ns) / 1000
    return us


def ns_to_ms(ns):
    """ convert ns to ms """
    ms = float(ns) / 1000000
    return ms


def ns_to_s(ns):
    """ convert ns to s """
    s = float(ns) / 1000000000
    return s


def fmtout(s, cmd=None):
    """ clean up router outputs """
    if type(s) is bytes:
        s = s.decode("utf-8")
    tmp = '\n'
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue  # remove empty line
        if cmd and cmd in line:
            continue  # remove cmd line
        if re.search(r'\*?(A|B):', line):
            continue  # remove router prompt line
        if cmd and cmd in line:
            continue  # remove cmd line
        tmp += line+'\n'
    return tmp


def parse_show_port(s):
    """ parse "show port" output, return a dict """
    myd = dict()
    for line in s.splitlines():
        m = re.search(r'^(\d/\d/\d) +(\S+) +(\S+) +(\S+) .*$', line)
        if m:
            myd[m.group(1)] = dict()
            myd[m.group(1)]['admin'] = m.group(2)
            myd[m.group(1)]['link'] = m.group(3)
            myd[m.group(1)]['state'] = m.group(4)
    return myd


def parse_show_port_detail(s):
    """ parse "show port" output, return a dict """
    # set all default to None
    myd = dict()
    for ky in ['admin', 'oper', 'network_status', 'radio_mode', 'band',
               'channel', 'rssi', 'rsrp', 'tracking_area', 'cell_identity',
               'pdn_state', 'ip_addr']:
        myd[ky] = None

    for line in s.splitlines():
        m = re.search(r'^Admin State +: (\S+) +Oper State +: (\S+)$', line)
        if m:
            myd['admin'] = m.group(1)
            myd['oper'] = m.group(2)
            continue
        m = re.search(
            r'^Network Status +: (\S+) +Radio Mode +: *(\S+|\s*)$', line)
        if m:
            myd['network_status'] = m.group(1)
            myd['radio_mode'] = m.group(2)
            continue
        m = re.search(r'^Band +: *(\S+|\s*) *Channel +: *(\S+|\s*)$', line)
        if m:
            myd['band'] = m.group(1)
            myd['channel'] = m.group(2)
            continue
        m = re.search(
            r'^RSSI +: *(?:<=)? *(-\d+) dBm +RSRP +: (-\d+) dBm$', line)
        if m:
            myd['rssi'] = m.group(1)
            myd['rsrp'] = m.group(2)
            continue
        m = re.search(
            r'^Tracking Area Code: *(\S+) +Cell Identity *: *(\S+)$', line)
        if m:
            myd['tracking_area'] = m.group(1)
            myd['cell_identity'] = m.group(2)
            continue
        m = re.search(
            r'^PDN State +: ((not)? *\S+) +IP Address +: (\S+)$', line)
        if m:
            myd['pdn_state'] = m.group(1)
            myd['ip_addr'] = m.group(3)
    return myd


def td(f0):
    """ table data (td) decorator """
    def f1(*args):
        return '  <td>{0}</td>\n'.format(f0(*args))
    return f1

# table data with color, Green for PASS, Red for FAIL
@ td
def tdmsg(msg):
    if msg == 'PASS':
        return '<font color="Green">{0}</font>'.format(msg)
    elif msg == 'FAIL':
        return '<font color="Red">{0}</font>'.format(msg)
    else:
        return msg

# table data pointing to log link
@ td
def tdlog(href, name='log'):
    return '<a href="{0}">{1}</a>'.format(href, name)


def tbrow(msg):
    """ make table row """
    return ' <tr>\n{0} </tr>\n'.format(msg)


def tagpre(msg):
    """ wrap pre tag """
    return '<pre>\n{0}</pre>\n'.format(msg)


def tagcolor(msg, color='Blue', size=3):
    """ wrap font color tag """
    if re.search(r'PASS', msg):
        color = 'Green'
    elif re.search(r'FAIL', msg):
        color = 'Red'
    elif re.search(r'PARTIAL', msg):
        color = 'DarkOrange'
    return '<font color={} size={}>{}</font>\n'.format(color, size, msg)


def u2a(data):
    if isinstance(data, dict):
        return OrderedDict((u2a(x), u2a(y)) for x, y in data.items())
    elif isinstance(data, list):
        return [u2a(x) for x in data]
    elif isinstance(data, str):
        return str(data)
    else:
        return data


def log2html(logfile, message, bkdir=None):
    """ convert raw log to html """
    # read logfile line by line
    tbfile = None
    resultd = None
    taglog = str()
    with open(logfile) as f:
        for line in f:
            # replace '<' with '&lt', '>' with '&gt'
            line = re.sub(r'<', '&lt', line)
            line = re.sub(r'>', '&gt', line)
            # color other special lines
            if re.search(r' Testbed file: (\S+)$', line):
                tbfile = re.search(r' Testbed file: (\S+)$', line).group(1)
            elif re.search(r' Start case: (\S+)$', line):
                name = re.search(r' Start case: (\S+)$', line).group(1)
                line = tagcolor('<a name="%s">%s</a>' %
                                (name, line.strip('\n')), size=5)
            elif re.search(r' End case:', line):
                line = tagcolor(line.strip('\n'), 'Brown')
            elif re.search(r' ERROR ', line):
                line = tagcolor(line.strip('\n'), 'Red')
            elif re.search(r'JSON result: *({.*})', line):
                # convert json dump string into ordered dictionary
                jdumps = re.search(r'JSON result: *({.*})', line).group(1)
                decoder = json.JSONDecoder(object_pairs_hook=OrderedDict)
                resultd = decoder.decode(jdumps)
                line = '<!-- %s -->\n' % jdumps
            taglog += line
    taglog = tagpre(taglog)

    # return when resultd not exist
    if not resultd:
        mylog.error("JSON result string NOT exist!")
        return

    # counting
    tcpass = 0
    passrate = 0
    overall = 'PASS'
    tctotal = len(resultd)
    for t, r in resultd.items():
        if r[0] == 'PASS':
            tcpass += 1
    tcfail = tctotal-tcpass
    if tctotal == 0 or tcfail != 0:
        overall = 'FAIL'
    if tctotal != 0:
        passrate = "{:4.1f}".format(tcpass*100.0/tctotal)

    # prepare log header
    hdr = str()
    hdr += tagcolor('Overall result: %s' % overall)
    hdr += tagcolor('Pass rate: %s%%' % passrate)
    hdr += tagcolor('Case total: %d' % tctotal)
    hdr += tagcolor('Case passed: %d' % tcpass)
    hdr += tagcolor('Case failed: %d' % tcfail)
    for tc, tr in resultd.items():
        tr = u2a(tr)  # convert unicode to ascii
        hdr += tagcolor('<a href="#%s">%s</a> -- %s' % (tc, tc, tr))
    hdr = tagpre(hdr)

    # write html log
    title = '\n<title>%s</title>\n' % ('/'.join(logfile.split('/')[-2:]))
    taglog = '<body>\n{0}</body>\n'.format(hdr+taglog)
    taglog = '<!DOCTYPE html>\n<html>{0}{1}</html>'.format(title, taglog)
    with open(logfile, 'w') as f:
        f.write(taglog)

    ################################################################
    # update test suite summary index entry
    suitename = os.path.basename(os.path.dirname(logfile))
    hrflog = os.path.join(URLPFX, logfile[LSI:])
    if bkdir:
        bklog = os.path.join(URLPFX, bkdir[LSI:])
    logmtime = datetime.fromtimestamp(
        os.path.getmtime(logfile)).strftime(TF1)
    entry = tdmsg(logmtime)
    entry += tdmsg(message)
    entry += tdmsg(tbfile)
    entry += tdmsg(suitename)
    entry += tdmsg(overall)
    entry += tdmsg(passrate+'%')
    entry += tdmsg(tctotal)
    entry += tdmsg(tcpass)
    entry += tdmsg(tcfail)
    entry += tdlog(hrflog)
    entry += tdlog(bklog, 'backup') if bkdir else tdmsg('-')
    entry = tbrow(entry)

    # open suite index file and add table entry
    tsidxf = os.path.join(os.path.dirname(logfile), 'index.html')
    if not os.path.exists(tsidxf):
        shutil.copy2(os.path.join(AUTODIR, 'ts_index.html'), tsidxf)
    # fixed index.html title
    sedcmd = ['sed', '-i', 's/>index</>%s</' % suitename, tsidxf]
    subprocess.call(sedcmd)

    newtable = str()
    addentry = True
    # index file read line by line
    with open(tsidxf) as f:
        for line in f:
            if addentry and re.search(r'</tr>$', line):
                # add new entry as 1st row
                line = line+entry
                addentry = False
            newtable += line

    # write new table
    with open(tsidxf, 'w') as f:
        f.write(newtable)

    ################################################################
    # update regression index file
    rridxf = os.path.join(LOGHOME, 'index.html')
    if not os.path.exists(rridxf):
        shutil.copy2(os.path.join(AUTODIR, 'rr_index.html'), rridxf)

    # index file read as a string and split into list
    with open(rridxf) as f:
        rrtl = f.read().splitlines()

    # search line <td>suitename</td>
    insertI = None
    for idx, line in enumerate(rrtl):
        if '>%s<' % suitename in line:
            insertI = idx
            break

    if insertI:
        # suite entry exist, update its time and result
        rrtl[insertI+1] = tdmsg(logmtime).strip('\n')
        rrtl[insertI+2] = tdmsg(overall).strip('\n')
    else:
        # suite entry not exist, create one
        hrfkpi = os.path.join(URLPFX, 'kpis', suitename)
        entry = tdmsg(suitename)
        entry += tdmsg(logmtime)
        entry += tdmsg(overall)
        entry += tdlog(os.path.dirname(hrflog), 'all results')
        entry += tdlog(hrfkpi, 'all kpis')
        entry = tbrow(entry)
        # locate table head end
        insertI = rrtl.index(' </tr>')+1
        # insert new entry as 1st table row
        rrtl = rrtl[0:insertI]+entry.splitlines()+rrtl[insertI:]

    # write updated table
    with open(rridxf, 'w') as f:
        f.write('\n'.join(rrtl))


def poll(func, timeout=60, intv=5, **args):
    """ func must return True or False """
    fn = func.__name__
    t1 = int(time.time())+timeout
    result = False
    while int(time.time()) < t1:
        if func(**args):
            result = True
            break
        mylog.info("%s not success. retry after %ss" % (fn, intv))
        time.sleep(intv)
    if result:
        mylog.info("%s poll success within %ss." % (fn, timeout))
    else:
        mylog.error("%s poll Failed within %ss!" % (fn, timeout))
    return result


def polldeco(func):
    """ make function pollable """
    def plf(*args, **kwargs):
        to = kwargs.get('timeout', 60)
        wt = kwargs.get('interval', 5)
        ps = 'FAILED'  # init poll state
        t1 = int(time.time())+to
        fn = func.__name__
        while int(time.time()) < t1:
            if func(*args, **kwargs):
                ps = 'PASSED'
                break
            mylog.info("%s not success. Wait %ss & retry" % (fn, wt))
            time.sleep(wt)
        # check state after loop
        mylog.info("%s %s within %ss" % (fn, ps, to))
        return True if ps == 'PASSED' else False
    # return plf
    return plf


def parse_show_bgp(s):
    """ parse "show router bgp info" output, return a dict """
    myd = dict()
    for line in s.splitlines():
        if not line.strip():
            continue  # skip empty line
        m = re.search(
            r'BGP Router ID: *(\S+) +AS: *(\S+) +Local AS: *(\S+)', line)
        if m:
            myd['routerId'] = m.group(1)
            myd['as'] = m.group(2)
            myd['localAs'] = m.group(3)
            continue
        m = re.search(
            r'BGP Admin State *: (\S+) +BGP Oper State *: (\S+)', line)
        if m:
            myd['adminState'] = m.group(1)
            myd['operState'] = m.group(2)
            continue
    return myd


def find_nodes(nd_dict, pattern, attr='name'):
    return [x for x in nd_dict.values()
            if hasattr(x, attr) and getattr(x, attr)
            and re.search(pattern, getattr(x, attr))]


def framelog(m, c='-', n=70):
    """ log message with a frame """
    mylog.info(c*(n))
    for l in m.splitlines():
        mylog.info(' ' + l.strip())
    mylog.info(c*(n))


def save_tb_config(tbfile):
    """ save testbed nodes configuration """
    tb = node.Testbed(tbfile, use_ixia=False)
    for _, nd in tb.node_dict.items():
        nd.backup_config()
    return tb.bkup_dir


# re-generate suite log web index file
# /var/www/html/$user/rrlog/$suite/index.html
def refresh_index(logdir):
    logfiles = glob.glob(os.path.join(logdir, '*.log'))
    if not logfiles:
        mylog.info("%s empty!" % logdir)
        return

    tablerows = str()
    logfiles.reverse()  # latest file first
    for f in logfiles:
        # read log lines till "Testbed backup:"
        # but drop any lines after "Testbed file:"
        htmlfile = False
        dropline = False
        count = 0
        sinfo = str()
        with open(f) as g:
            for line in g:
                count += 1
                if not dropline:
                    sinfo += line
                if "DOCTYPE html" in line:
                    htmlfile = True
                if "Testbed file:" in line:
                    dropline = True
                if "Testbed backup:" in line or count > 500:
                    sinfo += line
                    break
        # extract data from log header & build index table row
        tr = tdmsg(
            datetime.fromtimestamp(os.path.getmtime(f)).strftime(TF1))
        rs = re.search(r' Log id: *(.*?)\n', sinfo, re.I)
        tr += tdmsg(rs.group(1) if rs else '-')
        rs = re.search(r' Testbed file: *(\S+)\n', sinfo)
        tr += tdmsg(rs.group(1) if rs else '-')
        tr += tdmsg(os.path.basename(logdir))
        rs = re.search(r'Overall result: *(PASS|FAIL)', sinfo)
        tr += tdmsg(rs.group(1) if rs else 'ERROR')
        rs = re.search(r'Pass rate: *([\d.%]+)', sinfo)
        tr += tdmsg(rs.group(1) if rs else '-')
        rs = re.search(r'Case total: *(\d+)', sinfo)
        tr += tdmsg(rs.group(1) if rs else '-')
        rs = re.search(r'Case passed: *(\d+)', sinfo)
        tr += tdmsg(rs.group(1) if rs else '-')
        rs = re.search(r'Case failed: *(\d+)', sinfo)
        tr += tdmsg(rs.group(1) if rs else '-')
        tr += tdlog(os.path.join(URLPFX, f[LSI:]))
        rs = re.search(r' Testbed backup: *(/\S+)\n', sinfo)
        tr += tdlog(os.path.join(URLPFX, rs.group(1)[LSI:]), 'backup')\
            if rs else tdmsg('-')
        tr = tbrow(tr)
        tablerows += tr
        # in case log not html style, add tags
        if not htmlfile:
            tags = '<!DOCTYPE html>\n<pre>\n{0}</pre>\n'
            with open(f) as g:
                tagf = tags.format(g.read())
            with open(f, 'w') as g:
                g.write(tagf)

    # copy template to /var/www/html/$user/rrlogs/$suite/index.html
    template = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'ts_index.html')
    tsidxf = os.path.join(logdir, 'index.html')
    shutil.copy2(template, tsidxf)
    os.system("restorecon -R %s" % logdir)  # enable web permission
    # read index template & add tablerows
    newtable = str()
    with open(tsidxf) as f:
        for line in f:
            if re.search(r'</tr>$', line):
                line += tablerows
            newtable += line

    # write new table
    with open(tsidxf, 'w') as f:
        f.write(newtable)
    print("%s refreshed!" % tsidxf)


def d2s(d):
    """ return string "key=value, ..." of d (dictionary) """
    kv = list()
    for k, v in d.items():
        kv.append("%s=%s" % (k, v))
    return ", ".join(kv)
