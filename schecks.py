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
 This small lib is used by shinken checks to got helping functions
'''
import os
import sys
import subprocess
import optparse

VERSION = 0.1

try:
    import paramiko
except ImportError:
    paramiko = None

# If we are in local, we will allow us to avoid to run with ssh
def is_local(hostname):
    if hostname == '127.0.0.1' or hostname == '':
        return True
    return False


class LocalExec(object):
    def __init__(self):
        pass

    def close(self):
        pass

    def exec_command(self, command):
        cmd = command.encode('utf8', 'ignore')
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                close_fds=True, shell=True, preexec_fn=os.setsid)
            stdout, stderr = process.communicate()
        except OSError, exp:
            stderr = exp.__str__()
            stdout = stdin = ''
        return '',stdout.splitlines(),stderr.splitlines()

def get_client(opts):
    hostname = opts.hostname
    port = opts.port
    ssh_key_file = opts.ssh_key_file
    user = opts.user
    passphrase = opts.passphrase
    
    # Ok now connect, and try to get values for memory
    client = connect(hostname, port, ssh_key_file, passphrase, user)
    return client
    

def connect(hostname, port, ssh_key_file, passphrase, user):
    # If we are in a localhost case, don't play with ssh
    if is_local(hostname):
        return LocalExec()

    # Maybe paramiko is missing, but now we relly need ssh...
    if paramiko is None:
        print "ERROR : this plugin needs the python-paramiko module. Please install it"
        sys.exit(2)
    
    if not os.path.exists(os.path.expanduser(ssh_key_file)):
        err = "Error : missing ssh key file. please specify it with -i parameter"
        raise Exception(err)

    ssh_key_file = os.path.expanduser(ssh_key_file)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
    try:
        client.connect(hostname, port=port, username=user,
                       key_filename=ssh_key_file, password=passphrase)
    except Exception, exp:
        err = "Error : connexion failed '%s'" % exp
        print err
        sys.exit(2)
    return client


def close(client):
    try:
        client.close()
    except Exception, exp:
        pass
        

# Try to parse and get int values from warning and critical parameters
def get_warn_crit(s_warn, s_crit):
    if s_warn.endswith('%'):
        s_warn = s_warn[:-1]
    if s_crit.endswith('%'):
        s_crit = s_crit[:-1]
    try:
        warn, crit = int(s_warn), int(s_crit)
    except ValueError:
        print "Error : bad values for warning and/or critical : %s %s" % (s_warn, s_crit)
        sys.exit(2)

    if warn > crit:
        print "Error : warning value %s can't be greater than critical one %s " % (warn, crit)
        sys.exit(2)    

    return warn, crit



def get_parser():
    parser = optparse.OptionParser(
        "%prog [options]", version="%prog " + str(VERSION))
    parser.add_option('-H', '--hostname', default='',
                      dest="hostname", help='Hostname to connect to')
    parser.add_option('-p', '--port',
                      dest="port", type="int", default=22,
                      help='SSH port to connect to. Default : 22')
    parser.add_option('-i', '--ssh-key', default=os.path.expanduser('~/.ssh/id_rsa'),
                      dest="ssh_key_file", help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
    parser.add_option('-u', '--user', default='shinken',
                      dest="user", help='remote use to use. By default shinken.')
    parser.add_option('-P', '--passphrase', default='',
                      dest="passphrase", help='SSH key passphrase. By default will use void')
    parser.add_option('-t',
                      dest="modname", help='Check to load')
    parser.add_option('-l', action='store_true',
                      dest="listmod", help='List all checks available')

    return parser





class GenCheck(object):
    def __init__(self):
        self.output = self.perfdata = ''
        self.exit_code = 3
        self.parser = get_parser()

    # By default do nothing
    def fill_parser(self):
        return


    def parse_args(self):
        # Ok first job : parse args
        self.opts, self.args = self.parser.parse_args()
    
    
    def check_args(self):
        pass


    def get_client(self):
        # Ok now got an object that link to our destination
        self.client = get_client(self.opts)
        
    
    def do_check(self):
        print 'Unknown: no check selected'
        sys.exit(3)


    def set(self, output, exit_code, perfdata=''):
        self.output = output
        self.perfdata = perfdata
        self.exit_code = exit_code
        
        
    def exit(self):
        # first close the client
        self.client.close()

        if self.perfdata:
            print '%s | %s' % (self.output, self.perfdata)
        else:
            print self.output
        sys.exit(self.exit_code)
