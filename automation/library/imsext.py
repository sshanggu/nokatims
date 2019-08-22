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
import logging
import pexpect
import utils
import time
import re

mylog = logging.getLogger(__name__)
mylog.addHandler(logging.StreamHandler())


def tmpf1(self, cmd=None, timeout=1, log=True):
    """ send cmd via ssh. collect/return outputs """
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


@property
def tmpf3(self):
    return self.get_transport().is_active()


# add methods in Channel class
Channel.cmdline = tmpf1
Channel.is_active = tmpf3


def tmpf2(self, cmd, timeout=40, log=True, prompt=None):
    """ send cmd via telnet. collect/return outputs
        timeout (default 40s) if prompt not expected """
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


# add method tmpf2 in spawn class
spawn.cmdline = tmpf2
