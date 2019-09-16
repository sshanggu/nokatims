#!/usr/bin/python
#
###############################################################################
#
# Created by: Sam Shangguan
# Last Update: 2019-12-09
# Description: generate xml rpc for netconf
#
###############################################################################

import os
import re
import sys
import glob
import time
import types
import logging
from six import StringIO
from io import BytesIO
from lxml import etree

mylog = logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler(sys.stdout))

xmlns = 'urn:alcatel-lucent.com:sros:ns:yang:conf-r13'


def x2h(xb):
    # convert xml-bytes to html-str for browser to display
    if type(xb) is not bytes:
        xb = xb.encode('utf-8')
    hs = etree.tostring(etree.fromstring(xb),
                        pretty_print=True).decode('utf-8')
    hs = re.sub(r'<', '&lt', hs)
    hs = re.sub(r'>', '&gt', hs)
    return hs


def pset(port, **kwargs):
    # initial elements
    xc = etree.Element('configure', xmlns=xmlns)
    xcp = etree.SubElement(xc, 'port')
    xcpi = etree.SubElement(xcp, 'port-id')
    xcpi.text = port
    # add passed-in elements
    for tag, text in kwargs.items():
        if tag == 'shutdown':
            xcpt = etree.SubElement(xcp, tag)
            xcpt.text = text
            continue
        if tag == 'description':
            xcpt = etree.SubElement(xcp, tag)
            xcpt1 = etree.SubElement(xcpt, 'long-description-string')
            xcpt1.text = text
            continue
    return xc
