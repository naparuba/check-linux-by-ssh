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
DEFAULT_WARNING = '1,1,1'
DEFAULT_CRITICAL = '2,2,2'


def get_tcp_states(client):
    # We are looking for a line like 
    #0.19 0.17 0.15 1/616 3634 4
    # l1  l5   l15  _     _    nb_cpus
    raw = r"""cat /proc/net/tcp /proc/net/tcp6 2>/dev/null | awk ' /:/ { c[$4]++; } END { for (x in c) { print x, c[x]; } }'"""
    stdin, stdout, stderr = client.exec_command(raw)
    states = {}
    for line in stdout:
        line = line.strip()
        if not line:
            continue
        state, nb = tuple(line.split(' '))
        states[state] = int(nb)

    # Before return, close the client
    client.close()
        
    return states






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
parser.add_option('-C', '--cpu-based', action='store_true',
    dest="cpu_based",
    help='Set the warning/critical number of cpu based values. For example '
        '1,1,1 will warn if the load if over the number of CPUs. '
        'Default : False')



if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    hostname = opts.hostname
    if not hostname:
        print "Error : hostname parameter (-H) is mandatory"
        sys.exit(2)
    port = opts.port
    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    # Try to get numeic warning/critical values
    s_warning  = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL
    
    # For warning/critical : or we got a int triplet, or a float*nb_cpu values
    cpu_based = opts.cpu_based or False
    if s_warning.count(',') != 2 or s_critical.count(',') != 2:
        print "Error: warning and/or critical values do not match type. Please fix it (-w and -c)"
        sys.exit(2)
    warning  = [float(v) for v in s_warning.split(',')]
    critical = [float(v) for v in s_critical.split(',')]
        
    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    states = get_tcp_states(client)

    # Thanks the "/proc and /sys" book :)
    mapping = {'ESTABLISHED':'01', 'SYN_SENT':'02', 'SYN_RECV':'03', 'FIN_WAIT1':'04', 'FIN_WAIT2':'05',
               'TIME_WAIT':'06', 'CLOSE':'07', 'CLOSE_WAIT':'08', 'LAST_ACK':'09', 'LISTEN':'0A', 'CLOSING':'0B'}

        
    perfdata = []
    for (k,v) in mapping.iteritems():
        # Try to get by the state ID, if none, get 0 instead
        nb = states.get(v, 0)
        perfdata.append( '%s=%d' % (k, nb) )

    print "OK | %s" % ' '.join(perfdata)
    sys.exit(0)

        

