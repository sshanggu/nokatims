#!/usr/bin/python

##################################################################################################
###
### Created by: Allan Phoenix
###
### Last Update: 2018-04-19
###
### Description:
###
### endpoint module:
###
###   - Service class
###   - Sap class
###
### All classes use SNMP gets and sets to poll and configure the node
###
### The relevant MIBs are TIMETRA-SAP-MIB.mib & TIMETRA-SERV-MIB.mib
###
### The returned value is the text as defined in the MIB with the exception of:
###
###   tls =  mapped to 'vpls'
###
### This is to line up with CLI output
###
### Version control:
###
### v1:
###        - Creation.
###
###
### Usage:
###
### Needs updating! 
###



import re
import pdb
import logging
from easysnmp import Session

mylog=logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler())

class Service(object):

    def __init__(self, cpm_obj, svcn, svcd):
        self.sysname = None
        self.node = cpm_obj
        self.ip = cpm_obj.ip
        self.session = cpm_obj.session
        self.id = svcd.get('id',1)
        self.type = svcd.get('type','customer')
        self.custid = svcd.get('customer_id',1)
        self.def_nh = svcd.get('def_nh',1)
        setattr(cpm_obj, svcn, self)

        # add sap in service 
        if 'saps' in svcd and svcd['saps']:
            self.add_sap(**svcd['saps'])
        

    def add_sap(self, **sapd):
        for sn,sp in sapd.items(): Sap(self,sn,sp)  


    def get_oper_state(self):
        oid     = 'svcOperStatus' + '.' + str(self.id)
        return self.session.get(oid).value


    def get_admin_state(self):
        oid     = 'svcAdminStatus' + '.' + str(self.id)
        return self.session.get(oid).value


    def set_admin_state (self,state):
        oid = 'svcAdminStatus' + '.' + str(self.id)

        if state == 'up' or state == 'down':
            self.session.set(oid,state,'i')
        else:
            print("Illegal service state of ", state, "passed into set_admin_state")


    def shutdown(self):
        oid = 'svcAdminStatus' + '.' + str(self.id)
        self.session.set(oid,'down','i')


    def no_shutdown(self):
        oid = 'svcAdminStatus' + '.' + str(self.id)
        self.session.set(oid,'up','i')


    def wait_service_oper_up_ex(self,wait):
        if not self.sysname:  self.sysname = self.node.get_system_name()
        count    = 0
        mylog.info("Wait up to %s seconds for node %s (%s) service %s to go oper up " %(wait,self.sysname,self.ip,self.id))

        while self.get_oper_state() != 'up':
            if count == wait:
                mylog.error ("Node %s (%s) service %s NOT oper up after %s seconds " %(self.sysname,self.ip,self.id,count))
                return False 
            count += 1
            time.sleep(1)
        mylog.info ("Node %s (%s) service %s oper down up %s seconds " %(self.sysname,self.ip,self.id,count))
        return True 

    def wait_service_oper_down_ex(self,wait):
        if not self.sysname:  self.sysname = self.node.get_system_name()
        count    = 0
        mylog.info("Wait up to %s seconds for node %s (%s) service %s to go oper down " %(wait,self.sysname,self.ip,self.id))

        while self.get_oper_state()  != 'down':
            if count == wait:
                mylog.error ("Node %s (%s) service %s NOT oper down after %s seconds " %(self.sysname,self.ip,self.id,count))
                return False 
            count += 1
            time.sleep(1)
        mylog.info ("Node %s (%s) service %s oper down after %s seconds " %(self.sysname,self.ip,self.id,count))
        return True 

class Sap(object):
    
    def __init__(self, svc_obj, sap_name, sap_pid):
        self.sysname = None
        self.sap_id  = sap_pid
        self.port_id = sap_pid.split(':')[0]
        self.vlan    = sap_pid.split(':')[1]
        self.ip      = svc_obj.ip
        self.svc_id  = svc_obj.id
        self.session = svc_obj.session
        self.name    = sap_name
        self.node    = svc_obj.node
        setattr(svc_obj, sap_name, self)

        # Perform an SNMP walk on the port table to get the ifIndex for port 'port'
        table = 'tmnxPortName.1'
        table_items = self.session.walk(table)

        for item in table_items:
            if item.value == self.port_id:
                self.port_idx = item.oid_index.split('.')[1]


    def shutdown(self):
        print("hehehee")
        oid = 'sapAdminStatus' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        self.session.set(oid,'down','i')


    def no_shutdown(self):
        oid = 'sapAdminStatus' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        self.session.set(oid,'up','i')


    def get_oper_state(self):
        oid = 'sapOperStatus' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        return self.session.get(oid).value


    def get_admin_state(self):
        oid = 'sapAdminStatus' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        return self.session.get(oid).value


    def set_admin_state(self,state):
        oid = 'sapAdminStatus' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        if state == 'up':
            self.session.set(oid,'up','i')
        elif state == 'down':
            self.session.set(oid,'down','i')
        else:
            print("Invalid SAP state of %s passed into set_admin_state" %(state))


    def wait_sap_oper_up_ex(self,wait):
        if not self.sysname:  self.sysname = self.node.get_system_name()
        count    = 0
        mylog.info("Wait up to %s seconds for node %s (%s) service %s sap %s to go oper up " %(wait,self.sysname,self.ip,self.svc_id, self.sap_id))

        while self.get_oper_state() != 'up':
            if count == wait:
                mylog.error ("Node %s (%s) service %s sap %s NOT oper up after %s seconds " %(self.sysname,self.ip,self.svc_id,self.sap_id,count))
                return False 
            count += 1
            time.sleep(1)
        mylog.info ("Node %s (%s) service %s sap %s oper up %s seconds " %(self.sysname,self.ip,self.svc_id,self.sap_id,count))
        return True 

    def wait_sap_oper_down_ex(self,wait):
        if not self.sysname:  self.sysname = self.node.get_system_name()
        count    = 0
        mylog.info("Wait up to %s seconds for node %s (%s) service %s sap %s to go oper down " %(wait,self.sysname,self.ip,self.svc_id, self.sap_id))

        while self.get_oper_state()  != 'down':
            if count == wait:
                mylog.error ("Node %s (%s) service %s sap %s NOT oper down after %s seconds " %(self.sysname,self.ip,self.svc_id,self.sap_id,count))
                return False 
            count += 1
            time.sleep(1)
        mylog.info ("Node %s (%s) service %s sap %s oper down %s seconds " %(self.sysname,self.ip,self.svc_id,self.sap_id,count))
        return True 

    def get_type(self):
        oid      = 'sapType' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        sap_type = self.session.get(oid).value
        if sap_type == 'tls':
            return 'vpls'
        else:
            return sap_type


    def get_oper_flags(self):
        oid = 'sapOperFlags' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        return self.session.get(oid).value


    def get_ingress_packets(self):
        oid = 'sapBaseStatsIngressPchipOfferedLoPrioPackets' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        snmp_get_lo =  self.session.get(oid).value

        oid = 'sapBaseStatsIngressPchipOfferedHiPrioPackets' + "." + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        snmp_get_high =  self.session.get(oid).value

        ingress_packets = int(snmp_get_lo) + int(snmp_get_high)

        return ingress_packets


    def get_egress_packets(self):
        oid = 'sapBaseStatsEgressQchipForwardedInProfPackets' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        snmp_get_q_fwd_in  =  self.session.get(oid).value

        oid = 'sapBaseStatsEgressQchipForwardedOutProfPackets' + '.' + str(self.svc_id) + '.' + str(self.port_idx) + '.' + str(self.vlan)
        snmp_get_q_fwd_out = self.session.get(oid).value

        egress_packets = int(snmp_get_q_fwd_in) + int(snmp_get_q_fwd_out)

        return egress_packets


    def get_ingress_pchip_dropped_packets(self):
        oid  = 'sapBaseStatsIngressPchipDroppedPackets' + "." + str(self.svc_id) + "." + str(self.port_idx) + "." + str(self.vlan)
        return int(self.session.get(oid).value)


    def get_ingress_pchip_dropped_octets(self):
        oid  = 'sapBaseStatsIngressPchipDroppedOctets' + "." + str(self.svc_id) + "." + str(self.port_idx) + "." + str(self.vlan)
        return int(self.session.get(oid).value)

##
## aphoenix - move to new router.py file
##

class Router(object):

    def __init__(self, cpm_obj, router_name, router_desc):
        self.name = router_name
        self.node = cpm_obj
        self.ip = cpm_obj.ip
        self.session = cpm_obj.session
        setattr(cpm_obj, router_name, self)

        self.set_router_idx()
        if 'interfaces' in router_desc and router_desc['interfaces']:
            self.add_interface(**router_desc['interfaces'])
        
    def set_router_idx(self):
        table_items = self.session.walk('vRtrName')
        for item in table_items:
            if self.name in item.value:
                self.r_idx = item.oid_index

    def get_router_id(self):
        return (self.session.get('vRtrRouterId' + '.' + str(self.r_idx))).value

    def get_router_admin(self):
        return (self.session.get('vRtrAdminState' + '.' + str(self.r_idx))).value

    def get_vrf_target(self):
        return (self.session.get('vRtrVrfTarget' + '.' + str(self.r_idx))).value

    def get_vrf_export_target(self):
        return (self.session.get('vRtrVrfExportTarget' + '.' + str(self.r_idx))).value

    def get_vrf_import_target(self):
        return (self.session.get('vRtrVrfImportTarget' + '.' + str(self.r_idx))).value

    def get_router_type(self):
        return (self.session.get('vRtrType' + '.' + str(self.r_idx))).value

    def get_router_as(self):
        return (self.session.get('vRtrAS4Byte' + '.' + str(self.r_idx))).value

    def get_route_distinguisher(self):
        return (self.session.get('vRtrRouteDistinguisher' + '.' + str(self.r_idx))).value

    def add_interface(self, **router_desc):
        for int_name,int_info in router_desc.items():  
            Interface(self,int_name, int_info)

class Interface(object):    

    def __init__(self, router_obj, int_name, int_desc):
        self.name    = int_name
        self.router  = router_obj
        self.ip      = router_obj.ip
        self.session = router_obj.session
        self.r_idx   = router_obj.r_idx

        self.set_interface_idx()
        setattr(router_obj, int_name, self)

    def set_interface_idx(self):
        table = 'vRtrIfName' + '.' + self.r_idx
        table_items = self.session.walk(table)
        for item in table_items:
            if self.name in item.value:
                int_idx = item.oid_index
                self.int_idx = int_idx.split('.')[1]

    def get_mac_address(self):
        return (self.session.get('vRtrIfPhysicalAddress' + '.' + str(self.r_idx) + '.' + str(self.int_idx))).value

    def get_admin_state(self):
        return (self.session.get('vRtrIfAdminState' + '.' + str(self.r_idx) + '.' + str(self.int_idx))).value

    def get_oper_state(self):
        return (self.session.get('vRtrIfOperState' + '.' + str(self.r_idx) + '.' + str(self.int_idx))).value

    def shutdown (self):
        oid = 'vRtrIfAdminState' + '.' + str(self.r_idx) + '.' + str(self.int_idx)
        self.session.set(oid,'outOfService','i')

    def no_shutdown (self):
        oid = 'vRtrIfAdminState' + '.' + str(self.r_idx) + '.' + str(self.int_idx)
        self.session.set(oid,'inService','i')
