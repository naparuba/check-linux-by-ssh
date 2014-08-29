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

def get_mpstat(client):
    # We are looking for such lines:
    #Average:     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest   %idle
    #Average:     all    1.51    0.00    0.50    0.25    0.00    0.00    0.00    0.00   97.74
    #Average:       0    1.01    0.00    0.00    0.00    0.00    0.00    0.00    0.00   98.99
    #Average:       1    1.01    0.00    0.00    0.00    0.00    0.00    0.00    0.00   98.99
    #Average:       2    2.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00   97.00
    #Average:       3    2.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00   97.00

    # Beware of the export!
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && mpstat -P ALL 1 1')
    stats = {}

    pos = {'%usr':-1, '%nice':-1, '%sys':-1, '%iowait':-1, '%irq':-1, '%soft':-1, '%steal':-1, '%guest':-1, '%idle':-1}

    for line in stdout:
        line = line.strip()
        # By pass the firt line, we already know about it
        if not line:
            continue
        
        # Some mpstat version got various index for %usr or %idle, so parse the line and find the index
        # directly
        if 'CPU' in line and (r'%usr' in line or r'%user' in line):
            elts = [e for e in line.split(' ') if e]
            for k in pos:
                try:
                    pos[k] = elts.index(k)
                except ValueError:
                    if k == '%usr':
                        pos[k] = elts.index('%user')
                    elif k == '%guest':
                        pass
                    else:
                        raise
            continue
        
        if not line.startswith('Average:'):
            continue
        
        # Ok we do not want for the first one with title
        if line.startswith('CPU'):
            continue

        tmp = [e for e in line.split(' ') if e]
        cpu = tmp[1]#.pop(0)
        # Beware of _sys, not sys that is a module!
        stats[cpu] = {'%usr':0, '%nice':0, '%sys':0, '%iowait':0, '%irq':0, '%soft':0, '%steal':0, '%guest':0, '%idle':0}

        for (k, idx) in pos.iteritems():
            if idx == -1:
                continue
            stats[cpu][k] = float(tmp[idx])

    # Before return, close the client
    client.close()
    return stats





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
    stats = get_mpstat(client)
    
    # Maybe we failed at getting data
    if not stats:
        print "Error : cannot fetch cpu stats values from host"
        sys.exit(3)
    
    perfdata = []
    for (cpu, v) in stats.iteritems():
        s_cpu = 'cpu_%s' % cpu
        for (k,j) in v.iteritems():
            # We remove the % of the %usr for example in k
            perfdata.append('%s_%s=%.2f%%' % (s_cpu, k[1:], j))


    print "OK | %s" % (' '.join(perfdata))
    sys.exit(0)

