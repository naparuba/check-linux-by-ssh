#!/usr/bin/env python2

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


"""This script checks Linux RAID status via /proc/mdstat. """
import os
import sys


# Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    import schecks
except ImportError:
    print "ERROR : this plugin needs the local schecks.py lib. Please install it"
    sys.exit(2)

VERSION = "0.3"


def get_raid_status(client):
    # Default values
    mdraid_healthy = True
    mdraid_recover = '100'
    mdraid_check = '0'
    mdraid_sync = '0'

    # Try to read in the mdstat file contents.
    cat_mdstat = 'cat /proc/mdstat'
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && %s' % cat_mdstat)
    if stderr.read():
        print 'No MDRAID arrays found'
        sys.exit(0)
    else:
        mdadm_lines = [line.strip() for line in stdout]

    # Sometimes a /proc/mdstat will exist, even when there are no active arrays.
    # Check to see if any md* arrays exist.
    if not any('md' in line for line in mdadm_lines):
        print 'No active MDRAID arrays found'
        sys.exit(0)

    # Check if there are any missing RAID devices. If so, array must be degraded.
    if any('_' in line for line in mdadm_lines):
        mdraid_healthy = False

    # Check the RAID scrub, sync, and recover status.
    for line in mdadm_lines:
        if 'check' in line:
            mdraid_check = line.split()[3][:-1]
        elif 'sync' in line:
            mdraid_sync = line.split()[3][:-1]
        elif 'recover' in line:
            mdraid_recover = line.split()[3][:-1]

    # Before return, close the client
    client.close()

    return mdraid_healthy, mdraid_recover, mdraid_check, mdraid_sync

###############################################################################

parser = schecks.get_parser()

if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    
    # Ok now got an object that link to our destination
    client = schecks.get_client(opts)
    
    # Scrape /proc/mdstat and get result and perf data
    healthy, recover, scrub, sync = get_raid_status(client)
    # Format perf data
    perf = "|Recover={0}%;0%;100% Scrub={1}%;0%;100% Sync={2}%;0%;100%".format(recover, scrub, sync)

    if not float(recover) == 100:
        print("WARNING: RAID is recovering " + perf)
        sys.exit(1)
    elif healthy:
        print "OK: RAID is healthy " + perf
        sys.exit(0)
    else:
        print "CRITICAL: RAID is degraded " + perf
        sys.exit(2)
