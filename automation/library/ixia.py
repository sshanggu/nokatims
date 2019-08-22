#!/usr/bin/python

##################################################################################################
###
### Created by: Allan Phoenix 
###
### Last Update: 2018-04-13
###
### Description:  
###
### Wrapper procs to call Ixia libraries
###
### Version control:
###
### v1:  Creation.   
###
###
###
### Usage:
###
###     Needs updating!      

from utils import *
from IxNetwork import IxNet
from tabulate import tabulate
from collections import OrderedDict
import time, logging

# TODO - move to within class
def take_stats_snapshot (ixNet, name, csvLoc):

    sys.path.append (csvLoc)
    root=ixNet.getRoot()
    stats=ixNet.getList(root,'statistics')[0]

    view = get_stat_view(ixNet,name)
    views=view.split(',')

    snapshot=ixNet.getList(stats,'csvSnapshot')[0]
    ixNet.execute('resetToDefaults',snapshot)
    ixNet.setAttribute(snapshot,'-csvLocation',csvLoc)
    ixNet.setAttribute(snapshot,'-views',views)
    ixNet.commit()
    ixNet.execute('takeCsvSnapshot',snapshot)


###############################################################################
# 2018/02/15 sshanggu
#
# Add class IxNetx that inherits IxNet
###############################################################################
mylog=logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler(sys.stdout))

# convert ns-str to ms-str
def n2m(lns):
    lms=list()
    for s in lns:
        if s: s=str(float(s)/1000000)
        lms.append(s)
    return lms

# convert str to float-str
def s2f(ls):
    lf=list()
    for s in ls:
        lf.append(str(float(s)))
    return lf

# sort and uniquify list     
def uniq(l):
    ul=list()
    for e in l:
        if e not in ul: ul.append(e)
    ul.sort(); return ul

class IxNetx(IxNet):
    def __init__(self, **ixiad):
        self.connected=True
        self.stats=OrderedDict()
        self.rowstats=OrderedDict()
        self.user_stats=OrderedDict()
        self.flow_stats=OrderedDict()
        self.user_flow_stats=OrderedDict()
        self.traffic_items=list()
        self.traffic_names=list()
        self.name = ixiad.get('name','ixnet')
        self.server = ixiad.get('server')
        self.chassis = ixiad.get('chassis') 
        self.tclport = ixiad.get('port')
        self.pattern = ixiad.get('pattern',None)
        self.ixtis=None
        # log_columns defines those columns to be printed in log file
        # they must be sub-list of stats_long_names
        self.log_columns=[
            'Tx Frames',
            'Rx Frames',
            'Frames Delta',
            'Loss %',
            'Packet Loss Duration (ms)',
            'Tx Frame Rate',
            'Store-Forward Avg Latency (ns)']
        # stats_long_names defines those columns interested by tester
        # they must be sub-list of real Ixia view columnCaptions
        self.stats_long_names=[
            'Tx Frames',
            'Rx Frames',
            'Frames Delta',
            'Loss %',
            'Packet Loss Duration (ms)',
            'Tx Frame Rate',
            'Rx Frame Rate',
            'Store-Forward Avg Latency (ns)',
            'Store-Forward Min Latency (ns)',
            'Store-Forward Min Latency (ns)']
        # stats_short_names defines short-names that correspond to
        # stats_long_names (one by one)
        self.stats_short_names=[
            'tx',
            'rx',
            'delta',
            'loss%',
            'loss_ms',
            'tx_rate',
            'rx_rate',
            'avg_latency'
            'min_latency'
            'max_latency']
        
        # run parent constructot
        IxNet.__init__(self)
        # set stats_root
        self.stats_root=self._root+'statistics/view:"Traffic Item Statistics"'
        self.stats_user=self._root+'statistics/view:"User Defined Statistics"'
        # try connect and set traffic
        try:
            self.connect(self.server,'-port',self.tclport,'-version','8.01')
            mylog.info('Ixia %s:%s connected' %(self.server,self.tclport))
            if self.pattern:
                self.set_traffic(pattern=self.pattern,commit=True)
        except:
            mylog.exception('Ixia connection error!')
            self.connected=False

    # pattern and names excluded each other
    def set_traffic(self, pattern=str(), names=list(), commit=False):
        if not self.connected: mylog.error('Ixia not connected!'); return False

        if not self.ixtis:
            self.ixtis=self.getList(self._root+'/traffic','trafficItem')

        # pick useful traffic_names based on passed-in pattern or names
        for t in self.ixtis:
            # by default, set 'enabled' false
            self.setAttribute(t,'-enabled','false')
            tn = self.getAttribute(t,'-name')
            if pattern or names:
                if pattern:
                    if re.search(pattern,tn): self.traffic_names.append(tn)
                else:
                    if tn in names: self.traffic_names.append(tn)
            else:
                self.traffic_names.append(tn)
        
        # sort traffic_names and uniquify
        self.traffic_names=uniq(self.traffic_names)

        # reset traffic_items based on sorted traffic_names
        self.traffic_items=list()
        for tn in self.traffic_names:
            for t in self.ixtis:
                if tn == self.getAttribute(t,'-name'):
                    self.traffic_items.append(t)
                    # enabled in-use traffics
                    self.setAttribute(t,'-enabled','true')
        
        # commit and apply traffic (default not to commit and apply)
        if commit:
            try:
                self.commit()
                self.execute('apply','/traffic')
                mylog.info('Ixia commit/apply traffic successful')
                self.connected=True
            except:
                mylog.error('Ixia traffic commit/apply error!')
                self.connected=False
       
    def start_traffic(self, names=list(), atime=15):
        if not self.connected: mylog.error('Ixia not connected!'); return False

        if names: self.set_traffic(names=names)
        # return if traffic items not set
        if not self.traffic_items:
            mylog.error('Ixia object "%s" has no traffic items' %self)
            mylog.error('Call set_traffic before start_traffic' %self)
            return
        tis=self.traffic_items
        # start partial traffic if names passed in 
        if names:
            tmp=list()
            for tn in names:
                if tn in self.traffic_names:
                    tmp.append(self.traffic_items[self.traffic_names.index(tn)])
            tis=tmp
        # start traffic_items 
        for t in tis:
            self.execute('startStatelessTrafficBlocking',t)
            mylog.info('Traffic started: %s' %self.getAttribute(t,'-name'))
        # let traffic run sometime
        mylog.info('Let traffic run %ds' %atime)
        time.sleep(atime)
        
    def stop_traffic(self, names=list(), btime=15):
        if not self.connected: mylog.error('Ixia not connected!'); return False

        # return if traffic items not set
        if not self.traffic_items:
            mylog.error('Ixia object "%s" has no traffic items' %self)
            mylog.error('Call set_traffic before stop_traffic' %self)
            return
        tis=self.traffic_items
        # stop user specified traffic_items    
        if names:
            tmp=list()
            for tn in names:
                if tn in self.traffic_names:
                    tmp.append(self.traffic_items[self.traffic_names.index(tn)])
            tis=tmp
        # run traffic before stop
        mylog.info('Let traffic run %ds' %btime)
        time.sleep(btime)
        # stop traffic_items
        for t in tis:
            self.execute('stopStatelessTraffic',t)
            mylog.info('Traffic stopped: %s' %self.getAttribute(t,'-name'))
        # wait 10s for stable stats
        mylog.info('Wait 10s for stats to be stable')
        time.sleep(10)

    def drill_ipv6(self,traf_item):

        view = self.stats_root
        ddOption = "Drill Down Per IPv6:Traffic Class"
        targetRow = 0

        print("Creating DD %s on view %s" %(ddOption,view))
        self.setAttribute(traf_item,'-targetDrillDownOption')

    def set_stats(self, log=True, loss_only=False):
        if not self.connected: mylog.error('Ixia not connected!'); return False

        mylog.info('Snapshot traffic stats')
        statspage=self.stats_root+'/page'
        self.page_ready(path=statspage)

        # get pages/captions/
        tpages=int(self.getAttribute(statspage,'-totalPages'))
        stcaps=self.getAttribute(statspage,'-columnCaptions')
        self.rowstats['columnCaptions']=stcaps

        # loop through all pages
        for x in range(1, tpages+1):
            self.setAttribute(statspage,'-currentPage',x)
            self.commit()
            self.page_ready(path=statspage)
            for pv in self.getAttribute(statspage,'-pageValues'):
                rowdata=pv.pop()
                self.rowstats[rowdata[0]]=rowdata

        # log stats
        if log:
            mylog.info('===== %s =====' %statspage)
            self.logstats(loss_only=loss_only, **self.rowstats)

    def get_stats(self, tn, sc):
        if not self.connected: mylog.error('Ixia not connected!'); return False

        # when stats-column (sc) in short format, convert it to long one
        if sc in self.stats_short_names:
            sc=self.stats_long_names[self.stats_short_names.index(sc)]
        
        # find stats-column (sc) index
        if sc in self.rowstats['columnCaptions']:
            si=self.rowstats['columnCaptions'].index(sc)
            if tn in self.rowstats:
                return float(self.rowstats[tn][si])
        
        # log error
        mylog.error('stats %s/%s NOT exist.' %(tn,sc))
        return False

    def set_user_def_drill_stats(self, log=True, target_name=str(),
        ddopt='Drill Down per Rx Port', loss_only=False):
        if not self.connected: mylog.error('Ixia not connected!'); return False

        # get traffic item names
        tinames=self.execute('getColumnValues',self.stats_root,'Traffic Item')
        # if target_name passed-in, set targetrows accordingly
        if target_name: targetrows=[tinames.index(target_name)]
        else: targetrows=range(len(tinames))

        # loop through targetrows and drilldown
        drillDown=self.stats_root+'/drillDown'
        for row in targetrows:
            # set target row
            tin=tinames[row]
            mylog.info('\nDrilldown target:(%s) "%s"' %(row, tin))
            self.setAttribute(drillDown,'-targetRowIndex',row)
            self.commit()
            ddopts=self.getAttribute(drillDown,'-availableDrillDownOptions')
            self.ddopts = ddopts
            mylog.info('Drilldown available options: %s' %ddopts)
            if ddopt not in ddopts:
                mylog.info('Option "%s" not available for %s' %(ddopt,tin))
                continue

            # set drilldown option
            mylog.info('Drilldown option set to: %s' %ddopt)
            self.setAttribute(drillDown,'-targetDrillDownOption',ddopt)
            self.commit()
            self.execute('doDrillDown',drillDown)
            mylog.info('Drilldwon "%s" for "%s" created' %(ddopt,tin))

            # check ready user-defined-statistics/pages
            udspage=self.stats_user+'/page'
            self.setAttribute(udspage,'-isReadyTimeout',90)
            if not self.page_ready(path=udspage): continue

            # common drilldown variables
            ddpages=int(self.getAttribute(udspage,'-totalPages'))
            ddcaps=self.getAttribute(udspage,'-columnCaptions')
            dddk=tin+'/'+ddopt;# drilldown dict key
            self.user_stats[dddk]=OrderedDict()
            self.user_stats[dddk]['columnCaptions']=ddcaps

            # loop through drilldown pages
            for pg in range(1, ddpages+1):
                mylog.info('Drilldown set page %d' %pg)
                self.setAttribute(udspage,'-currentPage',pg)
                self.commit()
                if not self.page_ready(path=udspage,page=pg): continue
                # get page values and fill in dict
                for pv in self.getAttribute(udspage,'-pageValues'):
                    rowdata=pv.pop()
                    self.user_stats[dddk][rowdata[0]]=rowdata

            # log drilldown page data
            if log:
                mylog.info('\n===== %s =====' %dddk)
                self.logstats(loss_only=loss_only, **self.user_stats[dddk])

    def get_user_def_drill_stats(self,tn,dn,sc,ddopt='Drill Down per Rx Port'):
        if not self.connected: mylog.error('Ixia not connected!'); return False
        
        mylog.info('Get User defined Stats For %s/%s/%s/%s' %(tn,ddopt,dn,sc))
        # check traffic-item and drilldown-opt
        kname='%s/%s' %(tn,ddopt)
        if kname in self.user_stats:
            dddict=self.user_stats[kname]
        else:
            mylog.error('Traffic item/Drill down, %s/%s, Not found!' %(tn,ddopt))
            return False
        
        # check drilldown item name(dn)
        if dn in dddict:
            # when stats-column(sc) in short format, convert it to long one
            if sc in self.stats_short_names:
                sc=self.stats_long_names[self.stats_short_names.index(sc)]
            si=dddict['columnCaptions'].index(sc)
            return float(dddict[dn][si])
        else:
            mylog.error('Drill down item, %s, Not found!' %dn)
            return False


    def check_user_def_drill_stats(self, target_name=str(), ddopt='Drill down per Source/Dest Endpoint Pair', check_val='loss_ms', check_thresh=0):

        rval = True
        mylog.info('Check User Def Traffic Class Ixia Stats For Source / Dest endpoints')

        if not self.connected: mylog.error('Ixia not connected!'); return False

        ddn = target_name + '/' + ddopt

        ddn = str(ddn)

        idx=self.user_stats[ddn]['columnCaptions'].index('Packet Loss Duration (ms)')
        for line in self.user_stats[ddn].keys():
            if 'columnCaptions' not in line:
                lx = float(self.user_stats[ddn][line][idx])
                if lx > float(check_thresh):
                    mylog.error("Endpoint %s loss of %s > threshold %s" %(line,lx,check_thresh))
                    rval = False

        return rval


    def clear_stats(self):

        if not self.connected: mylog.error('Ixia not connected!'); return False

        mylog.info('Clear Ixia Stats')
        self.execute('clearStats')

    def check_losspct(self, pct=2):
        if not self.connected: mylog.error('Ixia not connected!'); return [False]

        self.set_stats(log=True)
        checks=[]
        for tn in self.traffic_names:
            if "SARHm01" in tn: continue;# skip SARHm01 stream
            pctv=self.get_stats(tn,'loss%')
            
            # traffic name(tn) stats not found 
            if not isinstance(pctv, float):
                checks.append(False); continue
            
            # traffic name(tn) stats exist
            if pctv > pct:
                mylog.error('%s traffic loss > %d%%. Fail!' %(tn,pct))
                checks.append(False)
            else:
                mylog.info('%s traffic loss < %d%%. Good' %(tn,pct))
                checks.append(True)
        
        return checks

    def logstats(self, loss_only=False, **statsd):
        # initialize variables
        capl=statsd['columnCaptions']
        idlt=capl.index('Frames Delta')
        caps=[capl[0]]+self.log_columns
        cidx=[capl.index(x) for x in caps]
        if loss_only:
            mylog.info('Only stats with Frame-Delta(!=0) logged')

        # prepare log data (list of lists)
        logdata=list()
        for ky,vl in statsd.items():
            if 'column' in ky: continue
            if loss_only and vl[idlt]=='0': continue
            logdata.append([vl[x] for x in cidx])

        # log with tabulate
        logdata.sort()
        mylog.info('\n'+tabulate(logdata, headers=caps))

    def page_ready(self,path=None,page=1):
        if not path: return False
        mylog.info('Check path//page ready, %s//%s' %(path,page))
        if self.getAttribute(path,'-isReady')=='true':
            mylog.info('Path//page %s//%s ready' %(path,page))
            return True
        mylog.error('Path//page %s//%s NOT ready in 90s!' %(path,page))
        return False

