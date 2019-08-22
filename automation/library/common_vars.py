import os
import sys
import socket
import getpass

# regression common vars
MAILSERVER = "mailhost.alcatel-lucent.com"
MAILSFX = "@nokia.com"
HTMLROOT = '/var/www/html'
MIBDIR = '/automation/mibs'
REGDIR = '/regression'
REGUSER = 'nightly'
TEAMMAIL = str("sam.shangguan.ext{x},"
               "allan.phoenix{x},"
               "tresnja.pesut{x},"
               "jim.hurd{x},"
               "kevin.oriet{x}").format(x=MAILSFX)
# luis.lima_guimaraes
# frederico.collodetti

# running user and host
RUNNER = getpass.getuser()
HOSTNAME = socket.gethostname()
HOSTIP = socket.gethostbyname(HOSTNAME)
USERMAIL = RUNNER + MAILSFX

# derived common vars for log
LOGHOME = os.path.join(HTMLROOT, RUNNER)
KPIDIR = os.path.join(LOGHOME, "kpis")
LOGDIR = os.path.join(LOGHOME, "rrlogs")
BKPDIR = os.path.join(LOGHOME, "backup_config")
URLPFX = os.path.join('http://', HOSTIP, RUNNER)
LSI = len(LOGHOME) + 1

# derived common vars for script files
AUTODIR = os.path.dirname(os.path.dirname(__file__))
REGDATA = os.path.join(AUTODIR, 'regdata.yaml')
