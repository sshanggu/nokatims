#!/bin/bash
##############################################################
# this script submits regression suite to testbed.queue
# it can be invoked by crontab or by command line
#
# 2018/05/08 sam_shangguan
##############################################################
CMDPATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# default SUITE="ott_plte", or 1st argument
SUITE=${1-"ott_plte"}

# find testbed name related to the suite
RDF=$CMDPATH/../regdata.yaml
TMP=$(egrep -A 4 "^$SUITE:" $RDF | egrep "^ +testbed:")
TMP=${TMP#*testbed: *}; # delete front 'testbed:'
TESTBED=${TMP%.yaml}; # delete back '.yaml'
if [ ! "$TESTBED" ]; then
    echo "invalid '$SUITE' or testbed not defined"; exit
fi

# source utils.sh
source $CMDPATH/utils.sh

# submit suite to testbed.queue
TECHO "submit suite '$SUITE' to queue '$TBQUEUE'"

# if testbed.queue not exist, create one
if [ ! -e $TBQUEUE ]; then touch $TBQUEUE; fi

# loop till testbed.queue locked
while ! LOCK $QMUTEX; do
    ECMD "sleep $(($RANDOM / 4096))";# wait random seconds
done

# append suite into its queue
# unlock the queue
ECMD "echo $SUITE >> $TBQUEUE"
UNLOCK $QMUTEX
