#!/usr/bin/python

###############################################################################
#
# Created by: Allan Phoenix
# Last Update: 2017-12-14
#
# Description:
# All testbed-related classes are defined here:
# class Testbed
# class Node
# class Mda
# class Lag
# class Iom
#
# All connection protocols are supported
# netconf (ncclient module)
# telnet (pexpect module)
# snmp (easysnmp module)
# ssh (paramiko module)
#
# Usage:
# import node
# tb = node.Testbed(tbyaml)
# tb.nodeA.nodeMethod()
# tb.nodeA.portB.portMethod()
#
###############################################################################

from common_vars import *
from datetime import datetime
from ncclient import manager
from lxml.etree import iselement
import os
import yaml
import re
import pexpect
import time
import sys
import utils
import ixia
import service
import paramiko
import easysnmp
import getpass
import imsext
import ftplib
import xrpc

mylog = utils.get_logger(__name__)
TODAY = datetime.today().strftime("%g%b%d")


class Node(paramiko.SSHClient):
    """
    Inherits paramiko.SSHClient and defines node-level methods
    """

    def __init__(self, **cpmd):
        """
        Initilize node attributes based on passed-in cpmd
        Do node-connection with snmp, telnet, ssh, and netconf
        Add ports/routers/services/ioms/mdas instances if needed

        Parameters: cpmd(dict) -- node data from testbed.yaml
        """
        # init ssh client
        super().__init__()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # set node attributes
        self.ip = cpmd.get('mgmt_ip', None)
        self.ipv6 = cpmd.get('mgmt_ipv6', None)
        self.system_ip = cpmd.get('system_ip', '192.168.0.1')
        self.pwd = cpmd.get('password', 'Nokia2018!')
        self.name = cpmd.get('name', '#')
        self.user = cpmd.get('username', 'admin')
        self.console = cpmd.get('console', None)
        self.netconf = cpmd.get('netconf', None)
        self.area_code = cpmd.get('area_code')
        self.skipPrompt = cpmd.get('skipPrompt', False)

        self.session = None
        self.mdcli = False
        self._snmpd = None
        self._sshd = None
        self._nccd = None

        if self.ipv6:
            self._sshd = {'hostname': self.ipv6,
                          'username': self.user,
                          'password': self.pwd,
                          'allow_agent': False,
                          'look_for_keys': False}
        elif self.ip:
            self._sshd = {'hostname': self.ip,
                          'username': self.user,
                          'password': self.pwd,
                          'allow_agent': False,
                          'look_for_keys': False}

        if self.ip and self.netconf:
            self._nccd = {'host': self.ip,
                          'username': self.user,
                          'password': self.pwd,
                          'hostkey_verify': False,
                          'allow_agent': False,
                          'look_for_keys': False,
                          'device_params': {'name': 'alu'}}
        if self.ip:
            self._snmpd = {'hostname': self.ip,
                           'version': 2,
                           'community': 'public',
                           'use_enums': True,
                           'timeout': 10}

        utils.framelog("%s node instance initialize ..." % self.name)
        self._snmpcon()  # connect snmp session
        self.sysname = self.get_system_name() if self.session else self.name

        self.hv_user = cpmd.get('hv_username', None)
        self.hv_pwd = cpmd.get('hv_password', None)

        self.prompt = self.name
        self.port_dict = dict()
        self.ioms = dict()
        self.mdas = dict()
        self.sshcon = None
        self.telcon = None
        self.nccon = None

        # set not prompt
        if self.name == '#':
            self.prompt0 = '#'
            self.prompt1 = '>'
        elif 'cmu' in self.name:
            self.prompt0 = 'cmu ~]#'
            self.prompt1 = self.prompt0
        elif 'rfsim' in self.name:
            self.prompt0 = 'RFSIM>'
            self.prompt1 = self.prompt0
        else:
            self.prompt0 = self.prompt+'#'
            self.prompt1 = self.prompt+'>'

        # connect node via either ssh, telnet, or netconf
        self.connect()

        # add port instance
        if 'ports' in cpmd and cpmd['ports']:
            self.add_port(**cpmd['ports'])

        # add router instance
        if 'routers' in cpmd and cpmd['routers']:
            self.add_router(**cpmd['routers'])

        # add service instance
        if 'services' in cpmd and cpmd['services']:
            self.add_service(**cpmd['services'])

        # add ioms instance
        if 'ioms' in cpmd and cpmd['ioms']:
            self.add_ioms(**cpmd['ioms'])

        # add mdas instance
        if 'mdas' in cpmd and cpmd['mdas']:
            self.add_mdas(**cpmd['mdas'])

    def connect(self, retry=1):
        """
        Set node.telcon session-handle if telnet connection successful
        Set node.sshcon session-handle if ssh connection successful
        Set node.nccon session-handle if netconf connection successful

        Parameters: retry(int) -- number of ssh connection retry
        """
        self._telcon()
        self._sshcon(retry)
        self._netconf()

    def _snmpcon(self):
        if self._snmpd:
            self.session = easysnmp.Session(**self._snmpd)
            mylog.info("%s snmp session established" % self.name)

    def _snmpset(self, oid, value, snmp_type):
        try:
            self.session.set(oid, value, snmp_type=None)
            return "OK"
        except Exception:
            mylog.error("SNMP set (%s,%s,%s) error!" % (oid, value, snmp_type))
            utils.log_exc(sys.exc_info())
            return "ERROR"

    def _netconf(self):
        if self._nccd and (not self.nccon or not self.nccon.connected):
            mylog.info("%s ncclient.manager.connect(%s)" % (
                self.sysname, utils.d2s(self._nccd)))
            self.nccon = manager.connect(**self._nccd)
            self.nccon.loadcfg = self.nccon.load_configuration  # rename
            mylog.info("%s netconf session OK" % self.sysname)

    def _telcon(self):
        """ try telnet node console """
        if self.console and not self.telcon:
            self.clear_console()  # clear console anyway
            time.sleep(1)
            mylog.info('%s spawn <telnet %s>' % (self.sysname, self.console))
            conn = pexpect.spawn('telnet %s' % self.console, timeout=10)
            time.sleep(1)
            # for rfsim. no password required
            if 'rfsim' in self.name:
                if conn.expect(['RFSIM>', pexpect.TIMEOUT]) == 0:
                    mylog.info('%s console connected. Good' % self.name)
                    self.telcon = conn
                else:
                    mylog.error('telnet %s TIMEOUT!' % self.console)
                return
            # for node that requires login password
            if conn.expect(['Escape character is', pexpect.TIMEOUT]) == 0:
                conn.sendline('')
                index = conn.expect(
                    ['Login:', self.prompt1, self.prompt0, pexpect.TIMEOUT])
                if index <= 2:
                    if index == 0:
                        if self.hv_user and self.hv_pwd:
                            # Hypervisor user/password defined in testbed yaml
                            # Assume connection is to a WBX HV
                            conn.sendline(self.hv_user)
                            conn.expect('Password:')
                            conn.sendline(self.hv_pwd)
                            conn.expect(self.prompt0)
                        else:
                            conn.sendline(self.user)
                            conn.expect('Password:')
                            conn.sendline(self.pwd)
                            conn.expect(self.prompt0)
                    elif index == 1:
                        conn.sendline('exit all')
                        conn.expect(self.prompt0)

                    # connction good, assign self.telcon
                    if self.hv_user and self.hv_pwd:
                        mylog.info('%s Hypervisor console OK' % self.name)
                    else:
                        mylog.info('%s console session OK' % self.name)
                    self.telcon = conn
                    self.telcon.sysname = self.sysname  # set telcon.sysname
                    self.telcon.prompt0 = self.prompt0  # set telcon.prompt0
                    self.telcon.prompt1 = self.prompt1  # set telcon.prompt1
                    # set env no more
                    mylog.info('%s environment no more' % self.prompt0)
                    conn.sendline('environment no more')
                    conn.expect(self.prompt0)
                    if self.hv_user:
                        # Linux show version
                        mylog.info('%s uname -a' % self.prompt0)
                        conn.sendline('uname -a')
                        conn.expect(self.prompt0)
                        mylog.info(utils.fmtout(conn.before))
                else:
                    mylog.error('login %s timeout' % self.console)
            else:
                mylog.error('%s telnet session timeout!' % self.name)

    def _sshcon(self, retry=1):
        """
        ssh to node mgmt-intf and set classic configuration mode

        Parameters: retry(int) -- number of connection retry
        """
        envcmd = 'environment no more'
        if self._sshd and retry != 0 and (
                not self.sshcon or not self.sshcon.is_active):

            mylog.info("%s paramiko.client.SSHClient.connect(%s) (retry=%d)"
                       % (self.sysname, utils.d2s(self._sshd), retry))
            try:
                super().connect(**self._sshd)
                mylog.info("%s ssh session OK" % self.sysname)
                self.sshcon = self.invoke_shell()
                self.sshcon.sysname = self.sysname  # set sshcon.sysname
                self.sshcon.mdcli = False  # set sshcon.mdcli (default)
                self.sshcon.node = self  # set sshcon.node
                mylog.info("%s interactive shell OK" % self.sysname)
                self.sshcon.cmdline(log=False)  # flush login msg
                if 'cmu' not in self.name:
                    self.sshcon.setmode()  # set SR-node classic mode
            except Exception:
                delay = retry * 10
                mylog.info('connection timeout. retry after %ss' % delay)
                time.sleep(delay)
                self._sshcon(retry-1)

    def close(self):
        """
        Close telnet session and set node.telcon None
        Close ssh session and set node.sshcon None
        Close netconf session and set node.nccon None
        """
        if self.telcon:
            self.telcon.close()
            self.telcon = None
            mylog.info("%s telnet session closed" % self.sysname)
        if self.sshcon:
            try:
                self.sshcon.close()
            except Exception:
                mylog.error(
                    "%s ssh session closing error." % self.sysname +
                    " ignored it as the connection reset by peer (node)")
            self.sshcon = None
            mylog.info("%s ssh session closed" % self.sysname)
        if self.nccon:
            if self.nccon.connected:
                try:
                    self.nccon.close_session()
                except Exception:
                    mylog.info("netconf session timeout!")
            self.nccon = None
            mylog.info("%s netconf session closed" % self.sysname)

    def cliexe(self, cmd, log=True, retry=1):
        """
        Connect to node if it is not connected yet
        Try to send command via ssh session if it exists
        Try to send command via telnet session if ssh session not exists

        Parameters: cmd(str) -- cli command string
                    log(bool) -- log cli output if True
                    retry(int) -- number of connection retry
        Return: command output if cmd executed
                '\n^\nError: Bad command.\n' if bad command
                empty string if connection failed
        """
        self.connect(retry)
        if self.sshcon:
            return self.sshcon.cmdline(cmd, log=log)
        elif self.telcon:
            return self.telcon.cmdline(cmd, log=log)
        else:
            mylog.info("%s Neither ssh nor console exists" % self.sysname)
            return str()  # return empty string

    def send_command(self, cmd, style='classic', protocol='ssh'):
        '''
        send command(str) based on parameter style/protocol

        Parameters: cmd(str) -- user should provide correct syntax cmd
                                according to style and protocol
                    style(str) -- 'classic'(default)|'md'
                                  style works when protocol='ssh'
                    protocol(str) -- 'ssh'(default)|'netconf'

        Return: cmd output
        '''
        self.connect(1)
        if self.sshcon and protocol == 'ssh':  # ssh session
            self.sshcon.setmode(style)  # set ssh session config mode
            if self.mdcli and cmd.startswith('config'):
                return self.sshcon.mdconf(cmd)  # model-driven configuration
            else:
                return self.sshcon.cmdline(cmd)  # classic cfg|show, md-show
        elif self.nccon and protocol == 'netconf':  # netconf session
            fmt = 'cli' if isinstance(cmd, str) else 'xml'
            mylog.info('%s Netconf %s operation:' % (self.sysname, fmt))
            if fmt == 'cli' and cmd.startswith('show '):
                return self.nccon.show_cli(cmd).data_text  # netconf cli-show
            elif fmt == 'cli' and cmd.startswith('config') or iselement(cmd):
                try:  # netconf cli-config or xml-config
                    return self.nccon.loadcfg(format=fmt, config=cmd)
                except Exception:
                    utils.log_exc(sys.exc_info())
                    return False
            else:
                mylog.error('Wrong command: %s' % cmd)
                return False
        else:
            mylog.error('Wrong protocol %s Or no connection' % protocol)
            return False

    def reboot(self):
        try:
            # do connection if not connected
            if not self.sshcon and not self.connect():
                mylog.error('fail to ssh %s. reboot aborted!' % self.name)
                return False
            # cmu (linux) reboot
            if 'cmu' in self.name:
                mylog.info(self.prompt0+'reboot')
                self.sshcon.sendline('reboot')
            # sr router reboot
            if 'SR' in self.name or 'CORE' in self.name:
                mylog.info(self.prompt0+'admin reboot')
                self.sshcon.sendline('admin reboot')
                self.sshcon.expect(
                    r'Are you sure you want to reboot \(y/n\)\?')
                mylog.info(self.sshcon.after+'y')
                self.sshcon.sendline('y')
            # close connection since reboot
            mylog.info('%s rebooted' % self.name)
            time.sleep(2)
            self.close()
            return True
        except Exception:
            mylog.error('%s reboot failed! connection issue?' % self.name)
            return False

    def sr_reboot(self, ssh_retry=4, mda_up_timeout=200, intv=20):
        utils.framelog('reboot %s' % self.sysname)
        if "(y/n)?" in self.cliexe('admin reboot'):
            if self.sshcon:  # ssh session
                self.sshcon.cmdline('y')
                self.close()
                # time.sleep(3)
                self._sshcon(ssh_retry)
            else:  # console session
                self.telcon.cmdline(
                    'y', timeout=200, prompt='Login:', log=False)
                self.telcon.cmdline(self.user, prompt='Password:')
                self.telcon.cmdline(self.pwd)
                self.telcon.cmdline("environment no more")
        return True

    def sr_reboot2(self, ssh_retry=4, mda_up_timeout=200, intv=20):
        utils.framelog('reboot %s' % self.sysname)
        if "(y/n)?" in self.cliexe('admin reboot'):
            if self.sshcon:  # ssh session
                self.sshcon.cmdline('y')
                self.close()
                # time.sleep(3)
                self._sshcon(ssh_retry)
            else:  # console session
                self.telcon.cmdline(
                    'y', timeout=200, prompt='Login:', log=False)
                self.telcon.cmdline(self.user, prompt='Password:')
                self.telcon.cmdline(self.pwd)
                self.telcon.cmdline("environment no more")
        # poll mda up
        return utils.poll(self.mda_up, timeout=mda_up_timeout, intv=intv)

    def mda_up(self):
        mda = self.cliexe('show mda | match expression "up +up$"')
        return True if mda.strip() else False

    @property
    def primary_config(self):
        """
        Get node primary-config file through classic mode
        """
        pcf = self.send_command("show bof | match primary-config")
        return re.search(r'primary-config +(cf\d.*)\n', pcf).group(1)

    def backup_ftp(self):
        """
        Backup node primary configuration through FTP
        """
        utils.framelog("%s backup configuration via FTP" % self.sysname)
        prcfg = self.primary_config
        if not re.search(r'^cf[123]:', prcfg):
            mylog.info("%s cf[123]: NOT found. aborted!" % self.sysname)
            return
        cfn, cfile = prcfg.split('\\')
        # make backup file name
        bkfile = "%s_%s.%s" % (
            self.sysname, cfile, datetime.now().strftime("%H%M%S"))
        # make backup_dir if not exists
        if not os.path.exists(self.bkup_dir):
            os.makedirs(self.bkup_dir)
        dfile = os.path.join(self.bkup_dir, bkfile)
        # try ftp config file
        try:
            with ftplib.FTP(self.ip) as ftp:
                mylog.info("ftp %s/%s => %s" % (cfn, cfile, dfile))
                ftp.login(self.user, self.pwd)
                ftp.cwd(cfn)
                ftp.retrbinary("RETR %s" % cfile, open(dfile, "wb").write)
        except ConnectionRefusedError:
            mylog.error("%s FTP connection refused!" % self.sysname)

    def backup_xml(self):
        """
        Backup node running configuration through netconf
        """
        if not self.nccon:
            mylog.info("%s netconf inactive. Skip XML backup" % self.sysname)
            return
        utils.framelog("%s backup configuration via NETCONF" % self.sysname)
        # make backup_dirx if not exists
        if not os.path.exists(self.bkup_dirx):
            os.makedirs(self.bkup_dirx)
        # set xml file with full path
        xfile = os.path.join(self.bkup_dirx, "%s.xml" % self.sysname)
        mylog.info("%s XML backup written to: %s" % (self.sysname, xfile))
        with open(xfile, 'w') as f:
            f.write(self.nccon.get_configuration().data_xml)

    def print_xml(self):
        if self.nccon:
            print(self.nccon.get_configuration().data_xml)
        else:
            mylog.info("Yaml file for node %s (%s) does not have netconf:True"
                       % (self.sysname, self.ip))

    def wbx_hv_upgrade(self, cloud_init='v2', copy_onie=None, log=True):
        err = None
        # if no connection exist, try connect
        if self.hv_user and self.hv_pwd:
            mylog.info("HV info found in yaml")
            if not self.telcon:
                mylog.info("HV telnet session NOT exist. Create one")
                self.connect()

            if self.telcon:
                mylog.info("HV telnet session exists")
                mycon = self.telcon
            else:
                err = '%s HV telnet connection NOT exist!' % self.name

            if err:
                mylog.error(err)
                return False

            # Copy correct cloud init
            mylog.info("Copy required cloud-init version")
            if cloud_init == 'v2':
                src = '/vsgx-sd/cloud-init-v2.cfg'
            elif cloud_init == 'v3':
                src = '/vsgx-sd/cloud-init-v3.cfg'
            dst = '/opt/cloud-init.cfg'
            mylog.info("cp %s %s" % (src, dst))
            mycon.sendline('cp %s %s' % (src, dst))
            index = mycon.expect(
                ['overwrite', pexpect.TIMEOUT, pexpect.EOF], timeout=50)
            if index == 0:
                mycon.sendline('y')
                mylog.info("overwrite detected - answer yes")
            else:
                mylog.error("overwrite not detected - index = %s" % (index))

            time.sleep(10)

            src = '/opt/cloud-init.cfg'
            dst = '/vsgx-sd/cloud-init.cfg'

            mylog.info("cp %s %s" % (src, dst))
            mycon.sendline('cp %s %s' % (src, dst))
            index = mycon.expect(
                ['overwrite', pexpect.TIMEOUT, pexpect.EOF], timeout=50)
            if index == 0:
                mycon.sendline('y')
                mylog.info("overwrite detected - answer yes")
            else:
                mylog.error("overwrite not detected - index = %s" % (index))

            time.sleep(10)

            if copy_onie:
                # Copy new omni installer
                mylog.info("Copy required onie version")
                src = copy_onie
                dst = '/opt/onie-installer-x86_64'
                mylog.info("cp %s %s" % (src, dst))
                mycon.sendline('cp %s %s' % (src, dst))
                index = mycon.expect(
                    ['overwrite', pexpect.TIMEOUT, pexpect.EOF], timeout=50)
                if index == 0:
                    mycon.sendline('y')
                    mylog.info("overwrite detected - answer yes")
                else:
                    mylog.error(
                        "overwrite not detected - index = %s" % (index))
                time.sleep(10)

                # Copy new omni installer
                src = '/opt/onie-installer-x86_64'
                dst = '/vsgx-sd/onie-installer-x86_64'
                mylog.info("cp %s %s" % (src, dst))
                mycon.sendline('cp %s %s' % (src, dst))
                index = mycon.expect(
                    ['overwrite', pexpect.TIMEOUT, pexpect.EOF], timeout=50)
                if index == 0:
                    mycon.sendline('y')
                    mylog.info("overwrite detected - answer yes")
                else:
                    mylog.error(
                        "overwrite not detected - index = %s" % (index))
                time.sleep(10)

            # send command
            mylog.info("Send HV reboot command via console")
            mycon.sendline('reboot')
            index = mycon.expect(
                ['The selected entry', pexpect.TIMEOUT, pexpect.EOF],
                timeout=50)
            if index == 0:
                mycon.sendline('\x1b[B')
                mycon.sendline('\r')
                mylog.info("")
                mylog.info("*" * 50)
                mylog.info("")
                mylog.info("Got the select entry prompt")
                mylog.info("Send 1 x down arrow, "
                           "then return to initiate OMNI Install OS")
                mylog.info("")
                mylog.info("*" * 50)
                mylog.info("")
            else:
                mylog.error('%s failed to get select entry prompt' % self.name)
                time.sleep(2)
                mycon.close()
                return False

            # Wait for post reboot indication
            index = mycon.expect(
                ['Welcome to GRUB', pexpect.TIMEOUT, pexpect.EOF], timeout=50)
            if index == 0:
                mylog.info("")
                mylog.info("*" * 50)
                mylog.info("")
                mylog.info("Got post ONIE prompt - Welcome to GRUB")
                mylog.info(
                    "Do nothing, ONIE Install will automatically happen in 5s")
                mylog.info("")
                mylog.info("*" * 50)
                mylog.info("")
            else:
                mylog.error('Failed to get post ONIE prompt - Welcome to GRUB')
                time.sleep(2)
                mycon.close()
                return False

            # close connection since it's a hv initiated upgrade
            time.sleep(2)
            mycon.close()

            return True
        else:
            mylog.error("HV info not found in yaml")
            return False

    def wbx_hv_reboot(self, copy=True, src='/vsgx-sd/ifcfg-mgmt-testing',
                      dst='/etc/sysconfig/network-scripts/ifcfg-mgmt'):
        # if no connection exist, try connect
        if self.hv_user and self.hv_pwd:
            mylog.info("WBX HV info found in yaml")
            if not self.telcon:
                mylog.info(
                    "HV telnet session does not exist. Create one")
                self.connect()
            if self.telcon:
                mylog.info("HV telnet session exists")
                mycon = self.telcon
            else:
                mylog.error('%s HV telnet connection failed' % self.name)
                return False

            if copy:
                # Copy over ifcfg-mgt file with ipv4 bof static
                mylog.info("cp %s %s" % (src, dst))
                mycon.sendline('cp %s %s' % (src, dst))
                index = mycon.expect(
                    ['overwrite', pexpect.TIMEOUT, pexpect.EOF], timeout=50)
                if index == 0:
                    mycon.sendline('y')
                    mylog.info("overwrite detected - answer yes")
                else:
                    mylog.error(
                        "overwrite not detected - index = %s" % (index))

                print(mycon.before.decode("utf-8"))

            # Now reboot HV
            mylog.info("Send WBX HV reboot command via console")
            mycon.sendline('reboot')
            # close connection since it's a hv reboot
            time.sleep(2)
            mycon.close()
            return True

        else:
            mylog.error("WBX HV info not found in yaml")
            return False

    def send_cli_command(self, command):
        cli_output = self.cliexe(command)

        status = 'OK'
        if 'MINOR' in cli_output or 'Error' in cli_output:
            status = 'ERROR'

        return status, cli_output

    def print_cli_port_util(self, port):

        command = 'monitor port ' + port + ' rate interval 3 repeat 1'
        child = pexpect.spawn('ssh %s@%s' % (self.user, self.ip))
        child.timeout = 10
        child.expect('password:')
        child.sendline(self.pwd)
        child.expect(self.prompt)
        child.sendline(command)
        if not self.skipPrompt:
            child.expect(self.prompt)
        cli_return = child.before.decode("utf-8")
        x = cli_return.partition('Utilization')
        z = x[2]
        for char in ['=', '\n', '\r']:
            z = z.replace(char, '')
        z = z.split(':')
        z = z[0]
        for char in ['*', 'A', 'B']:
            z = z.replace(char, '')
        mylog.info("Port {:<36} Input {:<16} Output".format(port, ''))
        mylog.info(z)

    def print_cli_lag_util(self, lag):

        lag = lag.split('-')[1]
        command = 'monitor lag ' + lag + ' rate interval 3 repeat 1'
        child = pexpect.spawn('ssh %s@%s' % (self.user, self.ip))
        child.timeout = 10
        child.expect('password:')
        child.sendline(self.pwd)
        child.expect(self.prompt)
        child.sendline(command)
        if not self.skipPrompt:
            child.expect(self.prompt)

        cli_return = child.before.decode("utf-8")
        a = cli_return.partition('At time t = 3 sec (Mode: Rate)')
        b = a[2]
        for char in ['=']:
            b = b.replace(char, '')

        c = b.partition('* indicates')
        d = c[0]

        mylog.info("Lag %s" % (lag))
        mylog.info("------")
        line1 = "Port-id   Input       Input       Output" +\
                "      Output      Input      Output"
        line2 = "          Bytes       Packets     Bytes" +\
                "       Packets     Errors     Errors"
        mylog.info(line1)
        mylog.info(line2)
        mylog.info(d)

    def get_chassis_type(self):

        # Gets and returns the chassis type of an Timos node
        #

        mib_1 = 'tmnxChassisType'
        mib_2 = 'tmnxChassisTypeName'

        oid_1 = mib_1 + '.' + str(1)

        snmp_get = self.session.get(oid_1)
        snmp_get_1 = snmp_get.value

        oid_2 = mib_2 + '.' + str(snmp_get_1)
        snmp_get = self.session.get(oid_2)
        snmp_get_2 = snmp_get.value

        return snmp_get_2

    def get_cpm_slot_nums(self):

        # Based on the chassis type return which slots are the CPMs in
        # Returns FALSE for CPM B if chassis does not support 2 x control cards

        chassis = self.get_chassis_type()
        if re.search('SR-7', str(chassis)):
            cpm_a = 6
            cpm_b = 7
        elif re.search('SR-12', str(chassis)):
            cpm_a = 11
            cpm_b = 12
        elif re.search('SR-12e', str(chassis)):
            cpm_a = 10
            cpm_b = 11
        elif re.search('SR-a8', str(chassis)):
            cpm_a = 3
            cpm_b = 4
        elif re.search('VSG', str(chassis)):
            cpm_a = 2
            cpm_b = 'FALSE'
        elif re.search('WBX', str(chassis)):
            cpm_a = 2
            cpm_b = 'FALSE'
        elif re.search('IXR-6', str(chassis)):
            cpm_a = 6
            cpm_b = 7
        elif re.search('VSR-I', str(chassis)):
            cpm_a = 2
            cpm_b = 'FALSE'
        elif re.search('SR-a4', str(chassis)):
            cpm_a = 2
            cpm_b = 3
        elif re.search('SR-1', str(chassis)):
            cpm_a = 2
            cpm_b = 'FALSE'
        elif re.search('IXR-s', str(chassis)):
            cpm_a = 2
            cpm_b = 'FALSE'
        elif re.search('7210 SAS-VC', str(chassis)):
            cpm_a = 9
            cpm_b = 10
        else:
            print("ERROR: Currently unsupported node of %s at ip %s"
                  % (chassis, self))
            cpm_a = 'FALSE'
            cpm_b = 'FALSE'

        return cpm_a, cpm_b

    def get_cpm_slot_status(self):

        # Returns the status of the CPMs
        # If this can't be determined - unknown is returned
        #

        cpm_a_status = 'unknown'
        cpm_b_status = 'unknown'

        # Based on the chassis types, which slots are the CPMs in
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Check which CPM is active
        mib_1 = 'tmnxCpmCardRedundant'
        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)

        snmp_get = self.session.get(oid_1)
        cpm_a_status = snmp_get.value
        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        snmp_get = self.session.get(oid_2)
        cpm_b_status = snmp_get.value

        return cpm_a_status, cpm_b_status

    def get_active_cpm_slot_num(self):
        """
        Return: slot number of the active CPM
                or "unknown"
        """
        active_cpm = 'unknown'
        # Based on the chassis types, which slots are the CPMs in
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Check which CPM is active
        mib_1 = 'tmnxCpmCardRedundant'
        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)

        snmp_get = self.session.get(oid_1)
        status_cpm_a = snmp_get.value
        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        snmp_get = self.session.get(oid_2)
        status_cpm_b = snmp_get.value

        if (str(status_cpm_a) == 'redundantActive'):
            active_cpm = cpm_a
        elif (str(status_cpm_a) == 'singleton'):
            active_cpm = cpm_a
        elif (str(status_cpm_b) == 'redundantActive'):
            active_cpm = cpm_b
        elif (str(status_cpm_b) == 'singleton'):
            active_cpm = cpm_b
        else:
            print("ERROR: Neither CPMs are active!")

        return active_cpm

    def get_active_cpm(self):

        active_cpm = 'unknown'

        # Based on the chassis types, which slots are the CPMs in
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Check which CPM is active
        mib_1 = 'tmnxCpmCardRedundant'
        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)

        snmp_get = self.session.get(oid_1)
        status_cpm_a = snmp_get.value
        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        snmp_get = self.session.get(oid_2)
        status_cpm_b = snmp_get.value

        if (str(status_cpm_a) == 'redundantActive'):
            active_cpm = 'A'
        elif (str(status_cpm_a) == 'singleton'):
            active_cpm = 'A'
        elif (str(status_cpm_b) == 'redundantActive'):
            active_cpm = 'B'
        elif (str(status_cpm_b) == 'singleton'):
            active_cpm = 'B'
        else:
            print("ERROR: Neither CPMs are active!")

        return active_cpm

    def check_for_valid_standby_cpm(self):
        """
        Check standby CPM in redundant standby state

        Return: True -- If standby exists and in redundant state
                False -- Otherwise
        """
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Check which CPM is active
        mib_1 = 'tmnxCpmCardRedundant'
        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)

        snmp_get = self.session.get(oid_1)
        status_cpm_a = snmp_get.value

        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        snmp_get = self.session.get(oid_2)
        status_cpm_b = snmp_get.value

        if (str(status_cpm_a) == 'redundantStandby'):
            valid_standby_cpm = 'TRUE'
        elif (str(status_cpm_b) == 'redundantStandby'):
            valid_standby_cpm = 'TRUE'
        else:
            valid_standby_cpm = 'FALSE'

        return valid_standby_cpm

    def wait_for_valid_standby_cpm(self, wait):

        count = 0
        valid_standby_cpm = 'FALSE'
        mib_1 = 'tmnxCpmCardRedundant'
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)
        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        mylog.info("Wait up to %s seconds for valid standby" % (wait))
        while valid_standby_cpm == 'FALSE':
            if count == wait:
                mylog.info("No valid standby after %s seconds " % (count))
                return 'ERROR'

            else:
                snmp_get = self.session.get(oid_1)
                status_cpm_a = snmp_get.value

                oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

                snmp_get = self.session.get(oid_2)
                status_cpm_b = snmp_get.value

                if (str(status_cpm_a) == 'redundantStandby'):
                    valid_standby_cpm = 'TRUE'
                elif (str(status_cpm_b) == 'redundantStandby'):
                    valid_standby_cpm = 'TRUE'
                else:
                    valid_standby_cpm = 'FALSE'

                count = count + 1
                time.sleep(1)
        mylog.info("Valid standby after %s seconds " % (count))

        return 'OK'

    def get_standby_cpm_slot_num(self):
        """
        Return: slot number of active CPM
                or "unknown"
        """
        standby_cpm = 'unknown'
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Check which CPM is active
        mib_1 = 'tmnxCpmCardRedundant'
        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)

        snmp_get = self.session.get(oid_1)
        status_cpm_a = snmp_get.value

        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        snmp_get = self.session.get(oid_2)
        status_cpm_b = snmp_get.value

        if (str(status_cpm_a) == 'redundantStandby'):
            standby_cpm = cpm_a
        elif (str(status_cpm_b) == 'redundantStandby'):
            standby_cpm = cpm_b
        else:
            standby_cpm = 'unknown'

        return standby_cpm

    def get_standby_cpm(self):
        """
        Return: slot number of standby CPM
                or "unknown"
        """
        standby_cpm = 'unknown'
        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Check which CPM is active
        mib_1 = 'tmnxCpmCardRedundant'
        oid_1 = mib_1 + "." + str(1) + "." + str(cpm_a) + "." + str(1)

        snmp_get = self.session.get(oid_1)
        status_cpm_a = snmp_get.value

        oid_2 = mib_1 + "." + str(1) + "." + str(cpm_b) + "." + str(1)

        snmp_get = self.session.get(oid_2)
        status_cpm_b = snmp_get.value

        if (str(status_cpm_a) == 'redundantStandby'):
            standby_cpm = 'A'
        elif (str(status_cpm_b) == 'redundantStandby'):
            standby_cpm = 'B'
        else:
            standby_cpm = 'unknown'

        return standby_cpm

    def get_standby_cpm_hw_index(self):
        """
        Return: active CPM's SNMP Index
                or "unknown"
        """
        standby_cpm_hw_index = 'unknown'

        valid_standby = self.check_for_valid_standby_cpm()
        if valid_standby == 'TRUE':

            # Get the standby CPM
            standby_cpm = self.get_standby_cpm_slot_num()

            if standby_cpm != 'unknown':

                mib_1 = 'tmnxCpmCardHwIndex'
                oid_1 = mib_1 + "." + str(1) + "." + \
                    str(standby_cpm) + "." + str(1)

                snmp_get = self.session.get(oid_1)
                standby_cpm_hw_index = snmp_get.value

        return standby_cpm_hw_index

    def get_active_cpm_hw_index(self):
        """ Return active CPM's SNMP Index for other SNMP get/sets
            Return 'unknown' if get_active_cpm_slot_num failed """

        active_cpm_hw_index = 'unknown'

        # Get the active CPM
        active_cpm = self.get_active_cpm_slot_num()

        if active_cpm != 'unknown':
            mib_1 = 'tmnxCpmCardHwIndex'
            oid_1 = mib_1 + "." + str(1) + "." + str(active_cpm) + "." + str(1)

            snmp_get = self.session.get(oid_1)
            active_cpm_hw_index = snmp_get.value

        return active_cpm_hw_index

    def get_active_cpm_sw_version(self):
        """
        Return: active CPM's software version
                or 'unknown'
        """
        active_cpm_sw_version = 'unknown'

        # Get the SNMP index for the active CPM
        active_cpm_hw_index = self.get_active_cpm_hw_index()

        if active_cpm_hw_index != 'unknown':
            mib_1 = 'tmnxHwSoftwareCodeVersion'
            oid_1 = mib_1 + "." + str(1) + "." + str(active_cpm_hw_index)

            snmp_get = self.session.get(oid_1)
            active_cpm_sw_version = snmp_get.value

            active_cpm_sw_version = active_cpm_sw_version[:21]

        return active_cpm_sw_version

    def get_active_cpm_oper_state(self):
        """
        Return: active CPM's software version
                or 'unknown'
        """
        active_cpm_hw_index = 'unknown'
        active_cpm_oper_state = 'unknown'

        # Get the SNMP index for the active CPM
        active_cpm_hw_index = self.get_active_cpm_hw_index()

        if active_cpm_hw_index != 'unknown':
            mib_1 = 'tmnxHwOperState'
            oid_1 = mib_1 + "." + str(1) + "." + str(active_cpm_hw_index)

            snmp_get = self.session.get(oid_1)
            active_cpm_oper_state = snmp_get.value

        return active_cpm_oper_state

    def get_standby_cpm_oper_state(self):

        # Get & return active CPM's software version
        # If h/w index is 'unknown', return 'unknown' for sw version

        standby_cpm_hw_index = 'unknown'
        standby_cpm_oper_state = 'unknown'

        standby_cpm_hw_index = self.get_standby_cpm_hw_index()

        if standby_cpm_hw_index != 'unknown':
            mib_1 = 'tmnxHwOperState'
            oid_1 = mib_1 + "." + str(1) + "." + str(standby_cpm_hw_index)

            snmp_get = self.session.get(oid_1)
            standby_cpm_oper_state = snmp_get.value

        return standby_cpm_oper_state

    def get_standby_cpm_sw_version(self):

        # Get & return active CPM's software version
        # If h/w index is 'unknown', return 'unknown' for sw version

        standby_cpm_hw_index = 'unknown'
        standby_cpm_sw_version = 'unknown'

        standby_cpm_hw_index = self.get_standby_cpm_hw_index()

        if standby_cpm_hw_index != 'unknown':

            mib_1 = 'tmnxHwSoftwareCodeVersion'
            oid_1 = mib_1 + "." + str(1) + "." + str(standby_cpm_hw_index)

            snmp_get = self.session.get(oid_1)
            standby_cpm_sw_version = snmp_get.value

            standby_cpm_sw_version = standby_cpm_sw_version[:19]

        return standby_cpm_sw_version

    def reboot_standby_cpm(self):

        result = 'OK'

        # Check for a redundant standby CPM
        redundant_standby = self.check_for_valid_standby_cpm()

        if redundant_standby == 'TRUE':
            mylog.info("Rebooting standby CPM")
            # Get the active CPM
            standby_cpm = self.get_standby_cpm_slot_num()

            mib_1 = 'tmnxCpmCardReboot'
            oid_1 = mib_1 + "." + str(1) + "." + \
                str(standby_cpm) + "." + str(1)

            self.session.set(oid_1, 1)

        else:
            mylog.error("No valid redundant standby CPM")
            result = 'ERROR'

        return result

    def switch_active_cpm(self):

        # Perform CPM activity switch - only work if redundant card exists
        # If no valid standby CPM exists, return 'ERROR'

        result = 'OK'

        # Check for a redundant standby CPM
        redundant_standby = self.check_for_valid_standby_cpm()

        if redundant_standby == 'TRUE':
            # Get the active CPM
            active_cpm = self.get_active_cpm_slot_num()

            mib_1 = 'tmnxCpmCardSwitchToRedundantCard'
            oid_1 = mib_1 + "." + str(1) + "." + str(active_cpm) + "." + str(1)

            self.session.set(oid_1, 1)

        else:
            mylog.error("No valid redundant standby CPM")
            result = 'ERROR'

        return result

    def get_chassis_port_id_scheme(self):

        # Gets and returns the chassis type of an Timos node
        #

        mib_1 = 'tmnxChassisPortIdScheme'

        oid_1 = mib_1 + '.' + str(1)

        snmp_get = self.session.get(oid_1)
        port_id_scheme = snmp_get.value

        return port_id_scheme

    def check_for_hw_errors(self):

        result = 'OK'
        fcs_dict = {}
        al_dict = {}

        if not self.sysname:
            self.sysname = self.get_system_name()

        fcs_table = 'dot3StatsFCSErrors'
        fcs_items = self.session.walk(fcs_table)

        al_table = 'dot3StatsAlignmentErrors'
        al_items = self.session.walk(al_table)

        for f_item in fcs_items:
            if f_item.value != '0':
                result = 'ERROR'
                fcs_dict[f_item.oid_index] = f_item.value

        for a_item in al_items:
            if a_item.value != '0':
                al_dict[a_item.oid_index] = a_item.value

        for fp in fcs_dict.keys():
            fp_name = self.session.get('tmnxPortName.1.' + fp)
            mylog.error('Node %s (%s) port %s FCS Errors = %s' %
                        (self.sysname, self.ip, fp_name.value, fcs_dict[fp]))

        for ap in al_dict.keys():
            ap_name = self.session.get('tmnxPortName.1.' + ap)
            mylog.error('Node %s (%s) port %s Alignment Errors = %s' %
                        (self.sysname, self.ip, ap_name.value, al_dict[ap]))

        return result

    def clear_all_stats(self):

        slot = int(1)
        slot_list = []

        # Get number of slots in a chassis
        num_slots = self.session.get('tmnxChassisNumSlots.1')
        num_slots = int(num_slots.value)

        # Put in a list
        while slot <= num_slots:
            slot_list.append(slot)
            slot += 1

        cpm_a, cpm_b = self.get_cpm_slot_nums()

        # Remove CPMs from list
        if cpm_a != 'FALSE':
            slot_list.remove(cpm_a)
        if cpm_b != 'FALSE':
            slot_list.remove(cpm_b)

        # Clear stats for every IOM slot
        for clear_slot in slot_list:
            self.send_cli_command('/clear port %s statistics' % (clear_slot))

    def shutdown_log_98(self):
        return self.cliexe('/configure log log-id 98 shutdown')

    def no_shutdown_log_98(self):
        return self.cliexe('/configure log log-id 98 no shutdown')

    def clear_log_99(self):
        return self.cliexe('/clear log 99')

    def show_log_99(self):
        return self.cliexe('show log log-id 99 ascending')

    def show_bof(self):
        return self.cliexe('show bof')

    def take_tech_support(self):

        file_trail = time.time()

        chassis_type = self.get_chassis_type()
        mylog.info('Taking tech support on %s' % (self.ip))

        child = pexpect.spawn('ssh %s@%s' % (self.user, self.ip))
        child.timeout = 300
        child.expect('password:')
        child.sendline(self.pwd)
        child.expect(self.prompt)

        child.sendline('/admin enable-tech')
        if 'Nuage' in chassis_type:
            cf = 'cf1:'
            mylog.info('Tech support = %s / tech-support-%s'
                       % (cf, file_trail))
            child.sendline(
                '/admin tech-support cf1:/tech-support-%s' % (file_trail))
        else:
            cf = 'cf3:'
            child.sendline(
                '/admin tech-support cf3:/tech-support-%s' % (file_trail))

    def ping(self, count=1):
        response = os.system("ping -c %s %s" % (count, self.ip))
        if response == 0:
            mylog.info('Ping to %s was successful' % (self.ip))
            return True
        else:
            mylog.error('Ping to %s was not successful' % (self.ip))
            return False

    def ping6(self, count=1, size=56, gap=1):
        response = os.system("ping6 -c %s -s %s -i %s %s" %
                             (count, size, gap, self.ipv6))
        if response == 0:
            mylog.info('IPv6 Ping to %s was successful' % (self.ipv6))
            return True
        else:
            mylog.error('IPv6 Ping to %s was not successful' % (self.ipv6))
            return False

    def wait_node_up(self, wait):

        count = 0
        node_up = False

        mylog.info("Wait %s seconds for node to respond to ping" % (wait))
        while not node_up:
            if count == wait:
                mylog.info("Node not up after %s seconds " % (count))
                return False
            else:
                if not self.ping():
                    node_up = False
                else:
                    node_up = True

                count += 1
                mylog.info("Count = %s Wait = %s" % (count, wait))
                time.sleep(1)
        mylog.info("Node up after %s seconds " % (count))

        return True

    def wait_node_up2(self, wait):

        count = 0
        node_up = False

        mylog.info("Wait %s seconds for node to respond to ping" % (wait))
        while not node_up:
            if count == wait:
                mylog.info("Node not up after %s seconds " % (count))
                return False
            else:
                if not self.ping():
                    node_up = False
                else:
                    node_up = True

                count += 1
                mylog.info("Count = %s Wait = %s" % (count, wait))
                time.sleep(1)
        mylog.info("Node up after %s seconds " % (count))

        # poll mda up
        return utils.poll(self.mda_up, timeout=200, intv=20)

    def bof_save(self, wait=90):
        count = 0
        if not self.sysname:
            self.sysname = self.get_system_name()

        self.session.set('ssiSaveBof.0', 'doAction', 'i')

        mylog.info("Performing bof save on %s (%s)" % (self.sysname, self.ip))
        while count <= wait:
            if self.session.get('ssiSaveBofResult.0').value == 'success':
                mylog.info("Bof save on %s (%s) successful after %s seconds"
                           % (self.sysname, self.ip, count))
                return True
            else:
                count += 1
                time.sleep(1)
        mylog.error("bof save on %s (%s) was not successful after %s seconds"
                    % (self.sysname, self.ip, count))
        return False

    def check_bof_save(self):
        if self.session.get('ssiSaveBofResult.0').value == 'success':
            mylog.info("bof save on %s (%s) OK" % (self.sysname, self.ip))
            return True
        else:
            mylog.error("bof save on %s (%s) FAILED" % (self.sysname, self.ip))
            return False

    def admin_save(self, wait=90):
        """
        Perform admin save

        Parameters: wait(int) -- max wait time (seconds)
        Return: True|False(bool)
        """
        count = 0
        if not self.sysname:
            self.sysname = self.get_system_name()

        self.session.set('ssiSaveConfig.0', 'doAction', 'i')

        mylog.info("Perform admin save on %s (%s)" % (self.sysname, self.ip))
        while count <= wait:
            if self.session.get('ssiSaveConfigResult.0').value == 'success':
                mylog.info("Admin save successful in %d seconds" % count)
                return True
            else:
                count += 1
                time.sleep(1)
        mylog.error("Admin save Unsuccessful after %d seconds" % count)
        return False

    def admin_save_detail(self, wait=90):
        """
        Perform admin save detail

        Parameters: wait(int) -- max wait time (seconds)
        Return: True|False(bool)
        """
        count = 0
        if not self.sysname:
            self.sysname = self.get_system_name()

        self.session.set('ssiSaveConfigDetail.0', 'true', 'i')
        self.session.set('ssiSaveConfig.0', 'doAction', 'i')
        self.session.set('ssiSaveConfigDetail.0', 'false', 'i')

        mylog.info("Perform admin save detail on %s (%s)" %
                   (self.sysname, self.ip))
        while count <= wait:
            if self.session.get('ssiSaveConfigResult.0').value == 'success':
                mylog.info("Admin save detail successful in %d sec" % count)
                return True
            else:
                count += 1
                time.sleep(1)
        mylog.error("Admin save Unsuccessful after %d seconds" % count)
        return False

    def check_admin_save(self):
        if self.session.get('ssiSaveConfigResult.0').value == 'success':
            mylog.info("Admin save on %s (%s) OK" % (self.sysname, self.ip))
            return True
        else:
            mylog.error("Admin save on %s (%s) FAILED" %
                        (self.sysname, self.ip))
            return False

    def isolate(self):
        mylog.info("Isolate node %s" % (self.ip))
        for px in self.port_dict.keys():
            self.port_dict[px].shutdown(opt='snmp')

    def no_isolate(self):
        mylog.info("No isolate node %s" % (self.ip))
        for px in self.port_dict.keys():
            self.port_dict[px].no_shutdown(opt='snmp')

    def add_port(self, **portd):
        """
        Add port instance in node instance

        Parameters portd(dict) -- port data from testbed.yaml
        """
        mylog.info('Add ports in node instance')
        for pn, pt in portd.items():
            if 'lag' in pt:
                Lag(self, pt, pn)
            else:
                Port(self, pt, pn)

    def get_mem_available(self):
        return (self.session.get('sgiMemoryAvailable.0')).value

    def get_mem_current_total(self):
        return (self.session.get('sgiMemoryPoolAllocated.0')).value

    def get_mem_total_in_use(self):
        return (self.session.get('sgiMemoryUsed.0')).value

    def get_system_name(self):
        return (self.session.get('sysName.0')).value

    def get_service_admin_up_list(self, max=20000):
        svc = 1
        svc_admin_up_list = []
        while svc <= max:
            ssvc = str(svc)
            svc_admin = self.session.get('svcAdminStatus.' + ssvc).value
            if svc_admin == 'up':
                svc_admin_up_list.append(ssvc)
            svc += 1
        return svc_admin_up_list

    def get_service_oper_up_list(self, max=20000):
        svc = 1
        svc_oper_up_list = []
        while svc <= max:
            ssvc = str(svc)
            svc_oper = self.session.get('svcOperStatus.' + ssvc).value
            if svc_oper == 'up':
                svc_oper_up_list.append(ssvc)
            svc += 1
        return svc_oper_up_list

    def get_number_service_admin_up(self, max=20000):
        svc = 1
        svc_admin_up_list = []
        while svc <= max:
            ssvc = str(svc)
            svc_admin = self.session.get('svcAdminStatus.' + ssvc).value
            if svc_admin == 'up':
                svc_admin_up_list.append(ssvc)
            svc += 1
        return len(svc_admin_up_list)

    def get_number_service_oper_up(self, max=20000):
        svc = 1
        svc_oper_up_list = []
        while svc <= max:
            ssvc = str(svc)
            svc_oper = self.session.get('svcOperStatus.' + ssvc).value
            if svc_oper == 'up':
                svc_oper_up_list.append(ssvc)
            svc += 1
        return len(svc_oper_up_list)

    def add_router(self, **routerd):
        """
        Add router instance in node instance

        Parameters routerd(dict) -- router data from testbed.yaml
        """
        mylog.info("Add router in node instance")
        for rn, rd in routerd.items():
            service.Router(self, rn, rd)

    def add_service(self, **serviced):
        """
        Add service instance in node instance

        Parameters serviced(dict) -- service data from testbed.yaml
        """
        mylog.info("Add service in node instance")
        for sn, sd in serviced.items():
            service.Service(self, sn, sd)

    def add_ioms(self, **iomsd):
        """
        Add ioms instance in node instance

        Parameters iomsd(dict) -- iom data from testbed.yaml
        """
        mylog.info("Add ioms in node instance")
        for name, slot in iomsd.items():
            Iom(self, name, slot)

    def add_mdas(self, **mdasd):
        """
        Add mdas instance in node instance

        Parameters mdasd(dict) -- mda data from testbed.yaml
        """
        mylog.info("Add mdas in node instance")
        for name, slot in mdasd.items():
            Mda(self, name, slot)

    def clear_console(self):
        tsvr, line = self.console.split()
        if tsvr == "135.228.2.28" or tsvr == '135.228.0.23':
            return  # skip for RFSIM and 135.228.0.23

        # extract line number from port (remove leading 0)
        line = re.search(r'0?(\d+)$', line[-2:]).group(1)
        conn = pexpect.spawn('telnet %s' % tsvr, timeout=5)
        index = conn.expect(['>', pexpect.TIMEOUT])
        if index == 0:
            mylog.info('>enable')
            conn.sendline('enable\r')
            conn.expect(r'\(enable\)#')
            mylog.info('(enable)#tunnel %s' % line)
            conn.sendline('tunnel %s\r' % line)
            conn.expect(r'\(tunnel.%s\)#' % line)
            if tsvr == '135.228.0.23':
                # ts 135.228.0.23 CLI is different
                mylog.info('(tunnel:%s)#accept' % line)
                conn.sendline('accept\r')
                conn.expect(r'\(tunnel-accept:%s\)#' % line)
                mylog.info('(tunnel-accept:%s)#kill connection' % line)
                conn.sendline('kill connection\r')
                conn.expect(r'\(tunnel-accept:%s\)#' % line)
            else:
                mylog.info('(tunnel-%s)#kill accept connection' % line)
                conn.sendline('kill accept connection\r')
                conn.expect(r'\(tunnel-%s\)#' % line)
            conn.close()
            mylog.info('%s console %s cleared' % (self.name, self.console))
        else:
            mylog.error('telnet terminal-server %s timeout!' % tsvr)
            self.telcon = None
        return

    def set_rssi(self, mobiles=1, cells=1, rssi=127):
        cmd = 'set %s %s %s' % (mobiles, cells, rssi)
        cmdok = cmd+' OK'
        if self.cliexe(cmd, log=False).splitlines()[-1] != cmdok:
            # try cmd again after 5 seconds
            mylog.info('try %s after 5s' % cmd)
            time.sleep(5)
            if self.cliexe(cmd).splitlines()[-1] != cmdok:
                mylog.error('%s error!' % cmd)
                return False
        # set rssi OK, return True
        mylog.info('Wati for 5s after rssi set')
        time.sleep(5)
        return True

    def get_rssi(self, mobile=1, cell=1, matrix=False):
        cmd = 'get %s %s' % (mobile, cell)
        if matrix:
            cmd = 'get_matrix'
        cmdok = cmd+' OK'
        cmdresult = self.cliexe(cmd).splitlines()
        if cmdok in cmdresult[-1]:
            if matrix:
                return cmdresult[-2]
            return cmdresult[-1].split('=')[1]
        # log error and return False
        mylog.error('%s error!' % cmd)
        return False

    def wait_route_match(self, router, route, match, wait):
        count = 0

        self.sysname = self.get_system_name()
        mylog.info("Wait %s seconds for route %s present on node %s router %s"
                   % (wait, route, self.sysname, router))
        while count <= wait:
            default_result = 'OK'
            res, cli_return = self.send_cli_command(
                'show router %s route-table ipv6 %s' % (router, route))

            if match not in cli_return:
                route_result = False
                mylog.error("Route %s NOT present on %s router %s in %ssec"
                            % (route, self.sysname, router, count))
            else:
                route_result = True

            if route_result:
                mylog.info("Route %s IS present on %s router %s in %ssec"
                           % (route, self.sysname, router, count))
                break
            else:
                count += 1
                time.sleep(1)

        return route_result

    def wait_pim_resolved(self, router, ver, wait):

        count = 0
        self.sysname = self.get_system_name()
        mylog.info("Wait %s seconds for pim to resolve on node %s router %s"
                   % (wait, self.sysname, router))
        while count <= wait:
            res, cli_return = self.send_cli_command(
                'show router %s pim group %s detail | match Resolved'
                % (router, ver))
            if 'Resolved' not in cli_return:
                pim_result = False
                mylog.error("%s pim NOT resolved on node %s router %s in %ssec"
                            % (ver, self.sysname, router, count))
            else:
                pim_result = True

            if pim_result:
                mylog.info("%s pim resolved on node %s router %s in %ssec"
                           % (ver, self.sysname, router, count))
                break
            else:
                count += 1
                time.sleep(1)

        return pim_result

    def wait_isis_adjacency_up(self, router, num_up, wait, instance):
        """
        Check isis adjacency up

        Parameters: router(str) -- router name
                    num_up(int) -- expected number of up isis adjacency
                    wait(int) -- max wait time (seconds)
                    instance(int) -- isis instance
        Return: True -- expected number of isis adjacency comes up
                False -- otherwise
        """
        count = 0
        self.sysname = self.get_system_name()
        mylog.info("Wait %ss for %s ISIS adjacency to come UP on %s router %s"
                   % (wait, num_up, self.sysname, router))
        while count <= wait:
            if router == 'base':
                if instance == 0:
                    cli_return = self.cliexe(
                        'show router isis adjacency | match Up | count')
                else:
                    cli_return = self.cliexe(
                        'show router isis %s adjacency | match Up | count'
                        % instance)
            else:
                cli_return = self.cliexe(
                    'show router %s isis adjacency | match Up | count'
                    % router)
            if str(num_up)+' lines' not in cli_return:
                isis_result = False
                mylog.error("(%s) ISIS adjacency NOT up on %s router %s in %ss"
                            % (num_up, self.sysname, router, count))
            else:
                isis_result = True

            if isis_result:
                mylog.info("(%s) ISIS adjacency UP on %s router %s in %ss"
                           % (num_up, self.sysname, router, count))
                break
            else:
                count += 1
                time.sleep(1)

        return isis_result

    def wait_arp_nd(self, host, router, match, wait):

        count = 0
        self.sysname = self.get_system_name()
        dres, cli_return = self.send_cli_command(
            'show router %s route-table %s | match %s' % (router, host, match))
        mylog.info("Wait %ss for %s for host %s on node %s router %s" % (
            wait, match, self.sysname, host, router))
        while count <= wait:
            res, cli_return = self.send_cli_command(
                'show router %s route-table %s | match %s'
                % (router, host, match))
            if match not in cli_return:
                arp_nd_result = False
                mylog.error("Host %s NOT seen as %s in router %s on %s in %ss"
                            % (host, match, router, self.sysname, count))
            else:
                arp_nd_result = True
                pim_result = True

            if arp_nd_result:
                mylog.info("Host %s seen as %s in router %s on %s in %ss"
                           % (host, match, router, self.sysname, count))
                break
            else:
                count += 1
                time.sleep(1)

        return arp_nd_result

    def wait_vpls_mac(self, service, mac, wait):
        count = 0
        self.sysname = self.get_system_name()
        res, cli_return = self.send_cli_command(
            'show service id %s fdb detail | match %s' % (service, mac))
        mylog.info("Wait up to %s seconds for MAC %s on node %s vpls %s"
                   % (wait, mac, self.sysname, service))

        while count <= wait:
            res, cli_return = self.send_cli_command(
                'show service id %s fdb detail | match %s' % (service, mac))
            if mac not in cli_return:
                mac_result = False
                mylog.error("MAC %s NOT seen on %s vpls %s after %s seconds"
                            % (mac, self.sysname, service, count))
            else:
                mac_result = True

            if mac_result:
                mylog.info("MAC %s seen on %s vpls %s after %s seconds"
                           % (mac, self.sysname, service, count))
                break
            else:
                count += 1
                time.sleep(1)

        return mac_result

    def is_vrrp_master(self, interface, router):
        """
        Parameters: interface(str) -- router interface
                    router(int) -- router instance
        Return: True -- router vrrp instance of interface is Master
                False -- otherwise
        """
        cli_return = self.cliexe(
            'show router %d vrrp instance | match %s' % (router, interface))
        if 'Master' in cli_return:
            return True
        return False

    def flap_vprn(self, vprn, flap_time):

        count = 0
        self.sysname = self.get_system_name()
        dres, cli_return = self.send_cli_command(
            '/configure service vprn %s shut' % vprn)
        mylog.info("Shutting down VPRN %s for %ssecs" % (vprn, flap_time))
        while count <= flap_time:
            count += 1
            time.sleep(1)
        dres, cli_return = self.send_cli_command(
            '/configure service vprn %s no shut' % vprn)
        mylog.info("No Shut VPRN %s" % (vprn))

        return True

    def flap_bgp(self, vprn, flap_time):

        count = 0
        self.sysname = self.get_system_name()

        if vprn != 0:
            dres, cli_return = self.send_cli_command(
                '/configure service vprn %s bgp shut' % vprn)
            mylog.info("Shutting down BGP in VPRN %s for %ssecs"
                       % (vprn, flap_time))
        else:
            # VPRN = 0 means shut BGP in base routing
            dres, cli_return = self.send_cli_command(
                '/configure router bgp shut')
            mylog.info("Shutting down base routing BGP for %s secs"
                       % (flap_time))

        # Wait for flap_time secs before no shutting
        while count <= flap_time:
            count += 1
            time.sleep(1)

        if vprn != 0:
            dres, cli_return = self.send_cli_command(
                '/configure service vprn %s bgp no shut' % vprn)
            mylog.info("No Shut BGP in VPRN %s" % (flap_time))
        else:
            # VPRN = 0 means no shut BGP in base routing
            dres, cli_return = self.send_cli_command(
                '/configure router bgp no shut')
            mylog.info("No Shut BGP in base routing")

        return True

    def l2_silent_failure(self, filter, flap_time):

        count = 0
        self.sysname = self.get_system_name()
        dres, cli_return = self.send_cli_command(
            '/configure filter ipv6-filter %s default-action drop' % filter)
        mylog.info("Shutting filter %s for %s secs " % (filter, flap_time))
        while count <= flap_time:
            count += 1
            time.sleep(1)
        dres, cli_return = self.send_cli_command(
            '/configure filter ipv6-filter %s default-action forward' % filter)
        mylog.info("No Shut filter %s" % (filter))

        return True

    def verify_bgp_underlay(self, filter, wait):

        self.sysname = self.get_system_name()
        match = 'VpnIPv6'
        count = 0

        mylog.info("Wait up to %ss for BGP Neighbor %s to be UP on router %s"
                   % (wait, filter, self.sysname))
        while count <= wait:
            dres, cli_return = self.send_cli_command(
                'show router bgp summary | match %s post-lines 1' % filter)
            if match not in cli_return:
                isis_result = False
                mylog.error("BGP Neighbor (%s) NOT established on %s in %ss"
                            % (filter, self.sysname, count))
            else:
                isis_result = True

            if isis_result:
                mylog.info("BGP Neigbor (%s) established on %s in %ss"
                           % (filter, self.sysname, count))
                break
            else:
                count += 1
                time.sleep(1)

        return isis_result

    def verify_mda_state(self, iom, mda):

        self.sysname = self.get_system_name()
        dres, cli_return = self.send_cli_command(
            'show mda %s/%s' % (iom, mda))
        match = 'failed'
        if match in cli_return:
            return False
        else:
            return True

    def __iter__(self):
        """
        Return NodeIterator with a list of port instances
        """
        self.port_list = [*self.port_dict.values()]
        return NodeIterator(self)


class NodeIterator:
    """
    Implement Node iterator
    """

    def __init__(self, node):
        self._nd = node
        self._index = 0

    def __next__(self):
        if self._index < len(self._nd.port_list):
            self._index += 1
            return self._nd.port_list[self._index - 1]
        raise StopIteration


class Iom(object):

    def __init__(self, ndobj, name, slot):
        self.ip = ndobj.ip
        self.session = ndobj.session
        self.sysname = ndobj.sysname
        self.node = ndobj
        self.name = name
        self.iom_idx = None
        self.slot_num = slot
        setattr(ndobj, name, self)

    def get_iom_hw_index(self):

        iom_hw_index = 'unknown'

        mib_1 = 'tmnxCardHwIndex'
        oid_1 = mib_1 + "." + str(1) + "." + str(self.slot_num)

        snmp_get = self.session.get(oid_1)
        iom_hw_index = snmp_get.value

        self.iom_idx = iom_hw_index
        return iom_hw_index

    def get_iom_oper_state(self):

        mib_1 = 'tmnxHwOperState'
        hw_index = self.get_iom_hw_index()

        oid_1 = mib_1 + "." + str(1) + "." + str(hw_index)

        snmp_get = self.session.get(oid_1)
        iom_oper_state = snmp_get.value

        if (str(iom_oper_state) == '1'):
            iom_oper_state = 'unknown'
        elif (str(iom_oper_state) == '2'):
            iom_oper_state = 'up'
        elif (str(iom_oper_state) == '3'):
            iom_oper_state = 'down'
        elif (str(iom_oper_state) == '4'):
            iom_oper_state = 'diagnosing'
        elif (str(iom_oper_state) == '5'):
            iom_oper_state = 'failed'
        elif (str(iom_oper_state) == '6'):
            iom_oper_state = 'booting'
        elif (str(iom_oper_state) == '7'):
            iom_oper_state = 'empty'
        elif (str(iom_oper_state) == '8'):
            iom_oper_state = 'provisioned'
        elif (str(iom_oper_state) == '9'):
            iom_oper_state = 'unprovisioned'
        elif (str(iom_oper_state) == '10'):
            iom_oper_state = 'upgrade'
        elif (str(iom_oper_state) == '11'):
            iom_oper_state = 'downgrade'
        elif (str(iom_oper_state) == '12'):
            iom_oper_state = 'inServiceUpgrade'
        elif (str(iom_oper_state) == '13'):
            iom_oper_state = 'inServiceDowngrade'
        elif (str(iom_oper_state) == '14'):
            iom_oper_state = 'resetPending'
        elif (str(iom_oper_state) == '15'):
            iom_oper_state = 'softReset'
        elif (str(iom_oper_state) == '16'):
            iom_oper_state = 'preExtension'

        return iom_oper_state

    def get_iom_admin_state(self):

        mib_1 = 'tmnxHwAdminState'
        hw_index = self.get_iom_hw_index()

        oid_1 = mib_1 + "." + str(1) + "." + str(hw_index)

        snmp_get = self.session.get(oid_1)
        iom_admin_state = snmp_get.value

        if (str(iom_admin_state) == '1'):
            iom_admin_state = 'noop'
        elif (str(iom_admin_state) == '2'):
            iom_admin_state = 'up'
        elif (str(iom_admin_state) == '3'):
            iom_admin_state = 'down'
        elif (str(iom_admin_state) == '4'):
            iom_admin_state = 'diagnose'
        elif (str(iom_admin_state) == '5'):
            iom_admin_state = 'operateSwitch'

        return iom_admin_state

    def set_iom_admin_state(self, state):

        result = 'OK'

        mib = 'tmnxHwAdminState'
        hw_index = self.get_iom_hw_index()

        oid = mib + "." + str(1) + "." + str(hw_index)
        mylog.info("Changing admin status of IOM", self.slot_num, "to", state)

        if state == "up":
            self.session.set(oid, '2', 'i')
        elif state == "down":
            self.session.set(oid, '3', 'i')
        else:
            result = 'ERROR'
            mylog.error("ERROR: Illegal state ", state,
                        "passed into <set_iom_admin_state>")

        return result

    def shutdown(self):
        if not self.iom_idx:
            self.iom_idx = self.get_iom_hw_index()
        if not self.sysname:
            self.sysname = self.node.get_system_name()
        mylog.info("Node %s (%s) shutdown IOM %s"
                   % (self.sysname, self.ip, self.slot_num))
        oid = "tmnxHwAdminState" + "." + str(1) + "." + str(self.iom_idx)
        self.session.set(oid, '3', 'i')

    def no_shutdown(self):
        if not self.iom_idx:
            self.iom_idx = self.get_iom_hw_index()
        if not self.sysname:
            self.sysname = self.node.get_system_name()
        mylog.info("Node %s (%s) no shutdown IOM %s"
                   % (self.sysname, self.ip, self.slot_num))
        oid = 'tmnxHwAdminState' + "." + str(1) + "." + str(self.iom_idx)
        self.session.set(oid, '2', 'i')

    def wait_iom_oper_up(self, wait):
        if not self.iom_idx:
            self.get_iom_hw_index()

        count = 0
        oid = 'tmnxHwOperState' + '.' + str(1) + '.' + str(self.iom_idx)

        mylog.info("Wait up to %s seconds for IOM %s to come oper up "
                   % (wait, self.slot_num))
        snmp_get = self.session.get(oid).value

        while snmp_get != 'inService':
            snmp_get = self.session.get(oid).value
            if count == wait:
                mylog.error("IOM %s not oper up after %s seconds "
                            % (self.slot_num, wait))
                return 'ERROR'
            count = count + 1
            time.sleep(1)
        mylog.info("IOM %s oper up after %s seconds " % (self.slot_num, count))
        return 'OK'


class Mda(object):

    def __init__(self, ndobj, name, mda):

        self.ip = ndobj.ip
        self.session = ndobj.session
        self.sysname = ndobj.sysname
        self.node = ndobj
        self.name = name
        self.mda_idx = None
        self.iom_slot_num = mda.split('/')[0]
        self.mda_slot_num = mda.split('/')[1]
        setattr(ndobj, name, self)

    def get_mda_hw_index(self):
        oid_1 = "tmnxMDAHwIndex" + "." + \
            str(1) + "." + str(self.iom_slot_num) + \
            "." + str(self.mda_slot_num)
        self.mda_idx = self.session.get(oid_1).value
        return self.mda_idx

    def get_mda_oper_state(self):
        if not self.mda_idx:
            self.mda_idx = self.get_mda_hw_index()
        if not self.sysname:
            self.sysname = self.node.get_system_name()
        state = self.session.get(
            "tmnxHwOperState" + "." + str(1) + "." + str(self.mda_idx)).value
        if state == 'inService':
            state = 'up'
        elif state == 'outOfService':
            state = 'down'
        return state

    def get_mda_admin_state(self):
        if not self.mda_idx:
            self.mda_idx = self.get_mda_hw_index()
        if not self.sysname:
            self.sysname = self.node.get_system_name()
        state = self.session.get(
            "tmnxHwAdminState" + "." + str(1) + "." + str(self.mda_idx)).value
        if state == 'inService':
            state = 'up'
        elif state == 'outOfService':
            state = 'down'
        return state

    def set_mda_admin_state(self, state):

        result = 'OK'
        mib = 'tmnxHwAdminState'
        hw_index = self.get_mda_hw_index()
        oid = mib + "." + str(1) + "." + str(hw_index)
        mylog.info("Changing admin status of MDA %s/%s to %s"
                   % (self.iom_slot_num, self.mda_slot_num, state))

        if state == "up":
            self.session.set(oid, '2', 'i')
        elif state == "down":
            self.session.set(oid, '3', 'i')
        else:
            result = 'ERROR'
            print("ERROR: Illegal state ", state,
                  "passed into <set_iom_admin_state>")
            mylog.info("Illegal state ", state,
                       "passed into <set_iom_admin_state>")

        return result

    def shutdown(self):
        if not self.mda_idx:
            self.mda_idx = self.get_mda_hw_index()
        if not self.sysname:
            self.sysname = self.node.get_system_name()
        mylog.info("Node %s (%s) shutdown MDA %s/%s"
                   % (self.sysname, self.ip, self.iom_slot_num,
                      self.mda_slot_num))
        oid = "tmnxHwAdminState" + "." + str(1) + "." + str(self.mda_idx)
        self.session.set(oid, '3', 'i')

    def no_shutdown(self):
        if not self.mda_idx:
            self.mda_idx = self.get_mda_hw_index()
        if not self.sysname:
            self.sysname = self.node.get_system_name()
        mylog.info("Node %s (%s) no shutdown MDA %s/%s"
                   % (self.sysname, self.ip, self.iom_slot_num,
                      self.mda_slot_num))
        oid = 'tmnxHwAdminState' + "." + str(1) + "." + str(self.mda_idx)
        self.session.set(oid, '2', 'i')

    def wait_mda_oper_up(self, wait):
        if not self.mda_idx:
            self.get_mda_hw_index()

        count = 0
        oid = 'tmnxHwOperState' + '.' + str(1) + '.' + str(self.mda_idx)

        mylog.info("Wait up to %s seconds for MDA %s to come oper up "
                   % (wait, self.mda_slot_num))
        snmp_get = self.session.get(oid).value

        while snmp_get != 'inService':
            snmp_get = self.session.get(oid).value
            if count == wait:
                print("ERROR: MDA %s not oper up after %s seconds"
                      % (self.mda_slot_num, wait))
                return 'ERROR'
            count = count + 1
            time.sleep(1)
        mylog.info("MDA %s oper up after %s seconds"
                   % (self.mda_slot_num, count))
        return 'OK'


class Port(object):

    def __init__(self, cpm_obj, port, name):

        self.ip = cpm_obj.ip
        self.sysname = cpm_obj.sysname
        self.node = cpm_obj
        self.port = port
        self.name = name
        self.port_idx = None
        self.session = cpm_obj.session

        setattr(cpm_obj, name, self)
        # Add port object to parent CPM's port dictionary
        cpm_obj.port_dict[name] = self

    def set_port_idx(self):

        # Poll the node for the tmnxChassisPortIdScheme
        mib_1 = 'tmnxChassisPortIdScheme'
        oid_1 = mib_1 + '.' + str(1)
        snmp_get = self.session.get(oid_1)
        port_id_scheme = snmp_get.value

        if (str(port_id_scheme) == '1'):
            self.port_id_scheme = 'schemeA'
        elif (str(port_id_scheme) == '2'):
            self.port_id_scheme = 'schemeB'
        elif (str(port_id_scheme) == '3'):
            self.port_id_scheme = 'schemeC'
        else:
            self.port_id_scheme = 'unknown'

        # Perform SNMP walk on port table to get ifIndex for port 'port'
        table = 'tmnxPortName.1'
        table_items = self.session.walk(table)

        for item in table_items:
            if item.value == self.port:
                self.port_idx = item.oid_index.split('.')[1]

    def get_lag_ports(self):

        if 'lag' in self.port:
            lag_port_list = []
            lag_id = self.port.split('-')[1]

            # Perform SNMP walk on lag table to get the member port names
            table = 'tLagMemberPortName' + '.' + lag_id
            table_items = self.session.walk(table)
            for item in table_items:
                print(item.value)
                lag_port_list.append(item.value)
            return lag_port_list
        else:
            return 'ERROR'

    def get_port_info(self, get_info, verbose=True):
        if not self.port_idx:
            self.set_port_idx()
        if not self.sysname:
            self.sysname = self.node.get_system_name()

        if get_info == 'admin':
            mib = 'tmnxPortAdminStatus'
        elif get_info == 'oper':
            mib = 'tmnxPortOperStatus'
        elif get_info == 'encap':
            mib = 'tmnxPortEncapType'
        elif get_info == 'mode':
            mib = 'tmnxPortMode'
        else:
            mylog.error(
                "Unsupported %s passed-in to get_port_info" % get_info)
            return 'ERROR'

        oid = mib + '.' + str(1) + '.' + str(self.port_idx)
        snmp_get = self.session.get(oid).value

        if get_info == 'admin' or get_info == 'oper':
            # Map MIB value to those used in CLI
            #
            if snmp_get == 'inService':
                return_info = 'up'
            elif snmp_get == 'outOfService':
                return_info = 'down'
            else:
                return_info = snmp_get

        elif get_info == 'encap':
            # Map MIB value to those used in CLI
            #
            if snmp_get == 'qEncap':
                return_info = 'dot1q'
            elif snmp_get == 'nullEncap':
                return_info = 'null'
            elif snmp_get == 'qinqEncap':
                return_info = 'qinq'
            else:
                return_info = snmp_get

        elif get_info == 'mode':
            return_info = snmp_get
        else:
            return_info = snmp_get

        # Allan
        if verbose:
            mylog.info("Node %s (%s) port %s is %s %s"
                       % (self.sysname, self.ip, self.port,
                          get_info, return_info))

        return return_info

    def wait_port_oper_up(self, wait):
        if not self.port_idx:
            self.set_port_idx()
        if not self.sysname:
            self.sysname = self.node.get_system_name()

        count = 0
        oid = 'tmnxPortOperStatus' + '.' + str(1) + '.' + str(self.port_idx)

        mylog.info("Wait %s seconds for node %s port %s to come up"
                   % (wait, self.ip, self.port))
        snmp_get = self.session.get(oid).value

        while snmp_get != 'inService':
            snmp_get = self.session.get(oid).value
            if count == wait:
                mylog.error("Node %s port %s NOT oper up in %ss"
                            % (self.ip, self.port, count))
                return 'ERROR'
            count += 1
            time.sleep(1)
        mylog.info("Node %s port %s oper up after %s seconds"
                   % (self.ip, self.port, count))
        return 'OK'

    def wait_port_oper_up_ex(self, wait):
        if not self.port_idx:
            self.set_port_idx()
        if not self.sysname:
            self.sysname = self.node.get_system_name()

        count = 0
        oid = 'tmnxPortOperStatus' + '.' + str(1) + '.' + str(self.port_idx)

        mylog.info("Wait upto %ssec for node %s (%s) port %s to be oper up" % (
            wait, self.sysname, self.ip, self.port))
        snmp_get = self.session.get(oid).value

        while snmp_get != 'inService':
            snmp_get = self.session.get(oid).value
            if count == wait:
                mylog.error("Node %s (%s) port %s NOT oper up after %ssec" % (
                    self.sysname, self.ip, self.port, count))
                return False
            count += 1
            time.sleep(1)
        mylog.info("Node %s (%s) port %s oper up after %s seconds"
                   % (self.sysname, self.ip, self.port, count))
        return True

    def wait_port_oper_down(self, wait):
        if not self.port_idx:
            self.set_port_idx()
        if not self.sysname:
            self.sysname = self.node.get_system_name()

        count = 0
        oid = 'tmnxPortOperStatus' + '.' + str(1) + '.' + str(self.port_idx)

        mylog.info("Wait up to %s seconds for port %s to go oper down"
                   % (wait, self.port))
        snmp_get = self.session.get(oid).value

        while snmp_get != 'outOfService':
            snmp_get = self.session.get(oid).value
            if count == wait:
                mylog.error("Port %s NOT oper down after %s seconds"
                            % (self.port, count))
                return 'ERROR'
            count += 1
            time.sleep(1)
        mylog.info("Port %s oper down after %s seconds " % (self.port, count))
        return 'OK'

    def wait_port_oper_down_ex(self, wait):
        if not self.port_idx:
            self.set_port_idx()
        if not self.sysname:
            self.sysname = self.node.get_system_name()

        count = 0
        oid = 'tmnxPortOperStatus' + '.' + str(1) + '.' + str(self.port_idx)

        mylog.info("Wait up to %ss for node %s (%s) port %s to go oper down"
                   % (wait, self.sysname, self.ip, self.port))
        snmp_get = self.session.get(oid).value

        while snmp_get != 'outOfService':
            snmp_get = self.session.get(oid).value
            if count == wait:
                mylog.error("Node %s (%s) port %s NOT oper down after %ss"
                            % (self.sysname, self.ip, self.port, count))
                return False
            count += 1
            time.sleep(1)
        mylog.info("Node %s (%s) port %s oper down after %s seconds"
                   % (self.sysname, self.ip, self.port, count))
        return True

    def set_port_info(self, set_info, set_value, verbose=True):
        if not self.port_idx:
            self.set_port_idx()
        if not self.sysname:
            self.sysname = self.node.get_system_name()

        if set_info == 'admin':
            mib = 'tmnxPortAdminStatus'
        elif set_info == 'encap':
            mib = 'tmnxPortEncapType'
        elif set_info == 'mode':
            mib = 'tmnxPortMode'
        else:
            mylog.error(
                "Unsupported %s passed in to set_port_info" % (set_info))
            return 'ERROR'

        if set_info == 'encap' or set_info == 'mode':
            oid = 'tmnxPortAdminStatus' + "." + \
                str(1) + "." + str(self.port_idx)
            if self.session.get(oid).value == 'inService':
                mylog.error("Cannot change encap or mode on an admin up port")
                return 'ERROR'

        if set_info == 'admin':
            # Map CLI value to those used in MIB
            #
            if set_value == 'up':
                snmp_set = 'inService'
            elif set_value == 'down':
                snmp_set = 'outOfService'
            else:
                mylog.error(
                    "Unsupported %s passed in to set_port_info" % set_value)
                return 'ERROR'

        elif set_info == 'encap':
            # Map CLI value to those used in MIB
            #
            if set_value == 'dot1q':
                snmp_set = 'qEncap'
            elif set_value == 'null':
                snmp_set = 'nullEncap'
            elif set_value == 'qinq':
                snmp_set = 'qinqEncap'
            else:
                snmp_set = set_value

        elif set_info == 'mode':
            snmp_set = set_value
        else:
            snmp_set = set_value

        if verbose:
            mylog.info("Set node %s (%s) port %s to %s %s"
                       % (self.sysname, self.ip, self.port,
                          set_info, set_value))
        oid = mib + "." + str(1) + "." + str(self.port_idx)

        return self.node._snmpset(oid, snmp_set, 'i')

    def set_port_admin_state(self, status):
        if not self.port_idx:
            self.set_port_idx()

        result = 'OK'
        mib = "tmnxPortAdminStatus"

        oid = mib + "." + str(1) + "." + str(self.port_idx)
        mylog.info("Changing admin status of port", self.port, "to", status)

        if status == 'up':
            self.session.set(oid, '2', 'i')
        elif status == 'down':
            self.session.set(oid, '3', 'i')
        else:
            result = 'ERROR'
            mylog.error("Illegal status of ", status,
                        "passed into <set_port_admin_state>")

        return result

    def get_port_admin_state(self):
        if not self.port_idx:
            self.set_port_idx()

        mib = "tmnxPortAdminStatus"

        oid = mib + "." + str(1) + "." + str(self.port_idx)

        snmp_get = self.session.get(oid).value

        if snmp_get == '1':
            return 'noop'
        if snmp_get == '2':
            return 'up'
        elif snmp_get == '3':
            return 'down'
        elif snmp_get == '4':
            return 'diagnose'
        else:
            return 'unknown'

    def get_port_oper_state(self):
        if not self.port_idx:
            self.set_port_idx()

        mib = "tmnxPortOperStatus"

        oid = mib + "." + str(1) + "." + str(self.port_idx)

        snmp_get = self.session.get(oid).value

        if snmp_get == "2":
            return 'up'
        elif snmp_get == "3":
            return 'down'
        else:
            return 'unknown'

    def get_port_encap_type(self):
        if not self.port_idx:
            self.set_port_idx()

        mib = "tmnxPortEncapType"

        oid = mib + "." + str(1) + "." + str(self.port_idx)

        snmp_get = self.session.get(oid).value

        # Map MIB value to those used in CLI
        #
        if snmp_get == 'qEncap':
            encap_type = 'dot1q'
        elif snmp_get == 'nullEncap':
            encap_type = 'null'
        elif snmp_get == 'qinqEncap':
            encap_type = 'qinq'
        else:
            encap_type = snmp_get

        return encap_type

    def set_port_encap_type(self, encap):
        if not self.port_idx:
            self.set_port_idx()

        result = 'OK'

        # First check port is admin down
        # Can only make encap changes to an admin down port
        #

        mib = 'tmnxPortAdminStatus'
        oid = mib + "." + str(1) + "." + str(self.port_idx)
        snmp_get = self.session.get(oid).value

        if snmp_get == '3':
            # As per CLI, allowable values are
            # dot1q | null | qinq

            mib = 'tmnxPortEncapType'

            oid = mib + "." + str(1) + "." + str(self.port_idx)
            mylog.info("Changing encap  of port", self.port, "to", encap)

            if encap == 'null':
                self.session.set(oid, '1', 'i')
            elif encap == 'dot1q':
                self.session.set(oid, '2', 'i')
            elif encap == 'qinq':
                self.session.set(oid, '10', 'i')
            else:
                mylog.error("Illegal encap of ", encap,
                            "passed into <set_port_encap_type>")
        else:
            result = 'ERROR'
            mylog.error("Port is not admin down.  Cannot change encap type")

        return result

    def get_port_mode(self):
        if not self.port_idx:
            self.set_port_idx()

        mib = "tmnxPortMode"

        oid = mib + "." + str(1) + "." + str(self.port_idx)

        snmp_get = self.session.get(oid).value

        return snmp_get

    def set_port_mode(self, mode):
        if not self.port_idx:
            self.set_port_idx()

        result = 'OK'

        # First check port is admin down
        # Can only make mode changes to an admin down port
        #

        mib = 'tmnxPortAdminStatus'
        oid = mib + "." + str(1) + "." + str(self.port_idx)
        snmp_get = self.session.get(oid).value

        if snmp_get == 'outOfService':
            # As per CLI, allowable values are
            # access | hybrid | network

            mib = 'tmnxPortMode'

            oid = mib + "." + str(1) + "." + str(self.port_idx)
            mylog.info("Changing mode  of port", self.port, "to", mode)

            if mode == 'access' or mode == 'hybrid' or mode == 'network':
                self.session.set(oid, mode, 'i')
            else:
                mylog.error("Illegal encap of ", encap,
                            "passed into <set_port_mode>")
        else:
            result = 'ERROR'
            mylog.error("Port is not admin down.  Cannot change encap type")

        return result

    def get_port_rx_octets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCInOctets' + '.' + str(self.port_idx))).value

    def get_port_rx_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifInErrors' + '.' + str(self.port_idx))).value

    def get_port_rx_unicast_utilization(self):
        # MIB is not supported on lags, only ethernet ports
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'tmnxPortEtherUtilStatsInput' + '.' + str(self.port_idx))).value

    def get_port_rx_unicast_packets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCInUcastPkts' + '.' + str(self.port_idx))).value

    def get_port_rx_multicast_packets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCInMulticastPkts' + '.' + str(self.port_idx))).value

    def get_port_rx_broadcast_packets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCInBroadcastPkts' + '.' + str(self.port_idx))).value

    def get_port_rx_packets(self):
        if not self.port_idx:
            self.set_port_idx()

        ucast = self.get_port_rx_unicast_packets()
        mcast = self.get_port_rx_multicast_packets()
        bcast = self.get_port_rx_broadcast_packets()

        return (int(ucast) + int(mcast) + int(bcast))

    def get_port_rx_discards(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifInDiscards' + '.' + str(self.port_idx))).value

    def get_port_rx_unknown_proto(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifInUnknownProtos' + '.' + str(self.port_idx))).value

    def get_port_tx_octets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCOutOctets' + '.' + str(self.port_idx))).value

    def get_port_tx_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifOutErrors' + '.' + str(self.port_idx))).value

    def get_port_tx_unicast_utilization(self):
        # MIB is not supported on lags, only ethernet ports
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'tmnxPortEtherUtilStatsOutput' + '.' + str(self.port_idx))).value

    def get_port_tx_unicast_packets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCOutUcastPkts' + '.' + str(self.port_idx))).value

    def get_port_tx_multicast_packets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCOutMulticastPkts' + '.' + str(self.port_idx))).value

    def get_port_tx_broadcast_packets(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifHCOutBroadcastPkts' + '.' + str(self.port_idx))).value

    def get_port_tx_packets(self):
        if not self.port_idx:
            self.set_port_idx()

        ucast = self.get_port_tx_unicast_packets()
        mcast = self.get_port_tx_multicast_packets()
        bcast = self.get_port_tx_broadcast_packets()

        return (int(ucast) + int(mcast) + int(bcast))

    def get_port_tx_discards(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'ifOutDiscards' + '.' + str(self.port_idx))).value

    def get_port_tx_queue_length(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get('ifOutQLen' + '.' + str(self.port_idx))).value

    # Ethernet-like Medium statistics
    #

    def get_port_alignment_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsAlignmentErrors' + '.' + str(self.port_idx))).value

    def get_port_fcs_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsFCSErrors' + '.' + str(self.port_idx))).value

    def get_port_single_collision(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsSingleCollisionFrames'
            + '.' + str(self.port_idx))).value

    def get_port_multiple_collision(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsMultipleCollisionFrames'
            + '.' + str(self.port_idx))).value

    def get_port_late_collisions(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsLateCollisions' + '.' + str(self.port_idx))).value

    def get_port_excess_collision(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsExcessiveCollisions' + '.' + str(self.port_idx))).value

    def get_port_int_mac_tx_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsInternalMacTransmitErrors'
            + '.' + str(self.port_idx))).value

    def get_port_int_mac_rx_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsInternalMacReceiveErrors'
            + '.' + str(self.port_idx))).value

    def get_port_cse_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsCarrierSenseErrors' + '.' + str(self.port_idx))).value

    def get_port_too_long_frames(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsFrameTooLongs' + '.' + str(self.port_idx))).value

    def get_port_symbol_errors(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3StatsSymbolErrors' + '.' + str(self.port_idx))).value

    def get_port_in_pause_frames(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3InPauseFrames' + '.' + str(self.port_idx))).value

    def get_port_out_pause_frames(self):
        if not self.port_idx:
            self.set_port_idx()
        return (self.session.get(
            'dot3OutPauseFrames' + '.' + str(self.port_idx))).value

    def set_ether_stats_interval(self, itvl=300):

        mib = 'tmnxPortEtherUtilStatsInterval'

        if isinstance(self, Lag):
            for lp in self.port_dict.values():

                if not lp.port_idx:
                    lp.set_port_idx()

                oid = mib + "." + "1" + "." + str(lp.port_idx)
                snmp_set = self.session.set(oid, itvl, 'i')

        else:
            if not self.port_idx:
                self.set_port_idx()
            oid = mib + "." + "1" + "." + str(self.port_idx)
            snmp_set = self.session.set(oid, itvl, 'i')

    def get_util_perc(self, txrx):

        txrx_util = {}
        p_count = 1

        # TODO
        # Why does the SRa4 return different results?
        # Bug on the a4 ??

        if txrx == 'rx':
            mib = 'tmnxPortEtherUtilStatsInput'
        elif txrx == 'tx':
            mib = 'tmnxPortEtherUtilStatsOutput'

        if isinstance(self, Lag):
            for lp in self.port_dict.values():

                if not lp.port_idx:
                    lp.set_port_idx()

                oid = mib + "." + "1" + "." + str(lp.port_idx)

                snmp_get = self.session.get(oid)
                temp = snmp_get.value
                txrx_util[p_count] = int(snmp_get.value)
                p_count += 1

            txrx_sum = sum(txrx_util.values())
            txrx_num = len(txrx_util)
            if int(txrx_num) != 0:
                txrx_util_perc = float(txrx_sum) / int(txrx_num)
                txrx_util_perc = float(txrx_util_perc) / 100
            else:
                txrx_util_perc = 0

        else:
            if not self.port_idx:
                self.set_port_idx()
            oid = mib + "." + "1" + "." + str(self.port_idx)
            snmp_get = self.session.get(oid)
            txrx_util_perc = int(snmp_get.value) / 100

        return txrx_util_perc

    def get_util_perc_dict(self, txrx):

        txrx_util = {}
        p_count = 1
        txrx_list = []

        # TODO
        # Why does the SRa4 return different results?
        # Bug on the a4 ??

        if txrx == 'rx':
            mib = 'tmnxPortEtherUtilStatsInput'
        elif txrx == 'tx':
            mib = 'tmnxPortEtherUtilStatsOutput'
        if isinstance(self, Lag):
            for lp in self.port_dict.values():

                if not lp.port_idx:
                    lp.set_port_idx()

                x = str(lp.port)

                oid = mib + "." + "1" + "." + str(lp.port_idx)

                snmp_get = self.session.get(oid)
                txrx_util[x] = int(snmp_get.value) / 100
                p_count += 1

            txrx_sum = sum(txrx_util.values())
            txrx_num = len(txrx_util)
            txrx_util_perc = int(txrx_sum) / int(txrx_num)
            y = str(self.port)
            txrx_util[y] = int(snmp_get.value) / 100

        else:
            if not self.port_idx:
                self.set_port_idx()
            oid = mib + "." + "1" + "." + str(self.port_idx)
            y = str(self.port)
            snmp_get = self.session.get(oid)
            txrx_util[y] = snmp_get.value

        return txrx_util

    def get_port_unicast_packet_rate(self, interval=1):
        if not self.port_idx:
            self.set_port_idx()

        interval = int(10) * interval

        rx_mib = "ifHCInUcastPkts"
        tx_mib = "ifHCOutUcastPkts"

        rx_oid = rx_mib + "." + str(self.port_idx)
        tx_oid = tx_mib + "." + str(self.port_idx)

        snmp_rx_get_1 = int(self.session.get(rx_oid).value)
        snmp_tx_get_1 = int(self.session.get(tx_oid).value)

        time.sleep(interval)

        snmp_rx_get_2 = int(self.session.get(rx_oid).value)
        snmp_tx_get_2 = int(self.session.get(tx_oid).value)

        rx_rate = (snmp_rx_get_2 - snmp_rx_get_1) / interval
        tx_rate = (snmp_tx_get_2 - snmp_tx_get_1) / interval

        return rx_rate, tx_rate

    def get_port_unicast_octet_rate(self, interval=1):
        if not self.port_idx:
            self.set_port_idx()

        interval = int(10) * interval

        rx_mib = "ifHCInOctets"
        tx_mib = "ifHCOutOctets"

        rx_oid = rx_mib + "." + str(self.port_idx)
        tx_oid = tx_mib + "." + str(self.port_idx)

        snmp_rx_get_1 = int(self.session.get(rx_oid).value)
        snmp_tx_get_1 = int(self.session.get(tx_oid).value)

        time.sleep(interval)

        snmp_rx_get_2 = int(self.session.get(rx_oid).value)
        snmp_tx_get_2 = int(self.session.get(tx_oid).value)

        rx_rate = (snmp_rx_get_2 - snmp_rx_get_1) / interval
        tx_rate = (snmp_tx_get_2 - snmp_tx_get_1) / interval

        return rx_rate, tx_rate

    def get_port_speed_bps(self):
        if not self.port_idx:
            self.set_port_idx()

        # Gets the operational port speed
        # An estimate of the interface's current bandwidth
        # in units of 1,000,000 bits per second.
        #
        # To return speed in bps - multiply by 1000000

        # For lags this will return the current operational total lag speed
        # If some ports in lag are down - this will reduce the overall port
        # speed

        speed = 'ERROR'
        mib = 'ifHighSpeed'

        speed_oid = mib + '.' + str(self.port_idx)
        speed = int(self.session.get(speed_oid).value) * 1000000

        return speed

    def get_port_speed_bytes_per_sec(self):
        if not self.port_idx:
            self.set_port_idx()

        # Gets the operational port speed
        # An estimate of interface's current bandwidth
        # in units of 1,000,000 bits per second.
        # To return speed in bps - multiply by 1000000

        # For lags this will return the current operational total lag speed
        # If some ports in the lag are down - this will reduce the overall port
        # speed

        speed = 'ERROR'
        mib = 'ifHighSpeed'

        speed_oid = mib + '.' + str(self.port_idx)
        speed = int(self.session.get(speed_oid).value) * 1000000
        speed = int(speed) / 8

        return speed

    def get_port_cellular_info(self, get_info):
        if not self.port_idx:
            self.set_port_idx()

        if get_info == 'network_status':
            mib = 'tmnxCellPortRegistrationStatus'
        elif get_info == 'band':
            mib = 'tmnxCellPortFrequencyBand'
        elif get_info == 'rssi':
            mib = 'tmnxCellPortRssi'
        elif get_info == 'rsrp':
            mib = 'tmnxCellPortRsrp'
        else:
            mylog.error("Unsupported %s passed in" % get_info)
            return 'ERROR'

        oid = mib + '.' + str(self.port_idx)
        snmp_get = self.session.get(oid).value

        print(snmp_get)

        return snmp_get

    def get_network_egress_dropped(self):

        if not self.port_idx:
            self.set_port_idx()

        queue = 1
        queue_dict = {}
        mib_1 = 'tmnxPortNetEgressDroInProfPkts' + \
            '.' + '1' + '.' + self.port_idx + '.'
        mib_2 = 'tmnxPortNetEgressDroOutProfPkts' + \
            '.' + '1' + '.' + self.port_idx + '.'

        while queue <= 8:
            oid_1 = mib_1 + str(queue)
            oid_2 = mib_2 + str(queue)

            val_1 = self.session.get(oid_1).value
            val_2 = self.session.get(oid_2).value

            val = int(val_1) + int(val_2)

            queue_dict[str(queue)] = val

            queue += 1

        return queue_dict

    def get_network_egress_forwarded(self):

        if not self.port_idx:
            self.set_port_idx()

        queue = 1
        queue_dict = {}
        mib_1 = 'tmnxPortNetEgressFwdInProfPkts' + \
                '.' + '1' + '.' + self.port_idx + '.'
        mib_2 = 'tmnxPortNetEgressFwdOutProfPkts' + \
            '.' + '1' + '.' + self.port_idx + '.'

        while queue <= 8:
            oid_1 = mib_1 + str(queue)
            oid_2 = mib_2 + str(queue)

            val_1 = self.session.get(oid_1).value
            val_2 = self.session.get(oid_2).value

            val = int(val_1) + int(val_2)

            queue_dict[str(queue)] = val

            queue += 1

        return queue_dict

    def clear_stats(self):

        # Same as 'clear port x/y/z statistics'
        port_id = "port-id=\"%s\"" % (str(self.port))
        self.session.set('tmnxClearParams.50.1', port_id)
        self.session.set('tmnxClearAction.50.1', 'doAction', 'i')

    # sshanggu
    # get port state via telnet connection

    def getstate(self):
        sout = self.node.cliexe('show port | match "%s "' % self.port)
        pat = r'\b{0} +(up|down) +(yes|no) +(up|down)'.format(self.port)
        for line in sout.splitlines():
            mo = re.search(pat, line, re.IGNORECASE)
            if mo:
                if mo.group(1) == 'Up' and mo.group(3) == 'Up':
                    return 'up'
                else:
                    return 'down'
        return 'ERROR'

    # check port up
    def stateup(self):
        if self.getstate() == 'up':
            mylog.info('port %s up. Pass' % self.port)
            return True
        else:
            mylog.error('port %s NOT up. Fail' % self.port)
            return False

    # show port details
    def getdetail(self, **args):
        cret = self.node.cliexe('show port %s' % self.port, **args)
        if cret == 'ERROR':
            mylog.error('failed to get port info')
            return False
        # parse port info
        return utils.parse_show_port_detail(cret)

    # shutdown port
    def shutdown(self, opt='ssh'):
        if opt == 'snmp':
            self.set_port_info('admin', 'down')
        elif opt == 'netconf':
            self.node.send_command(
                xrpc.pset(self.port, shutdown='true'), protocol=opt)
        elif opt == 'ssh' or opt == 'telnet':
            self.node.send_command('config port %s shutdown' % self.port)
        elif 'cmu' in self.node.name:
            # Linux device
            self.node.cliexe('ifconfig %s down' % self.port)
            self.node.cliexe('ifconfig %s' % self.port)  # show intf
        else:
            mylog.error('Wrong opt: %s' % opt)

    # noshutdow port
    def noshutdown(self, opt='ssh', verbose=True):
        if opt == 'snmp':
            self.set_port_info('admin', 'up', verbose)
        elif opt == 'netconf':
            self.node.send_command(
                xrpc.pset(self.port, shutdown='false'), protocol=opt)
        elif opt == 'ssh' or opt == 'telnet':
            self.node.send_command('config port %s no shutdown' % self.port)
        elif 'cmu' in self.node.name:
            # Linux device
            self.node.cliexe('ifconfig %s up' % self.port)
            self.node.cliexe('ifconfig %s' % self.port)  # show intf
        else:
            mylog.error('Wrong opt: %s' % opt)

    def no_shutdown(self, opt='ssh', verbose=True):
        self.noshutdown(opt=opt, verbose=verbose)

    def clear_host_mda(self):
        print("Clear MDA %s" % (self.mda))
        self.send_cli_command('/clear mda %s', self.mda)

    def check_admin_state(self, state='up', style='classic'):
        adminstate = state in self.node.send_command(
            'show port %s | match "Admin State"' % self.port, style=style)
        if not adminstate:
            mylog.error('%s NOT %s' % (self.port, state))
        return adminstate


class Lag(Port):

    def __init__(self, cpm_obj, lag, name):

        port_num = 1
        self.ip = cpm_obj.ip
        self.sysname = cpm_obj.sysname
        self.node = cpm_obj
        self.port = lag
        self.lag_num = self.port.split('-')[1]
        self.name = name
        self.port_idx = None
        self.port_dict = {}
        self.session = cpm_obj.session

        setattr(cpm_obj, name, self)
        cpm_obj.port_dict[name] = self

        lag_port_list = self.get_ports()

        for lag_port in lag_port_list:
            lag_port_name = 'lag_port_' + str(port_num)
            node_lag_port_name = name + '_' + lag_port_name
            port_obj = Port(cpm_obj, lag_port, node_lag_port_name)
            setattr(self, lag_port_name, port_obj)
            self.port_dict[lag_port_name] = port_obj
            port_num += 1

    def get_ports(self):

        lag_port_list = []
        lag_id = self.lag_num

        # Perform an SNMP walk on the lag table to get the member port names
        table = 'tLagMemberPortName' + '.' + self.lag_num
        table_items = self.session.walk(table)
        for item in table_items:
            lag_port_list.append(item.value)
        return lag_port_list

    def shutdown_one_lag_member(self):

        lag_port = self.port_dict.values()[0]
        lag_port.set_port_info('admin', 'down')

    def no_shutdown_one_lag_member(self):

        lag_port = self.port_dict.values()[0]
        lag_port.set_port_info('admin', 'up')

    def shutdown_two_lag_member(self):

        if len(self.port_dict) > 1:
            lag_port_1 = self.port_dict.values()[0]
            lag_port_1.set_port_info('admin', 'down')
            lag_port_2 = self.port_dict.values()[1]
            lag_port_2.set_port_info('admin', 'down')
        else:
            mylog.error('Lag %s does not have 2 member ports' % (self.name))

    def no_shutdown_two_lag_member(self):
        if len(self.port_dict) > 1:
            lag_port_1 = self.port_dict.values()[0]
            lag_port_1.set_port_info('admin', 'up')
            lag_port_2 = self.port_dict.values()[1]
            lag_port_2.set_port_info('admin', 'up')
        else:
            mylog.error('Lag %s does not have 2 member ports' % (self.name))

    def shutdown_all_lag_members(self):
        for p in self.port_dict.values():
            p.set_port_info('admin', 'down')

    def no_shutdown_all_lag_members(self):
        for p in self.port_dict.values():
            p.set_port_info('admin', 'up')

    def wait_all_lag_members_oper_up(self, wait):
        for p in self.port_dict.values():
            count = 0
            if not self.node.sysname:
                self.node.sysname = self.node.get_system_name()
            while p.get_port_info('oper', verbose=False) != 'up':
                if count == wait:
                    mylog.error("Node %s lag %s port %s NOT oper up in %ss" %
                                (self.node.sysname, self.port, p.port, count))
                    return False
                count += 1
                time.sleep(1)
            mylog.info("Node %s lag %s port %s oper up in %ss " % (
                self.node.sysname, self.port, p.port, count))

        return True


class Interface(object):

    def __init__(self, ip, if_ip):

        self.ip = ip
        self.if_ip = if_ip


class Testbed(object):
    def __init__(self, yamlf, use_ixia=True):
        # load tb.yaml
        fo = os.path.join(os.path.dirname(__file__), '..', 'tests', yamlf)
        with open(fo, 'r') as f:
            yamld = yaml.load(f, Loader=yaml.Loader)

        self.name = 'testbed'
        self.ixia_dict = dict()
        self.node_dict = dict()
        self.tb_name = yamlf.split('.')[0]
        self.bkup_dir = os.path.join(BKPDIR, self.tb_name, TODAY)
        self.bkup_dirx = os.path.join(BKPDIR, self.tb_name, TODAY+'xml')

        # create ixia instance
        if use_ixia and 'ixia' in yamld:
            name = yamld['ixia'].get('name', 'ixnet')
            obj = ixia.IxNetx(**yamld['ixia'])
            self.ixia_dict[name] = obj
            setattr(self, name, obj)

        # create node instances
        if 'nodes' in yamld:
            for name, ndict in yamld['nodes'].items():
                ndict.setdefault('name', name)  # set name if not exists
                obj = Node(**ndict)
                self.node_dict[name] = obj
                setattr(self, name, obj)
                # inject extra attributes in node instance
                setattr(obj, 'bkup_dir', self.bkup_dir)
                setattr(obj, 'bkup_dirx', self.bkup_dirx)

        # set topology name
        if 'topology' in yamld:
            self.name = yamld['topology']['name']

        mylog.info('Testbed object (instance) created!')

    def __iter__(self):
        """
        Return TestbedIterator with a list of node instances
        """
        self.node_list = [*self.node_dict.values()]
        return TestbedIterator(self)


class TestbedIterator:
    """
    Implement Testbed iterator
    """

    def __init__(self, testbed):
        self._tb = testbed
        self._index = 0

    def __next__(self):
        if self._index < len(self._tb.node_list):
            self._index += 1
            return self._tb.node_list[self._index - 1]
        raise StopIteration
