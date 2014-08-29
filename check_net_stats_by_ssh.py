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
DEFAULT_TEMP_FILE = '/tmp/__check_net_stats_by_ssh.tmp'

def get_net_stats(client):
    # We are looking for such lines for the first run:
    #1366283417                                                         <----- current unixtime on distant server
    #ls: cannot access /tmp/__disks_stats6: No such file or directory   <----- there was not previous check
    #cat: /tmp/__disks_stats6: No such file or directory                <----- same here
    #tun0: 5264250    7350    0    0    0     0          0         0  1257139    7196    0    0    0     0       0          0   <------- current raw values but we don't really care now
    #lo: 13954299  145920    0    0    0     0          0         0 13954299  145920    0    0    0     0       0          0
    #eth1: 715774062  699787    0    0    0     0          0         0 81419374  557455    0    0    0     0       0          0

    # After the first one we will have
    #1366283725                                                         <----- current unixtime on distant server
    #1366283423                                                         <----- the modification time of the CHK_FILE, so we know how much time we got between the two checks
    #tun0: 5264250    7350    0    0    0     0          0         0  1257139    7196    0    0    0     0       0          0   <------- current raw values but we don't really care now
    #lo: 13954299  145920    0    0    0     0          0         0 13954299  145920    0    0    0     0       0          0 
    #eth1: 715774062  699787    0    0    0     0          0         0 81419374  557455    0    0    0     0       0          0
    #tun0: 5264251    7350    0    0    0     0          0         0  1257139    7196    0    0    0     0       0          0   <------- NEW one
    #lo: 13954299  145920    0    0    0     0          0         0 13954299  145920    0    0    0     0       0          0 
    #eth1: 715774062  699787    0    0    0     0          0         0 81419374  557455    0    0    0     0       0          0

    # Aboutthe fields
    #face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed

   
    # Beware of the export!
    raw = 'CHK_FILE=%s;' % DEFAULT_TEMP_FILE
    raw += r"""date +%s;ls -l --time-style=+%s $CHK_FILE | awk '{print $6}';cat $CHK_FILE; sed 1,2d /proc/net/dev | tee $CHK_FILE"""
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % raw)

    errors = [l for l in stderr]
    for line in errors:
        line = line.strip()
        if line.startswith('ls:') and line.endswith('No such file or directory'):
            print "OK: the check is initializing"
            sys.exit(3)

    stats = {}
    lines = [line for line in stdout]
    if len(lines) < 2:
        print "Error: something goes wrong during the command launch sorry"
        sys.exit(2)
    # We try to get the diff betweenthe file date and now
    now = lines.pop(0)
    before = lines.pop(0)
    diff = int(now) - int(before)

    # Ok such things should not be true on day, but we don't really now
    if diff <= 0:
        diff = 300

    # Let's parse al of this
    for line in lines:
        line = line.strip()
        if not line:
            continue
        tmp = line.split(':', 1)
        ifname = tmp[0]
        # We don't care about lo
        if ifname.startswith('lo'):
            continue
        values = tmp[1]

        # By pass the firt line, we already know about it
        rx_bytes,rx_packets,rx_errs,rx_drop,_,_,_,rx_multicast,tx_bytes, tx_packets, tx_errs, tx_drop,_,_,_,_ = tuple([int(e) for e in values.split(' ') if e])

        if not ifname in stats:
            stats[ifname] = []
        stats[ifname].append( (rx_bytes,rx_packets,rx_errs,rx_drop, rx_multicast,tx_bytes, tx_packets, tx_errs, tx_drop) )

    # Before return, close the client
    client.close()
        
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
    dest="passphrase",
    help='SSH key passphrase. By default will use void')
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
    diff, stats = get_net_stats(client)
    
    # Maybe we failed at getting data
    if not stats:
        print "Error : cannot fetch cpu stats values from host"
        sys.exit(2)

    # We are putting diff into float so we are sure we will have float everywhere
    diff = float(diff)

    perfdata = []
    for (device, v) in stats.iteritems():
        if len(v) < 2:
            # Ok maybe this disk just disapears or pop up, not a problem
            continue
        # First the previous ones
        p_rx_bytes, p_rx_packets, p_rx_errs, p_rx_drop, p_rx_multicast, p_tx_bytes, p_tx_packets, p_tx_errs, p_tx_drop = v.pop(0)
        n_rx_bytes, n_rx_packets, n_rx_errs, n_rx_drop, n_rx_multicast, n_tx_bytes, n_tx_packets, n_tx_errs, n_tx_drop = v.pop(0)

        # We want only positive values, if not, means that ther ewas a problem
        # like a reboot for example, so counters are back to 0
        d_rx_bytes = max(0, n_rx_bytes - p_rx_bytes) / diff / 1024
        d_tx_bytes = max(0, n_tx_bytes - p_tx_bytes) / diff / 1024

        d_rx_packets = max(0, n_rx_packets - p_rx_packets) / diff
        d_tx_packets = max(0, n_tx_packets - p_tx_packets) / diff
        
        d_rx_errs = max(0, n_rx_errs - p_rx_errs) / diff
        d_tx_errs = max(0, n_tx_errs - p_tx_errs) / diff

        d_rx_multicast = max(0, n_rx_multicast - p_rx_multicast) / diff

        d_rx_drop = max(0, n_rx_drop - p_rx_drop) / diff
        d_tx_drop = max(0, n_tx_drop - p_tx_drop) / diff

        # Ok Now it's what we did all of this : dump the io stats!
        # PACKETS
        perfdata.append('%s_%s=%dp/s' % (device, "rx_by_sec", d_rx_packets))
        perfdata.append('%s_%s=%dp/s' % (device, "tx_by_sec", d_tx_packets))
        # BYTES
        perfdata.append('%s_%s=%dKB/s' % (device, "rwKB_by_sec", d_rx_bytes))
        perfdata.append('%s_%s=%dKB/s' % (device, "txKB_by_sec", d_tx_bytes))
        # Multicast
        perfdata.append('%s_%s=%dp/s' % (device, "rx_multicast_by_sec", d_rx_multicast))
        # Errs
        perfdata.append('%s_%s=%dp/s' % (device, "rxErrs_by_sec", d_rx_errs))
        perfdata.append('%s_%s=%dp/s' % (device, "txErrs_by_sec", d_tx_errs))
        # Drop
        perfdata.append('%s_%s=%dp/s' % (device, "rxDrops_by_sec", d_rx_drop))
        perfdata.append('%s_%s=%dp/s' % (device, "txDrops_by_sec", d_tx_drop))




    print "OK | %s" % (' '.join(perfdata))
    sys.exit(0)

