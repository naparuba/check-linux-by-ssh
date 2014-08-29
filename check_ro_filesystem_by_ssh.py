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


def get_fs(client):
    # We are looking for such lines:
    #/dev/sda5 /media/ntfs fuseblk rw,nosuid,nodev,noexec,relatime,user_id=0,group_id=0,default_permissions,allow_other,blksize=4096 0 0
    #/dev/sdb1 /media/bigdata ext3 rw,relatime,errors=continue,barrier=1,data=ordered 0 0
    
    # Beware of the export!
    stdin, stdout, stderr = client.exec_command('export LC_LANG=C && unset LANG && grep ^/dev < /proc/mounts')

    bad_fs = []
    lines = [line for line in stdout]
    # Let's parse al of this
    for line in lines:
        line = line.strip()
        if not line:
            continue
        tmp = line.split(' ')
        opts = tmp[3]
        if 'ro' in opts.split(','):
            name = tmp[1]
            bad_fs.append(name)

    # Before return, close the client
    client.close()
            
    return bad_fs





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
    dest="user",
    help='remote use to use. By default shinken.')
parser.add_option('-P', '--passphrase',
    dest="passphrase",
    help='SSH key passphrase. By default will use void')
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

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    bad_fs = get_fs(client)
    
    if len(bad_fs) == 0:
        print "OK : no read only file system"
        sys.exit(0)

    print "Critical: read-only FS %s" % ','.join(bad_fs)
    sys.exit(2)

