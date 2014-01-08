#!/usr/bin/env python

# Copyright (C) 2013:
#     Gabes Jean, naparuba@gmail.com
#     Pasche Sebastien, sebastien.pasche@leshop.ch
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#


'''
 This script is a check for lookup at memory consumption over ssh without
 having an agent on the other side
'''
import os
import sys
import optparse
import base64
import subprocess
try:
    import paramiko
except ImportError:
    print "ERROR : this plugin needs the python-paramiko module. Please install it"
    sys.exit(2)

# Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    import schecks
except ImportError:
    print "ERROR : this plugin needs the local schecks.py lib. Please install it"
    sys.exit(2)


VERSION = "0.1"
DEFAULT_WARNING = '100'
DEFAULT_CRITICAL = '200'


def get_processes(client):
    # We are looking for a line like 
    #(nap,7320,3384,0.0) /bin/bash
    
    # Beware of the export!
    raw = r"""ps ax -o user,vsz,rss,pcpu,command --columns 10000 | sed -e 1d -e 's/ *\([^ ]*\) *\([^ ]*\) *\([^ ]*\) *\([^ ]*\) */(\1,\2,\3,\4) /'"""
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % raw)
    pss = []
    for line in stdout:
        line = line.strip()
        # If the line is void, pass it
        if not line:
            continue
        
        # We should get the (user,vsz,rss,pcpu) command format
        # We remove the first ()
        line = line[1:]
        meta, cmd = line.split(')', 1)

        # We should remove all kernel based process, we don't care about them
        cmd = cmd.strip()
        if cmd.startswith('['):
            continue
        

        user,vsz,rss,pcpu = meta.split(',')
        
        vsz = int(vsz)
        rss = int(rss)
        pcpu = int(float(pcpu))
        pss.append( (user, vsz, rss, pcpu, cmd) )

    # Before return, close the client
    client.close()
        
    return pss





parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + VERSION)
parser.add_option('-H', '--hostname',
                  dest="hostname", help='Hostname to connect to')
parser.add_option('-i', '--ssh-key',
                  dest="ssh_key_file", help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
parser.add_option('-u', '--user',
                  dest="user", help='remote use to use. By default shinken.')
parser.add_option('-P', '--passphrase',
                  dest="passphrase", help='SSH key passphrase. By default will use void')
parser.add_option('-w', '--warning',
                  dest="warning", help='Warning value for RSS used memory. In MB. Default : 100')
parser.add_option('-c', '--critical',
                  dest="critical", help='Critical value for RSS used memory. In MB. Must be superior to warning value. Default : 200')
# Specific parameters
parser.add_option('-C', '--command',
                  dest="command", help='Command name to match for the check')
parser.add_option('-S', '--sum', action='store_true',
                  dest="sum_all", help='Sum all consomtion of matched processes for the check')



if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    hostname = opts.hostname
    if not hostname:
        print "Error : hostname parameter (-H) is mandatory"
        sys.exit(2)

    command = opts.command
    # Look if we need to sum all value from the process match or not
    sum_all = opts.sum_all
    if sum_all and not command:
        print "Error: the sum option is only valid with a -C option"
        sys.exit(2)

    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    # Try to get numeic warning/critical values
    s_warning  = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL
    warning, critical = schecks.get_warn_crit(s_warning, s_critical)


    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, ssh_key_file, passphrase, user)
    pss = get_processes(client)
    
    # Maybe we failed at getting data
    if not pss:
        print "Error : cannot fetch disks values from host"
        sys.exit(2)

    perfdata = ''
    status = 0 # all is green until it is no more ok :)
    bad_processes = []
    global_sum = 0
    for ps in pss:
        (user, vsz, rss, pcpu, cmd) = ps
        
        # Look if the cmd match out command filter
        if command and command not in cmd:
            continue
        
        #perfdata += '"%s_used_pct"=%s%%;%s%%;%s%%;0%%;100%% "%s_used"=%s;%s;%s;0;%s ' % (mount, used_pct, warning, critical, mount, used, _size_warn, _size_crit, size)
        # If we sum all, we will look at the comparision later
        if sum_all:
            global_sum += rss
            continue
        # And compare to limits
        if rss >= critical*1024:
            status = 2
            bad_processes.append( (cmd, rss) )
            continue

        if rss >= warning*1024:
            if status == 0:
                status = 1
            bad_processes.append( (cmd, rss) )

    if not sum_all:
        if status == 0:
            print "Ok: all processes are in the limits | %s" % (perfdata)
            sys.exit(0)
        if status == 1:
            print "Warning: some processes are not good : %s | %s" % (', '.join( ["%s:%dMB" % (cmd.split(' ')[0], float(rss)/1024) for (cmd, rss) in bad_processes]), perfdata)
            sys.exit(1)
        if status == 2:
            print "Critical: some processes are not good : %s | %s" % (', '.join( ["%s:%dMB" % (cmd.split(' ')[0], float(rss)/1024) for (cmd, rss) in bad_processes]), perfdata)
            sys.exit(2)

    # Ok here we are in sum_all
    perfdata = '"%s_consumtion"=%dMB' % (command, float(global_sum)/1024)
    if global_sum >= critical*1024:
        print 'Critical: the processes %s are too high %dMB | %s' % (command, float(global_sum)/1024, perfdata)
        sys.exit(2)
    
    if global_sum >= warning*1024:
        print "Warning: the processes %s are too high %dMB | %s" % (command, float(global_sum)/1024, perfdata)
        sys.exit(1)

        
    print "OK: the processes %s are good %dMB | %s" % (command, float(global_sum)/1024, perfdata)
    sys.exit(0)
