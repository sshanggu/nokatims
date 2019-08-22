#!/usr/bin/python

import node
import service
import utils
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

###################################
##
## Example test
##


# Create a log file
log_file=logging.getLogger(__name__)

# Configure log file to output to stdout too
log_file.addHandler(logging.StreamHandler(sys.stdout))

# Create a dictionary for the testbed data
# This dictionary is populated by reading in the 
# testbed's yaml file

testbed_data=attrdict.AttrDict()


def testbed_init(testbed_file):

    log_file.info('Initalize the testbed')
    global testbed_data
    if testbed_data:
        log_file.info('Testbed has already been initialized')
        return

    # Read in the testbed yaml file into yaml_data dictionary
    with open(testbed_file, 'r') as f: 
        yaml_data=yaml.load(f)

    testbed_data.name = yaml_data['topology']['name']

    # Read through the yaml_data dictionary and build CPM and port objects
    # Create a dictionary of testbed node/CPM objects to speed up node/port checking
    # later on 
    
    # Create ixia object
    log_file.info('Build Ixia')
    testbed_data.ixia_100g    = ixia.IxNetx(**yaml_data['ixia'])

    log_file.info('Build objects for nodes, IOMs, MDAs, ports and services')
    for tb_node in yaml_data['nodes'].keys() :
        cpm_obj=node.Node(**yaml_data['nodes'][tb_node])
        testbed_data[tb_node] = cpm_obj


def main(testcase='',testsuite='',testbed_file='example_test.yaml'):

    # Initialize the testbed
    testbed_init(testbed_file)
    pdb.set_trace()

if (__name__ == '__main__'):
    main()
