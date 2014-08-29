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
DEFAULT_WARNING = '0' # There is no warning, only critical
DEFAULT_CRITICAL = '3600'


def get_uptime(client):
    # We are looking for a line like 
    #5265660.84 4856671.67
    raw = r"""cat /proc/uptime"""
    stdin, stdout, stderr = client.exec_command(raw)
    line = [l for l in stdout][0].strip()
    
    uptime, _ = tuple([int(float(v)) for v in line.split(' ')])

    # Before return, close the client
    client.close()

    return uptime






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

parser.add_option('-c', '--critical',
                  dest="critical", help='Critical value for uptime in seconds. Less means critical error. Default : 3600')




if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    hostname = opts.hostname or ''
    port = opts.port
    
    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    # Try to get numeic warning/critical values
    s_warning  = DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL

    _, critical = schecks.get_warn_crit(s_warning, s_critical)
        
    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    uptime = get_uptime(client)

    # Two cases : cpu_based_load or not. For CPU the real warning is based on warning*nb_cpu
    status = 0
    s_pretty_uptime = '%ddays' % (float(uptime) / 86400)

    # Only look at critical level here, don't care about warning one
    if uptime < critical:
        print "Critical: uptime is %ds | uptime=%ds" %(uptime, uptime)
        sys.exit(2)
    print "Ok: uptime is %s (%ds) | uptime=%ds" % (s_pretty_uptime, uptime, uptime)
    sys.exit(0)
