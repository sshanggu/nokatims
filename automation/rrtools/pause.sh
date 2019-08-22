#!/bin/bash
# create directory "testbed_pause" on host atims1
### create directory "testbed_pause" on host .249
if [ ! "$1" ]; then
    echo "usage: pause.sh <testbed_name>"; exit
fi

TESTBED=$1
CMDPATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source $CMDPATH/utils.sh
mkdir -p $TBPAUSE
#ssh autorr@135.228.0.249 "mkdir -p $TBPAUSE"
echo "testbed <$TESTBED> PAUSED!"
