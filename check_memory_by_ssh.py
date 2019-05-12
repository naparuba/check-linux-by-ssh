#!/usr/bin/env python2

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

def get_meminfo(client):

    # get raw mem info
    stdin, stdout, stderr = client.exec_command('LC_ALL=C cat /proc/meminfo')

    # init data
    total = used = free = shared = buffed = cached = 0

    # first create a dict 
    meminfo = {}
    for line in stdout:
        raw = filter(None, line.strip().split(" "))
        if len(raw) < 3:
            raw.append("")
        raw[0] = raw[0].replace(":","")

        meminfo[raw[0]] = {
            "value": int(raw[1]),
            "unit": raw[2]
        }

    client.close()

    # get and compute data
    # According to https://access.redhat.com/solutions/406773
    # Note: shared is still there but forced to zero for backward compatibility (no meaning)

    total      = meminfo["MemTotal"]["value"]
    free       = meminfo["MemFree"]["value"]
    used       = total - free
    buffed     = meminfo["Buffers"]["value"]
    cached     = meminfo["Cached"]["value"]
    swap_total = meminfo["SwapTotal"]["value"]
    swap_free  = meminfo["SwapFree"]["value"]
    swap_used  = swap_total - swap_free
    shared     = 0

    return total, used, free, shared, buffed, cached, swap_total, swap_used, swap_free

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
parser.add_option('-m', '--measurement',
                  dest="measurement",action="store_true",default=False,
                  help='Measurement in absolute value of the memory behavior. Absolute value '
                  'currently can not be used as a check')
parser.add_option('-s', '--swap',
                  dest="swap",action="store_true",default=False,
                  help='Enable swap value measurement. Swap value currently can not be used '
                  'as a check')
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
    total, used, free, shared, buffed, cached, swap_total, swap_used, swap_free = get_meminfo(client)
    
    # Maybe we failed at getting data
    if total == 0:
        print "Error : cannot fetch memory values from host"
        sys.exit(2)

    # Ok analyse data
    pct_used = 100 * float(used - buffed - cached) / total
    pct_used = int(pct_used)
    
    d = {'used':used, 'buffered':buffed, 'cached':cached, 'free':free, 'consumed': used - buffed - cached}
    
    perfdata = ''
    for (k,v) in d.iteritems():
        # For used we sould set warning,critical value in perfdata
        _warn, _crit = '', ''
        if k == 'consumed':
            _warn, _crit = str(warning)+'%', str(critical)+'%'
        perfdata += ' %s=%s%%;%s;%s;0%%;100%%' % (k, int(100 * float(v)/total), _warn, _crit)

    # Add swap if required (actually no check supported)
    if opts.swap and swap_total > 0:
        d_swap = {'swap_used':swap_used, 'swap_free':swap_free}
        for (k,v) in d_swap.iteritems():
            ## manage division by zero, this is if the host doesn't have swap
            try:
                perfdata += ' %s=%s%%;;;0%%;100%%' % (k, int(100 * float(v)/swap_total))
            except ZeroDivisionError:
                print('The server either not have swap or that partition isn\'t mounted!')
    
    
    # Add measurement if required (actually no check supported) + total
    if opts.measurement :
        d['total']=total
        for (k,v) in d.iteritems():
            perfdata += ' %s=%sKB;;;0KB;%sKB' % (k+'_abs', v, total) 
        if opts.swap and swap_total > 0:
            d_swap['swap_total']=swap_total
            for (k,v) in d_swap.iteritems():
                perfdata += ' %s=%sKB;;;0KB;%sKB' % (k, v, swap_total) 


    # And compare to limits
    if pct_used >= critical:
        print "Critical : memory consumption is too high %s%% | %s" % (pct_used, perfdata)
        sys.exit(2)

    if pct_used >= warning:
        print "Warning : memory consumption is very high %s%% | %s" % (pct_used, perfdata)
        sys.exit(1)

    print "Ok : memory consumption is %s%% | %s" % (pct_used, perfdata)
    sys.exit(0)

        

