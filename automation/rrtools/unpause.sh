#t/bin/bash
# remove directory "testbed_pause" on host atims1
### remove directory "testbed_pause" on host .249
if [ ! "$1" ]; then
    echo "usage: unpause.sh <testbed_name>"; exit
fi

TESTBED=$1
CMDPATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source $CMDPATH/utils.sh
rmdir $TBPAUSE
#ssh autorr@135.228.0.249 "rmdir $TBPAUSE"
echo "testbed <$1> UN-PAUSED!"
