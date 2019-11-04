#!/usr/bin/env python3
##############################################################################
#
# Created by: Sam Shangguan
#
# Description: add methods in some classes
#
##############################################################################
from paramiko.channel import Channel
from pexpect.pty_spawn import spawn
import pexpect
import utils
import time
import re

mylog = utils.get_logger(__name__)


def sshcmd(self, cmd=None, timeout=1, log=True):
    '''
    Send cmd through node ssh session.

    Parameters: cmd(str) -- command string
                timeout(int) -- max time to wait node prompt
                log(boolean) -- log cmd_output if True(default)
    Return: cmd_output
    '''
    if cmd:
        if not hasattr(self, 'prompt'):
            self.prompt = self.sysname + "#"
        mylog.info("%s %s" % (self.prompt, cmd))
        self.send(cmd+"\n")

    # regex pattern sysname or (y/n)?
    pat = r'(:%s.*#)|(\(y/n\)\?)' % self.sysname
    data = str()
    tsec = 0
    while True:
        while self.recv_ready():
            data += self.recv(2048).decode("utf-8")
            tsec = 0
        # check prompt in data
        match = re.search(pat, data)
        if match:
            self.prompt = match.group()
        # end loop if prompt or timeout
        if match or tsec >= timeout:
            break
        tsec += 0.2
        time.sleep(0.2)
    # convert byte to string
    if log:
        mylog.info(data)
    return utils.fmtout(data, cmd)


def mdconf(self, cmd):
    '''
    Send config command through model-driven edit-config global

    Parameters: cmd(str) -- config command string (md style)
    Return: (str) -- config command output
    '''
    self.cmdline('edit-config global', log=False)
    cmdret = self.cmdline(cmd)
    self.cmdline('commit', log=False)
    self.cmdline('quit-config', log=False)
    return cmdret


def setmode(self, mode='classic'):
    '''
    Switch channel to specified configuration mode
    self.mdcli = True if config-mode sets to model-driven
    self.mdcli = False if config-mode sets to classic

    Parameters: mode(str) -- 'classic'(default)|'md'
    '''
    cmd = '/!%s-cli' % (mode)
    prompt = self.cmdline('\r', log=False)

    if mode == 'classic':  # set to classic
        if re.search(r'\[.*\]', prompt):
            mylog.info('#! %s, model-driven => classic' % self.sysname)
            if not re.search(r'\[\]', self.cmdline(cmd)):
                self.cmdline('environment no more', log=False)
                self.mdcli = self.node.mdcli = False
    else:  # set to model-driven
        if not re.search(r'\[.*\]', prompt):
            mylog.info('#! %s, classic => model-driven' % self.sysname)
            if re.search(r'\[\]', self.cmdline(cmd)):
                self.cmdline('environment more false', log=False)
                self.mdcli = self.node.mdcli = True
    mylog.info('#! %s, in %s mode' %
               (self.sysname, 'model-driven' if self.mdcli else 'classic'))


@property
def is_active(self):
    return self.get_transport().is_active()


# add methods in Channel class
Channel.cmdline = sshcmd
Channel.mdconf = mdconf
Channel.setmode = setmode
Channel.is_active = is_active


def telcmd(self, cmd, timeout=40, log=True, prompt=None):
    '''
    Send cmd via telnet session.

    Parameters: cmd(str) -- command string
                timeout(int) -- max time to wait node prompt
                log(boolean) -- log cmd_output if True(default)
    Return: cmd_outputs
    '''
    mylog.info("%s %s" % (self.after.decode("utf-8"), cmd))
    if not prompt:
        prompt = r'(%s)|(\(y/n\)\?)' % self.prompt0  # or (y/n)?
    self.sendline(cmd)
    index = self.expect([prompt, pexpect.TIMEOUT,
                         pexpect.EOF], timeout=timeout)
    if index != 0:
        mylog.error('failed to get prompt %s' % prompt)
        return str()  # return empty string
    data = utils.fmtout(self.before + self.after)
    if log:
        mylog.info(data)
    return data


# add method to pexpect.pty_spawn.spawn class
spawn.cmdline = telcmd
