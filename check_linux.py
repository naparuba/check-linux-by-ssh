#!/usr/bin/env python

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


import os
import sys
import imp
import glob

# Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    import schecks
except ImportError:
    print "ERROR : this plugin needs the local schecks.py lib. Please install it"
    sys.exit(2)


VERSION = "0.1"

import optparse

if __name__ == '__main__':

    modname = ''
    do_list = False
    is_next = False
    for arg in sys.argv:
        if arg == '-l':
            do_list = True
            continue
        if arg == '-t':
            is_next = True
            continue
        if is_next:
            modname = arg
            break

    if do_list:
        fnames = glob.glob(os.path.join(my_dir, 'checks', '*.py'))
        for fname in fnames:
            if fname.endswith('__init__.py'):
                continue
            try:
                mod = imp.load_source(fname[:-3], fname)
                desc = getattr(mod, 'description', 'No description')
                print '%s : %s' % (os.path.basename(fname)[:-3], desc)
            except ImportError, exp:
                print "Cannot load check %s:%s" % (fname, exp)
        sys.exit(0)

    if not modname:
        print "Error: no check name selected. Please list them with -l and select one with -t"
        sys.exit(2)

    try:
        fname = os.path.join(my_dir, 'checks', modname+'.py')
        mod = imp.load_source(modname, fname)
    except (ImportError, IOError), exp:
        print "Cannot load check %s:%s" % (modname, exp)
        sys.exit(2)
                         
    #from checks import disks_stats as mod
    
    # Load it
    check = mod.Check()
    
    # Fill the parser with specific args if need
    check.fill_parser()
    
    # Do the args parsing
    check.parse_args()
    
    # Check if specific args
    check.check_args()
    
    # Ok now get a connexion
    check.get_client()
    
    # Really launch the payload
    check.do_check()
    
    # Now exit with the check output and perfdata
    check.exit()
        
