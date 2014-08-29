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
 This script is a check for lookup at load average over ssh without
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
DEFAULT_WARNING = '1,1,1'
DEFAULT_CRITICAL = '2,2,2'


def get_load(client):
    # We are looking for a line like 
    #0.19 0.17 0.15 1/616 3634 4
    # l1  l5   l15  _     _    nb_cpus
    raw = r"""echo "$(cat /proc/loadavg) $(grep -E '^CPU|^processor' < /proc/cpuinfo | wc -l)" """
    stdin, stdout, stderr = client.exec_command(raw)
    line = [l for l in stdout][0].strip()
    
    load1, load5, load15, _, _, nb_cpus = (line.split(' '))
    load1 = float(load1)
    load5 = float(load5)
    load15 = float(load15)
    nb_cpus = int(nb_cpus)

    # Before return, close the client
    client.close()

    return load1, load5, load15, nb_cpus




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
                  help='Warning value for load average, as 3 values, for 1m,5m,15m. Default : 1,1,1')
parser.add_option('-c', '--critical',
                  dest="critical",
                  help='Critical value for load average, as 3 values, for 1m,5m,15m. Default : 2,2,2')
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

    port = opts.port
    hostname = opts.hostname or ''

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
    load1, load5, load15, nb_cpus = get_load(client)

    # Two cases : cpu_based_load or not. For CPU the real warning is based on warning*nb_cpu
    status = 0
    w1, w5, w15 = tuple(warning)
    c1, c5, c15 = tuple(critical)
    
    # Look if warning < critical
    if c1 < w1 or c5 < w5 or c15 < w15:
        print "Error: your critical values should be lower than your warning ones. Please fix it (-w and -c)"
        sys.exit(2)

    ratio = 1
    if cpu_based:
        ratio = nb_cpus
    # First warning
    if status == 0 and load1 >= w1*ratio:
        status = 1
    if status == 0 and load5 >= w5*ratio:
        status = 1
    if status == 0 and load15 >= w15*ratio:
        status = 1
    # Then critical
    if load1 >= c1*ratio:
        status = 2
    if load5 >= c5*ratio:
        status = 2
    if load15 >= c15*ratio:
        status = 2
        
    perfdata = ''
    perfdata += ' load1=%.2f;%.2f;%.2f;;' % (load1, w1*ratio, c1*ratio)
    perfdata += ' load5=%.2f;%.2f;%.2f;;' % (load5, w5*ratio, c5*ratio)
    perfdata += ' load15=%.2f;%.2f;%.2f;;' % (load15, w15*ratio, c15*ratio)

    # And compare to limits
    s_load = '%.2f,%.2f,%.2f' % (load1, load5, load15)
    if status == 2:
        print "Critical: load average is too high %s | %s" % (s_load, perfdata)
        sys.exit(2)

    if status == 1:
        print "Warning: load average is very high %s | %s" % (s_load, perfdata)
        sys.exit(1)

    print "Ok: load average is good %s | %s" % (s_load, perfdata)
    sys.exit(0)

        

