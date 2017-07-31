#!/usr/bin/env python2

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
 This script is a check for lookup at package update over ssh without
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
DEFAULT_WARNING = '1,0'
DEFAULT_CRITICAL = '2,2,2'


def get_package_update_debian(client):

    security_upgrades_cmd = "TMP_FILE=$( mktemp ) ; grep -R --no-filename security /etc/apt/sources.list* > $TMP_FILE ; apt-get upgrade -oDir::Etc::Sourcelist=$TMP_FILE   -o Dir::Etc::sourceparts=\"-\" -s | grep \"upgraded,\" |awk '{ print $1 }' ; rm -f $TMP_FILE"
    all_upgrades_cmd = "apt-get upgrade -s |grep upgraded,|awk '{print $1 }'"

    _, security_updates, _ = client.exec_command(security_upgrades_cmd)
    _, all_upgrades, _ = client.exec_command(all_upgrades_cmd)

    # Localhost request return list object
    if not isinstance(security_updates, list):
        security_updates = security_updates.read().strip()
        all_upgrades = all_upgrades.read().strip()
    else:
        security_updates = security_updates[0]
        all_upgrades = all_upgrades[0]

    # Before return, close the client
    client.close()

    return security_updates, all_upgrades

def get_package_update_yum(client):
    _, security_updates, _ = client.exec_command("yum list-sec updates --security --quiet |wc -l")
    _, all_upgrades, _ = client.exec_command("yum  list  updates --quiet |grep -v 'Updated Packages' |wc -l")

    # Localhost request return list object
    if not isinstance(security_updates, list):
        security_updates = security_updates.read().strip()
        all_upgrades = all_upgrades.read().strip()

    # Before return, close the client
    client.close()

    return security_updates[0], all_upgrades[0]

def get_package_update(client):

    _, os, _ = client.exec_command("cat /etc/issue|awk '{ print $1 }'|head -n1")
    if not isinstance(os, list):
        os = os.read().strip()
    if os == "Red" or os == "CentOS" or os == "Fedora":
        return get_package_update_yum(client)
    else:
        return get_package_update_debian(client)



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
                  default='0,-1',
                  dest="warning",
                  help='Warning value for upgradable package, as 2 values. First one for security upgrade, second one for standard. If you set one of this value to -1 this will disable the check. Default : 0,-1')
parser.add_option('-c', '--critical',
                  dest="critical",
                  default='1,-1',
                  help='Critical value for upgradable package, as 2 values. First one for security upgrade, second one for standard. If you set one of this value to -1 this will disable the check. Default : 1,-1')

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
    if s_warning.count(',') != 1 or s_critical.count(',') != 1:
        print "Error: warning and/or critical values do not match type. Please fix it (-w and -c)"
        sys.exit(2)
    warning  = [float(v) for v in s_warning.split(',')]
    critical = [float(v) for v in s_critical.split(',')]

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    security_updates, all_upgrades = get_package_update(client)
    security_updates = int(security_updates)
    all_upgrades = int(all_upgrades)

    status = 0
    # check warning threshold
    if ( warning[0] != -1 and warning[0] > security_updates ) or ( warning[1] != -1 and warning[1] > all_upgrades ):
        status = 1
    if ( critical[0] != -1 and critical[0] > security_updates ) or ( critical[1] != -1 and critical[1] > all_upgrades ):
        status = 2

    perfdata = ''
    perfdata += ' security={security_updates};{warn};{crit};;'.format(
            security_updates = security_updates,
            warn = warning[0] if warning[0] != -1 else '',
            crit = critical[0] if critical[0] != -1 else '')
    perfdata += ' all={all_upgrades};{warn};{crit};;'.format(
            all_upgrades = all_upgrades,
            warn = warning[1] if warning[1] != -1 else '',
            crit = critical[1] if critical[1] != -1 else '')

    # And compare to limits
    if status == 2:
        print "Critical: {security_updates} critical upgrade, {all_upgrades} upgrade | {perf_data}".format(
                security_updates = security_updates,
                all_upgrades = all_upgrades,
                perf_data = perfdata)
        sys.exit(2)

    if status == 1:
        print "Warning : {security_updates} critical upgrade, {all_upgrades} upgrade | {perf_data}".format(
                security_updates = security_updates,
                all_upgrades = all_upgrades,
                perf_data = perfdata)
        sys.exit(1)

    print "OK : {security_updates} critical upgrade, {all_upgrades} upgrade | {perf_data}".format(
            security_updates = security_updates,
            all_upgrades = all_upgrades,
            perf_data = perfdata)
    sys.exit(0)
