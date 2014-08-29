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

# Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    import schecks
except ImportError:
    print "ERROR : this plugin needs the local schecks.py lib. Please install it"
    sys.exit(2)


VERSION = "0.1"
DEFAULT_TEMP_FILE = '/tmp/__check_kernel_stats_by_ssh.tmp'

def get_kernel_stats(client):
    # We are looking for such lines for the first run:
    #1366283417                                                         <----- current unixtime on distant server
    #ls: cannot access /tmp/__disks_stats6: No such file or directory   <----- there was not previous check
    #cat: /tmp/__disks_stats6: No such file or directory                <----- same here
    #cpu  840802 25337 307315 6694839 157376 3 16239 0 0 0
    #cpu0 212495 5980 75330 1673111 38077 0 4370 0 0 0
    #intr 53421146 45 3 0 0 4 0 3 1 1 0 0 0 4 0 16351 0 1672609 0 201933 1177852 2955202 0 0 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 69827 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    #ctxt 171219536
    #btime 1366876148
    #processes 42956
    #procs_running 1
    #procs_blocked 2
    #softirq 24231851 0 4331903 3491 3371608 425905 0 1697846 3278376 9334 11113388


    # After the first one we will have
    #1366283725                                                         <----- current unixtime on distant server
    #1366283423                                                         <----- the modification time of the CHK_FILE, so we know how much time we got between the two checks
    #cpu  840802 25337 307315 6694839 157376 3 16239 0 0 0
    #cpu0 212495 5980 75330 1673111 38077 0 4370 0 0 0
    #intr 53421146 45 3 0 0 4 0 3 1 1 0 0 0 4 0 16351 0 1672609 0 201933 1177852 2955202 0 0 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 69827 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    #ctxt 171219536
    #btime 1366876148
    #processes 42956
    #procs_running 1
    #procs_blocked 2
    #softirq 24231851 0 4331903 3491 3371608 425905 0 1697846 3278376 9334 11113388
    
    # Beware of the export!
    raw = 'CHK_FILE=%s;' % DEFAULT_TEMP_FILE
    raw += r"""date +%s;ls -l --time-style=+%s $CHK_FILE | awk '{print $6}';cat $CHK_FILE; cat /proc/stat /proc/vmstat| tee $CHK_FILE"""
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % raw)

    errors = [l for l in stderr]
    for line in errors:
        if line.startswith('ls:') and line.endswith('No such file or directory'):
            print "OK: the check is initializing"
            sys.exit(3)

    stats = {'ctxt':[], 'processes':[], 'pgfault':[], 'pgmajfault':[]}
    lines = [line for line in stdout]
    if len(lines) < 2:
        print "Error: something goes wrong during the command launch sorry"
        sys.exit(2)

    # Remember to close the client when finish
    client.close()
        
    # We try to get the diff betweenthe file date and now
    now = lines.pop(0)
    before = lines.pop(0)
    try:
        diff = int(now) - int(before)
    except ValueError:
        print "OK: the check is initializing"
        sys.exit(3)

    # Ok such things should not be true on day, but we don't really now
    if diff <= 0:
        print "OK: the check is initializing"
        diff = 300

    # Let's parse al of this
    for line in lines:
        line = line.strip()
        if not line:
            continue
        tmp = line.split(' ', 1)
        if tmp[0] in ['ctxt', 'processes', 'pgfault', 'pgmajfault']:
             stats[tmp[0]].append(int(tmp[1]))
             
    return diff, stats





parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + VERSION)
parser.add_option('-H', '--hostname',
                  dest="hostname", help='Hostname to connect to')
parser.add_option('-p', '--port',
                  dest="port", type="int", default=22,
                  help='SSH port to connect to. Default : 22')
parser.add_option('-i', '--ssh-key',
                  dest="ssh_key_file",
                  help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
parser.add_option('-u', '--user',
                  dest="user", help='remote use to use. By default shinken.')
parser.add_option('-P', '--passphrase',
                  dest="passphrase", help='SSH key passphrase. By default will use void')


if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    port = opts.port
    hostname = opts.hostname or ''

    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    diff, stats = get_kernel_stats(client)
    
    # Maybe we failed at getting data
    if not stats:
        print "Error : cannot fetch kernel stats values from host"
        sys.exit(2)

    # We are putting diff into float so we are sure we will have float everywhere
    diff = float(diff)

    perfdata = []
    for k in ['ctxt', 'processes', 'pgfault', 'pgmajfault']:
        v = stats[k]
        if len(v) < 2:
            # Ok maybe this value just disapears or pop up, not a problem
            continue
        p_v = v.pop(0)
        n_v = v.pop(0)

        # We want only positive values, if not, means that ther ewas a problem
        # like a reboot for example, so counters are back to 0
        d_v = max(0, n_v - p_v) / diff
        
        # Ok Now it's what we did all of this : dump the io stats!
        perfdata.append('%s_by_s=%d%s/s' % (k, d_v, k))

    print "OK | %s" % (' '.join(perfdata))
    sys.exit(0)

