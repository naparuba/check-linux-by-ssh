#!/usr/bin/env python2

# Copyright (C) 2013-:
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
 This script is a check for lookup at disks consumption
'''
import os
import sys

import schecks

description = 'Disks space check'

DEFAULT_WARNING = '75%'
DEFAULT_CRITICAL = '90%'
MOUNTS = None 
UNITS= {'B': 0,
        'KB': 1,
        'MB': 2,
        'GB': 3,
        'TB': 4
        }

def convert_to(unit, value):
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

    return dfs


class Check(schecks.GenCheck):
    def fill_parser(self):
        self.parser.add_option('-w', '--warning',
                          dest="warning",
                          help='Warning value for physical used memory. In percent. Default : 75%')
        self.parser.add_option('-c', '--critical',
                      dest="critical",
                          help='Critical value for physical used memory. In percent. Must be '
                          'superior to warning value. Default : 90%')
        self.parser.add_option('-m', '--mount-points',
                          dest="mounts",
                          help='comma separated list of mountpoints to check. Default all mount '
                          'points except of tmpfs types')
        self.parser.add_option('-U', '--unit',
                          dest="unit", help='Unit of Disk Space. B, KB, GB, TB. Default : B')

    
    def check_args(self):
        global MOUNTS
        if self.opts.mounts:
            mounts = self.opts.mounts.split(',')
            MOUNTS = mounts
    
        # Try to get numeic warning/critical values
        s_warning  = self.opts.warning or DEFAULT_WARNING
        s_critical = self.opts.critical or DEFAULT_CRITICAL
        self.warning, self.critical = schecks.get_warn_crit(s_warning, s_critical)
    
        # Get Unit 
        self.s_unit = self.opts.unit or 'B'
        

    def do_check(self):
        ## And get real data
        dfs = get_df(self.client)
    
        # Maybe we failed at getting data
        if not dfs:
            print "Error : cannot fetch disks values from host"
            sys.exit(2)
    
        perfdata = ''
        status = 0 # all is green until it is no more ok :)
        bad_volumes = []
        for (mount, df) in dfs.iteritems():
            size = convert_to(self.s_unit, df['size'])
            used = convert_to(self.s_unit, df['used'])
            used_pct =  df['used_pct']
            # Let first dump the perfdata
        
            _size_warn = convert_to(self.s_unit,df['size'] * float(self.warning)/100)
            _size_crit = convert_to(self.s_unit,df['size'] * float(self.critical)/100)
        
            perfdata += '"%s_used_pct"=%s%%;%s%%;%s%%;0%%;100%% "%s_used"=%s%s;%s;%s;0;%s ' % (mount, used_pct, self.warning, self.critical, mount, used, self.s_unit, _size_warn, _size_crit, size)
        
            # And compare to limits
            if used_pct >= self.critical:
                status = 2
                bad_volumes.append( (mount, used_pct) )
        
            if used_pct >= self.warning and status == 0:
                status = 1
                bad_volumes.append( (mount, used_pct) ) 
    
        if status == 0:
            self.set("Ok: all disks are in the limits", 0, perfdata)
            return
    
        if status == 1:
            output = "Warning: some disks are not good : %s" % (','.join( ["%s:%s%%" % (mount, used_pct) for (mount, used_pct) in bad_volumes]))
            self.set(output, 1, perfdata)
            return

        if status == 2:
            output ="Critical: some disks are not good : %s" % (','.join( ["%s:%s%%" % (mount, used_pct) for (mount, used_pct) in bad_volumes]))
            self.set(output, 2, perfdata)
            return
