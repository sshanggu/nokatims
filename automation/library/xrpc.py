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
import utils
from six import StringIO
from io import BytesIO
from lxml import etree as ET
from lxml.builder import E

mylog = utils.get_logger(__name__)

xmlns = 'urn:alcatel-lucent.com:sros:ns:yang:conf-r13'


def x2h(xb):
    # convert xml-bytes to html-str for browser to display
    if type(xb) is not bytes:
        xb = xb.encode('utf-8')
    hs = ET.tostring(ET.fromstring(xb),
                     pretty_print=True).decode('utf-8')
    hs = re.sub(r'<', '&lt', hs)
    hs = re.sub(r'>', '&gt', hs)
    return hs


def pset(port, **kwargs):
    # initial elements
    xc = E('configure', E('port', E('port-id', port)), xmlns=xmlns)
    xcp = xc.xpath('//configure/port')[0]
    # add passed-in elements
    for tag, text in kwargs.items():
        if tag == 'shutdown':
            ET.SubElement(xcp, tag).text = text
            continue
        if tag == 'description':
            xcpt = ET.SubElement(xcp, tag)
            ET.SubElement(xcpt, 'long-description-string').text = text
    return xc
