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
    lines = [line.strip() for line in stdout]
    
    if 'null' in lines:
        print "No MDRAID arrays found"
        sys.exit(0)

    # Sometimes a /proc/mdstat will exist, even when there are no active arrays.
    # Check to see if any md* arrays exist.
    get_devices = 'grep ^md -c /proc/mdstat'
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_devices)
    lines = [line.strip() for line in stdout]
    raid_devices = int('\n'.join(lines))
    if raid_devices == 0:
        print "No MDRAID arrays found"
        sys.exit(0)

    # Check if there are any missing RAID devices. If so, array must be degraded.
    get_status = "grep '\[.*_.*\]' /proc/mdstat -c"
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_status)
    lines = [line.strip() for line in stdout]
    raid_status = int('\n'.join(lines))
    if raid_status == 1:
        mdraid_healthy = False

    # Check the raid recovery (rebuild) process.
    get_recover = "grep recovery /proc/mdstat | awk '{print $4}'"
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % get_recover)
    lines = [line.strip() for line in stdout]
    raid_recover = '\n'.join(lines)
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
    lines = [line.strip() for line in stdout]
    raid_check = '\n'.join(lines)
    if raid_check:
        mdraid_check = float(raid_check[:-2])

    raid_stats = [mdraid_healthy, mdraid_recover, mdraid_check]

    # Before return, close the client
    client.close()

    return raid_stats

###############################################################################

parser = schecks.get_parser()

if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    
    # Ok now got an object that link to our destination
    client = schecks.get_client(opts)
    
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
