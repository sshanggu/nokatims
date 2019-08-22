# define commonly used functions
#####################################################################
# echo command and execute it
function ECMD {
    TECHO "$*"
    eval $*
}

# echo with timestamp
function TECHO {
    echo $(date +"%F %H:%M:%S.%3N") $1
}

# remove mutex directory
function UNLOCK {
    if $(rmdir $1); then
        TECHO "removed mutex: $1"
    fi
}

# make mutex directory. return true or false
function LOCK {
    if $(mkdir $1); then
        TECHO "created mutex: $1"; true
    else
        false
    fi
}

# define commonly used variables
if [ ! "$TESTBED" ]; then
    echo "variable 'TESTBED' not exist!!!"
fi

#REGDIR=$HOME
REGDIR=/regression
TBPAUSE=$REGDIR/$TESTBED.pause
TBQUEUE=$REGDIR/$TESTBED.queue
TBRUNID=$REGDIR/$TESTBED.pid
QMUTEX=$REGDIR/$TESTBED.queue.mutex
SMUTEX=$REGDIR/$TESTBED.scheduler.mutex
