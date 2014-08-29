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
DEFAULT_WARNING = '10'
DEFAULT_CRITICAL = '60'

NTPQ_PATH=r"""ntpq"""


DEFAULT_DELAY_WARNING = '0.100' # 100 ms
DEFAULT_DELAY_CRITICAL = '0.150' # 150 ms
DEFAULT_OFFSET_WARNING = '0.0025' # 2.5 ms
DEFAULT_OFFSET_CRITICAL = '0.005' # 5ms


def get_ntp_sync(client):
    # We are looking for a line like 
    #     remote           refid      st t when poll reach   delay   offset  jitter
    #==============================================================================
    # 127.127.1.0     .LOCL.          10 l   53   64  377    0.000    0.000   0.001
    # *blabla   blabla                 3 u  909 1024  377    0.366   -3.200   5.268
     
    #raw = r"""/usr/sbin/ntpq -p"""
    raw = "%s -p" % NTPQ_PATH
    stdin, stdout, stderr = client.exec_command("export LC_LANG=C && unset LANG && export PATH=$PATH:/usr/bin:/usr/sbin && %s" % raw)

    errs = ''.join(l for l in stderr)
    if errs:
        print "Error: %s" % errs.strip()
        client.close()
        sys.exit(2)

    ref_delay = None
    for line in stdout:
        line = line.strip()
        # We want the line of the reference only
        if not line or not line.startswith('*'):
            continue
        tmp = [e for e in line.split(' ') if e]
        ref_delay = abs(float(tmp[8])) / 1000
            
    # Before return, close the client
    client.close()

    return ref_delay




def get_chrony_sync(client):
    # We are looking for a line like 
    #Reference ID    : 195.141.190.190 (time.sunrise.net)
    #Stratum         : 3
    #Ref time (UTC)  : Fri Jun 28 09:03:22 2013
    #System time     : 0.000147811 seconds fast of NTP time
    #Last offset     : 0.000177244 seconds
    #RMS offset      : 0.000363876 seconds
    #Frequency       : 26.497 ppm slow
    #Residual freq   : 0.024 ppm
    #Skew            : 0.146 ppm
    #Root delay      : 0.008953 seconds
    #Root dispersion : 0.027807 seconds
    #Update interval : 1024.1 seconds
    #Leap status     : Normal

     
    raw = r"""chronyc tracking"""
    stdin, stdout, stderr = client.exec_command("export LC_LANG=C && unset LANG && %s" % raw)

    errs = ''.join(l for l in stderr)
    if errs:
        print "Error: %s" % errs.strip()
        client.close()
        sys.exit(2)

    delay = offset = None
    for line in stdout:
        line = line.strip()
        tmp = line.split(':')
        
        if len(tmp) != 2:
            continue
        if line.startswith('RMS offset'):
            offset = float(tmp[1].strip().split(' ')[0])
        if line.startswith('Root delay'):
            delay = float(tmp[1].strip().split(' ')[0])

    # Before return, close the client
    client.close()

    return delay, offset






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
                  help='Warning delay for ntp, like 10. couple delay,offset value for chrony '
                  '0.100,0.0025')
parser.add_option('-c', '--critical',
                  dest="critical",
                  help='Warning delay for ntp, like 10. couple delay,offset value for chrony '
                  '0.150,0.005')
parser.add_option('-C', '--chrony',  action='store_true',
                  dest="chrony", help='check Chrony instead of ntpd')
parser.add_option('-n', '--ntpq',
                  dest="ntpq", help="remote ntpq bianry path")


if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    port = opts.port
    hostname = opts.hostname or ''

    ntpq = opts.ntpq
    if ntpq:
        NTPQ_PATH=ntpq

    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    chrony = opts.chrony

    if not chrony:
        # Try to get numeic warning/critical values
        s_warning  = opts.warning or DEFAULT_WARNING
        s_critical = opts.critical or DEFAULT_CRITICAL
        warning, critical = schecks.get_warn_crit(s_warning, s_critical)
    else:
        if opts.warning:
            warning_delay = float(opts.warning.split(',')[0])
            warning_offset = float(opts.warning.split(',')[1])
        else:
            warning_delay = float(DEFAULT_DELAY_WARNING)
            warning_offset = float(DEFAULT_OFFSET_WARNING)
        if opts.critical:
            critical_delay = float(opts.critical.split(',')[0])
            critical_offset = float(opts.critical.split(',')[1])
        else:
            critical_delay = float(DEFAULT_DELAY_CRITICAL)
            critical_offset = float(DEFAULT_OFFSET_CRITICAL)

    
        
    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)

    if not chrony:
        ref_delay = get_ntp_sync(client)

        if not ref_delay:
            print "Warning : There is no sync ntp server"
            sys.exit(1)

        perfdata = "delay=%.2fs;%.2fs;%.2fs;;" % (ref_delay, warning, critical)

        if ref_delay > critical:
            print "Critical: ntp delay is %.2fs | %s" %(ref_delay, perfdata)
            sys.exit(2)
        if ref_delay > warning:
            print "Warning: ntp delay is %.2fs | %s" %(ref_delay, perfdata)
            sys.exit(2)
        print "OK: ntp delay is %.2fs | %s" %(ref_delay, perfdata)
        sys.exit(0)

    else:
        delay, offset = get_chrony_sync(client)

        if not delay or not offset:
            print "Warning : cannot get delay or offset value"
            sys.exit(1)

        perfdata =  "delay=%.2fs;%.2fs;%.2fs;;" % (delay, warning_delay, critical_delay)
        perfdata += "offset=%.4fs;%.4fs;%.4fs;;" % (offset, warning_offset, critical_offset)

        if delay > critical_delay:
            print "Critical: ntp/chrony delay is %.2fs | %s" % (delay, perfdata)
            sys.exit(2)

        if offset > critical_offset:
            print "Critical: ntp/chrony offset is %.4fs | %s" % (offset, perfdata)
            sys.exit(2)

        if delay > warning_delay:
            print "Warning: ntp/chrony delay is %.2fs | %s" % (delay, perfdata)
            sys.exit(2)

        if offset > warning_offset:
            print "Warning: ntp/chrony offset is %.4fs | %s" % (offset, perfdata)
            sys.exit(2)

        print "OK: ntp delay is %.2fs offset is %.4fs | %s" %(delay, offset, perfdata)
        sys.exit(0)
        
