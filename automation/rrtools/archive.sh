#!/bin/bash
##############################################################
# this script zip  regression suite to testbed.queue
# it can be invoked by crontab or by command
#
# 2018/05/08 sam_shangguan
##############################################################
COMMAND=$(readlink -f $0)
CMDPATH=$(dirname $COMMAND)
CMD=$(basename $COMMAND)
TESTBED="dummy"
source $CMDPATH/utils.sh

HTMLDIR=/var/www/html
# make archives directory if not exist
ARCHDIR=$HTMLDIR/archives
if [ ! -d $ARCHDIR ]; then mkdir $ARCHDIR; fi

# by default, archive logs older than 60 days 
DAYS=60

usage() {
echo -e "
Usage:
    $CMD [-h] [-d\e[4mn\e[0m] [suiteX suiteY ...]
Example:
    $CMD -h           ;# print command help infomation
    $CMD              ;# archive all suites logs older than 60(default) days
    $CMD -d20         ;# archive all suites logs older than 20 days
    $CMD suiteX       ;# archive suiteX logs older than 60(default) days
    $CMD suiteX suiteY;# archive suiteX & suiteY logs older than 60(default) days
    $CMD -d\e[4m10\e[0m suiteX  ;# archive suiteX logs older than 10 days'
"
exit
}

# parse input option and arguments
while getopts "hd:" opt; do
    case $opt in
        d) DAYS=$OPTARG;;
        h|?) usage;;
    esac
done

# shift options away to get arguments
shift $((OPTIND-1))
unset LOGDIRS
if [ "$*" ]; then
    TECHO "archive suite '$*' logs older than $DAYS days"
    for ARG in $*; do
        LOGDIRS="$LOGDIRS $HTMLDIR/rrlogs/$ARG"
    done
else
    TECHO "archive all suites logs older than $DAYS days"
    LOGDIRS=$(ls -d $HTMLDIR/rrlogs/*/)
fi

# loop through each suite dir
for DIR in $LOGDIRS; do
    # continue if dir not exist or empty
    if [ ! "$(ls -A $DIR)" ]; then
        continue
    fi

    # make suite archive dir if not exist
    SUITE=$(basename $DIR)
    ZIPDIR=$ARCHDIR/$SUITE
    if [ ! -d $ZIPDIR ]; then
        ECMD "mkdir $ZIPDIR"
    fi

    # set tarzip file name with timestamps
    ZIPF=$ZIPDIR/$(date +"%F_%H%M%S_%3N.tar.gz")
    # go to suite log dir
    # check if logs older than $DAYS exist
    ECMD "cd $DIR"
    TOPF=$(find ./ -mtime +$DAYS -printf "%T@ %f\n" | sort -r | cut -d" " -f2 | head -1)
    if [ ! "$TOPF" ]; then
        TECHO "cannot find files older than $DAYS days in $DIR"
        continue
    fi
    # tarzip log files older then $DAYS
    # remove those log files
    ECMD "find ./ -mtime +$DAYS | xargs tar zcvf $ZIPF"
    ECMD "find ./ -mtime +$DAYS -exec rm {} \;"

    # set suite index file
    IDXF=$HTMLDIR/results/$SUITE/index.html
    if [ ! -f $IDXF ]; then
        TECHO "$IDXF not exist"
        continue
    fi

    # within index file
    # locate index entry having $TOPF
    L1=$(grep -n -B10 "$TOPF" $IDXF | grep "<tr>" | cut -d- -f1)
    # locate last entry 
    L2=$(grep -n "</tr>" $IDXF | tail -1 | cut -f1 -d:)
    
    # clean up entries in between $L1 and $L2
    if [ "$L1" ] && [ "$L1" -lt "$L2" ]; then
        TECHO "clean up index older than $DAYS in $IDXF"
        sed -i.bk "${L1},${L2}d" $IDXF
    else
        TECHO "cannot locate index of '$TOPF' in $IDXF"
    fi

    IP=$(ip -4 -o address list ens3 | awk '{print $4}' | cut -d/ -f1)
    # if archive link already exist. delete it anyway
    MATCHTXT="<a href=http://$IP/archives/$SUITE>"
    LINKLINE=$(grep -n "$MATCHTXT" $IDXF | cut -d: -f1)
    if [ "$LINKLINE" ]; then
        TECHO "removed archive link in $IDXF"
        sed -i.bk "${LINKLINE}d" $IDXF
    fi

    # add suite new archive link
    LKTX="logs before $(date --date="$DAYS days ago" +%F) archived"
    LINK="<a href=http://$IP/archives/$SUITE>$LKTX</a>"
    BODYEND=$(grep -n "</body>" $IDXF | cut -d: -f1)
    TECHO "insert archive link in $IDXF"
    sed -i.bk "${BODYEND}i $LINK" $IDXF
done

