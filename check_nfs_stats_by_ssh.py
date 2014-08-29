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

# Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    import schecks
except ImportError:
    print "ERROR : this plugin needs the local schecks.py lib. Please install it"
    sys.exit(2)


VERSION = "0.1"
DEFAULT_WARNING = '75%'
DEFAULT_CRITICAL = '90%'
DEFAULT_TEMP_FILE = '/tmp/__check_nfs_stats_by_ssh.tmp'

def get_nfs_stats(client):
    # We are looking for such lines for the first run:
    #1366283417                                                         <----- current unixtime on distant server
    #ls: cannot access /tmp/__disks_stats6: No such file or directory   <----- there was not previous check
    #cat: /tmp/__disks_stats6: No such file or directory                <----- same here
    #rc 90566 549905930 2132450813
    #fh 405 0 0 0 0
    #io 1908342383 2129640714
    #th 8 29934764 567650.738 252479.505 49455.931 0.000 22572.536 7989.642 5263.229 4076.437 0.000 11600.839
    #ra 32 43631901 0 0 0 0 0 0 0 0 0 12919491
    #net 2682967197 2490831124 192175293 21225
    #rpc 2682395815 16 16 0 0
    #proc2 18 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    #proc3 22 39 992875652 140854720 536774218 278787144 58 56444593 276675820 66624606 47098 27 0 65531032 81943 54147 515 26810978 9489846 213523510 34 0 1173216
    #proc4 2 0 0
    #proc4ops 40 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    

    # After the first one we will have
    #1366283725                                                         <----- current unixtime on distant server
    #1366283423                                                         <----- the modification time of the CHK_FILE, so we know how much time we got between the two checks
    # BIG PART *2


    #Interesting parts :
    #io 3197575487 677537481
    #io (input/output): <bytes-read> <bytes-written>
    #- bytes-read: bytes read directly from disk
    #- bytes-written: bytes written to disk
    #
    #proc3 22 1 219996357 556065 24059461 43520164 606473 150260668 28056897 545340 198181 3708 0 412742 104649 177365 10 4940 255357 152 3
    #                                                        READ    WRTIE    
    
    # Beware of the export!
    raw = 'CHK_FILE=%s;' % DEFAULT_TEMP_FILE
    raw += r"""date +%s;ls -l --time-style=+%s $CHK_FILE | awk '{print $6}';cat $CHK_FILE; cat /proc/net/rpc/nfsd | tee $CHK_FILE"""
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % raw)

    errors = [l for l in stderr]
    for line in errors:
        if line.startswith('ls:') and line.endswith('No such file or directory'):
            print "OK: the check is initializing"
            sys.exit(3)

    stats = {'io': {'r':[], 'w':[]}, 'proc3': {'r':[], 'w':[]}}
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
        #print line
        if not line:
            continue
        tmp = line.split(' ', 1)
        if tmp[0] == 'io':
            r,w = tuple([int(v) for v in tmp[1].split(' ')])
            stats['io']['r'].append(r)
            stats['io']['w'].append(w)
        if tmp[0] == 'proc3':
            _t = tmp[1].split(' ')
            r = int(_t[7])
            w = int(_t[8])
            stats['proc3']['r'].append(r)
            stats['proc3']['w'].append(w)
             
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
parser.add_option('-w', '--warning',
    dest="warning",
    help='Warning value for physical used memory. In percent. Default : 75%')
parser.add_option('-c', '--critical',
    dest="critical",
    help='Critical value for physical used memory. In percent. Must be '
        'superior to warning value. Default : 90%')


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

    # Try to get numeic warning/critical values
    s_warning  = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL
    warning, critical = schecks.get_warn_crit(s_warning, s_critical)

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    diff, stats = get_nfs_stats(client)
    
    # Maybe we failed at getting data
    if not stats:
        print "Error : cannot fetch cpu stats values from host"
        sys.exit(2)

    #print stats

    # We are putting diff into float so we are sure we will have float everywhere
    diff = float(diff)

    perfdata = []

    # First the B/s
    v = stats['io']
    rs = v['r']
    ws = v['w']
    # Ok only if we got the good len of data
    if len(rs) == len(ws) == 2:
        p_r = rs.pop(0)
        n_r = rs.pop(0)

        p_w = ws.pop(0)
        n_w = ws.pop(0)

        # We want only positive values, if not, means that ther ewas a problem
        # like a reboot for example, so counters are back to 0
        d_r = max(0, n_w - p_w) / diff
        d_w = max(0, n_w - p_w) / diff
        
        # Ok Now it's what we did all of this : dump the io stats!
        perfdata.append('RB_by_s=%dB/s' % d_r)
        perfdata.append('WB_by_s=%dB/s' % d_w)


    v = stats['proc3']
    rs = v['r']
    ws = v['w']
    # Ok only if we got the good len of data
    if len(rs) == len(ws) == 2:
        p_r = rs.pop(0)
        n_r = rs.pop(0)

        p_w = ws.pop(0)
        n_w = ws.pop(0)

        # We want only positive values, if not, means that ther ewas a problem
        # like a reboot for example, so counters are back to 0
        d_r = max(0, n_w - p_w) / diff
        d_w = max(0, n_w - p_w) / diff
        
        # Ok Now it's what we did all of this : dump the io stats!
        perfdata.append('R_by_s=%dR/s' % d_r)
        perfdata.append('W_by_s=%dW/s' % d_w)


    print "OK | %s" % (' '.join(perfdata))
    sys.exit(0)

