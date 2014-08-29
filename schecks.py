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
        raise Exception(err)
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


