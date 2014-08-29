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
DEFAULT_WARNING = '75%'
DEFAULT_CRITICAL = '90%'
DEFAULT_TEMP_FILE = '/tmp/__check_disks_stats_by_ssh.tmp'

def get_disks_stats(client):
    # We are looking for such lines for the first run:
    #1366283417                                                         <----- current unixtime on distant server
    #ls: cannot access /tmp/__disks_stats6: No such file or directory   <----- there was not previous check
    #cat: /tmp/__disks_stats6: No such file or directory                <----- same here
    #8       0 sda 151460 62629 4598672 2856532 150846 533107 5427936 21591596 0 1039636 24452556  <------- current raw values but we don't really care now
    #8      16 sdb 5062 545 831926 14272 390 383 6184 3724 0 15708 17992

    # After the first one we will have
    #1366283725                                                         <----- current unixtime on distant server
    #1366283423                                                         <----- the modification time of the CHK_FILE, so we know how much time we got between the two checks
    #8       0 sda 151460 62629 4598672 2856532 150880 533151 5428560 21591712 0 1039692 24452672    <--------- This is the old file
    #8      16 sdb 5065 545 832694 14272 390 383 6184 3724 0 15708 17992
    #8       0 sda 152406 62647 4634472 2868264 154112 544512 5545168 21751496 0 1051980 24624184    <--------- So this one is the new one
    #8      16 sdb 5129 546 846198 14564 396 385 6248 3760 0 16032 18320

    # And about the stats:
    #Field 1 -- # of reads issued
    #Field 2 -- # of reads merged, field 6 -- # of writes merged
    #Field 3 -- # of sectors read
    #Field 4 -- # of milliseconds spent reading
    #Field 5 -- # of writes completed
    #Field 7 -- # of sectors written
    #Field 8 -- # of milliseconds spent writing
    #Field 9 -- # of I/Os currently in progress
    #Field 10 -- # of milliseconds spent doing I/Os
    #Field 11 -- weighted # of milliseconds spent doing I/Os 
    
    # Beware of the export!
    raw = 'CHK_FILE=%s;' % DEFAULT_TEMP_FILE
    raw += r"""date +%s;ls -l --time-style=+%s $CHK_FILE | awk '{print $6}';cat $CHK_FILE; egrep ' (x?[shv]d[a-z]*|cciss/c[0-9]+d[0-9]+|emcpower[a-z]+|dm-[0-9]+|VxVM.*) ' < /proc/diskstats | tee $CHK_FILE"""
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % raw)

    errors = [l for l in stderr]
    for line in errors:
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

        # By pass the firt line, we already know about it
        _,_,device,nb_reads,_,nb_sec_read,_,nb_writes,_,nb_sec_write,_,_,io_time,_ = tuple([e for e in line.split(' ') if e])

        if not device in stats:
            stats[device] = []
        stats[device].append( (int(nb_reads), int(nb_sec_read), int(nb_writes), int(nb_sec_write), int(io_time)) )

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
    diff, stats = get_disks_stats(client)
    
    # Maybe we failed at getting data
    if not stats:
        print "Error : cannot fetch disk stats values from host"
        sys.exit(2)

    # We are putting diff into float so we are sure we will have float everywhere
    diff = float(diff)

    perfdata = []
    for (device, v) in stats.iteritems():
        if len(v) < 2:
            # Ok maybe this disk just disapears or pop up, not a problem
            continue
        # First the previous ones
        p_nb_reads, p_nb_sec_read, p_nb_writes, p_nb_sec_write, p_io_time = v.pop(0)
        n_nb_reads, n_nb_sec_read, n_nb_writes, n_nb_sec_write, n_io_time = v.pop(0)

        # We want only positive values, if not, means that ther ewas a problem
        # like a reboot for example, so counters are back to 0
        d_nb_reads = max(0, n_nb_reads - p_nb_reads) / diff
        d_nb_writes = max(0, n_nb_writes - p_nb_writes) / diff
        # 512K sectors from now
        d_nb_sec_read = 512/1024.0 * max(0, n_nb_sec_read - p_nb_sec_read) / diff
        d_nb_sec_write = 512/1024.0 * max(0, n_nb_sec_write - p_nb_sec_write) / diff
        # Ok for this one, the values are in millisec, and we want the % for the last diff period
        d_io_time = min(100.0, (max(0, n_io_time - p_io_time) / diff) / 10)
        
        
        # Ok Now it's what we did all of this : dump the io stats!
        perfdata.append('%s_%s=%dr/s' % (device, "r_by_sec", d_nb_reads))
        perfdata.append('%s_%s=%dw/s' % (device, "w_by_sec", d_nb_writes))
        perfdata.append('%s_%s=%drKB/s' % (device, "rKB_by_sec", d_nb_sec_read))
        perfdata.append('%s_%s=%dwKB/s' % (device, "wKB_by_sec", d_nb_sec_write))
        perfdata.append('%s_%s=%.2f%%' % (device, "util", d_io_time))

    print "OK | %s" % (' '.join(perfdata))
    sys.exit(0)

