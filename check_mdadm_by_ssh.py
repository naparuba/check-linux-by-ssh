#!/usr/bin/env python

# Copyright (C) 2013:
#     Gabes Jean, naparuba@gmail.com
#     Pasche Sebastien, sebastien.pasche@leshop.ch
#     Benjamin Moran, benmoran56@gmail.com
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
 This script is a check for Linux RAID status via /proc/mdstat.
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

def get_raid_status(client):

    # Default values
    mdraid_healthy = True
    #mdraid_resync = 100.0
    mdraid_recover = 100.0
    mdraid_check = 100.0

    # Check if /proc/mdstat exists or not.
    # Result will be empty IF /proc/mdstat is found.
    check_mdstat = 'test -f /proc/mdstat || echo "null"'
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % check_mdstat)
    result = stdout.readline()
    if result:
        print "No MDRAID arrays found"
        sys.exit(0)

    # Sometimes a /proc/mdstat will exist, even when there are no active arrays.
    # Check to see if any md* arrays exist.
    get_devices = 'grep ^md -c /proc/mdstat'
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_devices)
    raid_devices = int(stdout.read())
    if raid_devices == 0:
        print "No MDRAID arrays found"
        sys.exit(0)

    # Check if there are any missing RAID devices. If so, array must be degraded.
    get_status = "grep '\[.*_.*\]' /proc/mdstat -c"
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_status)
    raid_status = int(stdout.read())
    if raid_status == 1:
        mdraid_healthy = False

    # Check the raid recovery (rebuild) process.
    get_recover = "grep recovery /proc/mdstat | awk '{print $4}'"
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_recover)
    raid_recover = stdout.read()
    if raid_recover:
        mdraid_recover = raid_recover[:-1]

    """
    # Check the raid resync status.
    get_resync = "grep resync /proc/mdstat | awk '{print $4}'"
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_resync)
    raid_resync = stdout.read()
    if raid_resync:
        mdraid_resync = raid_resync
    """

    # Check the RAID scrub status
    #get_check = "grep '\[.*>.*\]' /proc/mdstat | awk '{print $4}'"
    get_check = "grep check /proc/mdstat | awk '{print $4}'"
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_check)
    raid_check = stdout.read()
    if raid_check:
        mdraid_check = float(raid_check[:-2])

    raid_stats = [mdraid_healthy, mdraid_recover, mdraid_check]

    # Before return, close the client
    client.close()

    return raid_stats

###############################################################################

parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + VERSION)
parser.add_option('-H', '--hostname',
                  dest="hostname", help='Hostname to connect to')
parser.add_option('-i', '--ssh-key',
                  dest="ssh_key_file", help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
parser.add_option('-u', '--user',
                  dest="user", help='remote use to use. By default shinken.')
parser.add_option('-P', '--passphrase',
                  dest="passphrase", help='SSH key passphrase. By default will use void')

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

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)

    # Scrape /proc/mdstat and get result and perf data
    raid_statistics = get_raid_status(client)
    recover_percent = str(raid_statistics[1])
    scrub_percent = str(raid_statistics[2])
    perf_data = "| Recover="+ recover_percent + "%;;;0%;100% Scrub="+ scrub_percent + "%;;;0%;100%"

    if raid_statistics[0] == True:
        print "OK: RAID is healthy " + perf_data
        sys.exit(0)
    else:
        print "CRITICAL: RAID is degraded " + perf_data
        sys.exit(2)
    sys.exit(0)
