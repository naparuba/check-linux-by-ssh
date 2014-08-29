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
MOUNTS = None 
UNITS= {'B': 0,
        'KB': 1,
        'MB': 2,
        'GB': 3,
        'TB': 4
        }

def convert_to(unit,value):
    power = 0
    if unit in UNITS:
        power = UNITS[unit]
    return round(float(value)/(1024**power), power)


def get_df(client):
    # We are looking for a line like 
    #Filesystem     Type     1K-blocks      Used Available Use% Mounted on
    #/dev/sda2      ext3      28834744  21802888   5567132  80% /
    #udev           devtmpfs   1021660         4   1021656   1% /dev
    #tmpfs          tmpfs       412972      1040    411932   1% /run
    #none           tmpfs         5120         4      5116   1% /run/lock
    #none           tmpfs      1032428     13916   1018512   2% /run/shm
    #none           tmpfs       102400         8    102392   1% /run/user
    #/dev/sda5      fuseblk  251536380 184620432  66915948  74% /media/ntfs
    #/dev/sdb1      ext3     961432072 833808328  78785744  92% /media/bigdata

    # Beware of the export!
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && df -l -T -k -P')
    dfs = {}

    for line in stdout:
        line = line.strip()
        # By pass the firt line, we already know about it
        if not line or line.startswith('Filesystem'):
            continue
        
        # Only keep non void elements
        tmp = [s for s in line.split(' ') if s]
        
        _type = tmp[1]
        # Ok maybe we got a none or tmpfs system, if so, bailout
        if _type in ['tmpfs', 'devtmpfs', 'iso9660']:
            continue

        #if we specify a list of mountpoints to check then verify that current line is in the list
        to_check = True
        if MOUNTS:
            to_check = False
            for mnt in MOUNTS:
                if tmp[6].startswith(mnt):
                    to_check = True
        
        # Maybe this mount point did not match any required mount point
        if not to_check:
            continue

        # Ok now grep values
        fs =  tmp[0]
        size = int(tmp[2])*1024
        used = int(tmp[3])*1024
        avail = int(tmp[4])*1024
        used_pct = int(tmp[5][:-1]) # we remove the %
        mounted = ' '.join(tmp[6:])
        dfs[mounted] = {'fs':fs, 'size':size, 'used':used, 'avail':avail, 'used_pct':used_pct}

    # Before return, close the client
    client.close()

    return dfs





parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + VERSION)
parser.add_option('-H', '--hostname',
    dest="hostname", help='Hostname to connect to')
parser.add_option('-i', '--ssh-key',
                  dest="ssh_key_file",
                  help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
parser.add_option('-p', '--port',
                  dest="port", type="int", default=22,
                  help='SSH port to connect to. Default : 22')
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
parser.add_option('-m', '--mount-points',
                  dest="mounts",
                  help='comma separated list of mountpoints to check. Default all mount '
                  'points except of tmpfs types')
parser.add_option('-U', '--unit',
                  dest="unit", help='Unit of Disk Space. B, KB, GB, TB. Default : B')


if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    port = opts.port
    hostname = opts.hostname or ''

    if opts.mounts:
        mounts = opts.mounts.split(',')
        MOUNTS=mounts

    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    # Try to get numeic warning/critical values
    s_warning  = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL
    warning, critical = schecks.get_warn_crit(s_warning, s_critical)

    # Get Unit 
    s_unit = opts.unit or 'B'

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    dfs = get_df(client)
    
    # Maybe we failed at getting data
    if not dfs:
        print "Error : cannot fetch disks values from host"
        sys.exit(2)

    perfdata = ''
    status = 0 # all is green until it is no more ok :)
    bad_volumes = []
    for (mount, df) in dfs.iteritems():
        size = convert_to(s_unit,df['size'])
        used = convert_to(s_unit,df['used'])
        used_pct =  df['used_pct']
        # Let first dump the perfdata
        
        _size_warn = convert_to(s_unit,df['size'] * float(warning)/100)
        _size_crit = convert_to(s_unit,df['size'] * float(critical)/100)
        
        perfdata += '"%s_used_pct"=%s%%;%s%%;%s%%;0%%;100%% "%s_used"=%s%s;%s;%s;0;%s ' % (mount, used_pct, warning, critical, mount, used, s_unit, _size_warn, _size_crit, size)
        
        # And compare to limits
        if used_pct >= critical:
            status = 2
            bad_volumes.append( (mount, used_pct) )

        if used_pct >= warning and status == 0:
            status = 1
            bad_volumes.append( (mount, used_pct) ) 

    if status == 0:
        print "Ok: all disks are in the limits | %s" % (perfdata)
        sys.exit(0)
    if status == 1:
        print "Warning: some disks are not good : %s | %s" % (','.join( ["%s:%s%%" % (mount, used_pct) for (mount, used_pct) in bad_volumes]), perfdata)
        sys.exit(1)
    if status == 2:
        print "Critical: some disks are not good : %s | %s" % (','.join( ["%s:%s%%" % (mount, used_pct) for (mount, used_pct) in bad_volumes]), perfdata)
        sys.exit(2)

