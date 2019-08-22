#!/bin/bash
##############################################################
# This script pops a task (test suite) from testbed.queue,
# and invoke the task run if testbed is free.
# The script runs by crontab every 2 minutes.
#
# 2018/05/08 sam_shangguan
##############################################################
CMDPATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# default TESTBED="ott_plte", or 1st argument
TESTBED=${1-"ott_plte"}

# source utils.sh
source $CMDPATH/utils.sh

# exit if TBPAUSE exists
if [ -d $TBPAUSE ]; then
    TECHO "testbed '$TESTBED' paused. exit!"; exit
fi

# exit if TBRUNID exist and non-empty
if [ -e $TBRUNID -a -s $TBRUNID ]; then
    ECMD "ps -p $(cat $TBRUNID) -wwf"
    TECHO "testbed '$TESTBED' busy. exit!"; exit
fi

# exit if TBQUEUE not exist or empty
if [ ! -e $TBQUEUE -o ! -s $TBQUEUE ]; then
    TECHO "$TBQUEUE empty or not exist. exit!"; exit
fi

# smutex excludes other scheduler runs
# exit if lock fails. try next time by crontab
if ! LOCK $SMUTEX; then exit; fi

# qmutex excludes submit access testbed.queue
# if lock fails, unlock scheduler and exit.  
if ! LOCK $QMUTEX; then
    UNLOCK $SMUTEX; exit
fi

# at this point, both smutex and qmutex locked
# now pop top job from testbed.queue
ECMD "read -r TASK < $TBQUEUE"
ECMD "sed -i -e '1d' $TBQUEUE"
# unlock the queue
UNLOCK $QMUTEX

# invoke regression run
# send output to RUNLOG if crontab run
TECHO "invokes $CMDPATH/../regrun.py $TASK"
if [ "$CRONJOB" ]; then
    RUNLOG=$HOME/$TESTBED.$TASK.cron.log
    $CMDPATH/../regrun.py $TASK &> $RUNLOG
    UNLOCK $SMUTEX &>> $RUNLOG
else
    $CMDPATH/../regrun.py $TASK
    UNLOCK $SMUTEX
fi
