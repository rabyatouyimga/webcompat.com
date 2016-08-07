#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import pkg_resources
from pkg_resources import DistributionNotFound, VersionConflict
import time
import datetime
import os
import sys

IMPORT_ERROR = '''
==============================================
It seems like you don't have all dependencies.
Please re-run:
    pip install -r requirements.txt
==============================================
'''

NO_CONF_ERROR = '''
==============================================
The config.py file seems to be missing.

Please create a copy of config.py.example and customize it accordingly.
For details, please see
https://github.com/webcompat/webcompat.com/blob/master/CONTRIBUTING.md#configuring-the-server
==============================================
'''

FILE_NOT_FOUND_ERROR = '''
==============================================
The issues.db file seems to be missing.

Please create a issues.db file by running:

python run.py
==============================================
'''

try:
    from webcompat import app
except ImportError, e:
    if 'import_name' in e and e.import_name == 'config':
        # config not found, did you forget to copy config.py.example?
        raise ImportError('{0}\n\n{1}'.format(e, NO_CONF_ERROR))
    else:
        raise ImportError('{0}\n\n{1}'.format(e, IMPORT_ERROR))


TOKEN_HELP = '''
The OAUTH_TOKEN is not configured in your config file.
You will need to set up one on github for testing your
local developments.
Read Instructions at
https://github.com/webcompat/webcompat.com/blob/master/CONTRIBUTING.md#configuring-the-server
'''

DEPS_VERSION_HELP = '''
The following required versions do not match your locally installed versions:

  %s

Install the correct versions using the commands below before continuing:

pip uninstall name
pip install name==1.2.1
'''

DEPS_NOTFOUND_HELP = '''
The following required module is missing from your installation.

  %s

Install the module using the command below before continuing:

pip install name==1.2.1
'''


def check_pip_deps():
    '''Check installed pip dependencies.

    Make sure that the installed pip packages match what is in
    requirements.txt, prompting the user to upgrade if not.
    '''
    for req in open("./config/requirements.txt"):
        try:
            pkg_resources.require(req)
        except VersionConflict as e:
            print(DEPS_VERSION_HELP % e)
        except DistributionNotFound as e:
            print(DEPS_NOTFOUND_HELP % e)
        else:
            return True


def config_validator():
    '''Make sure the config file is ready.'''
    # Checking if oauth token is configured
    if app.config['OAUTH_TOKEN'] == '':
        sys.exit(TOKEN_HELP)

if __name__ == '__main__':
    # testing the config file
    config_validator()
    # Parsing arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--testmode', action='store_true',
                        help='Run server in "test mode".')
    parser.add_argument('--backup', action='store_true',
                        help='backup existing issues.db and update db schema and issues dump.')
    args = parser.parse_args()

    if args.testmode:
        # disable HttpOnly setting for session cookies so Selenium
        # can interact with them. *ONLY* do this for testing.
        app.config['SESSION_COOKIE_HTTPONLY'] = False
        app.config['TESTING'] = True
        print("Starting server in ~*TEST MODE*~")
        app.run(host='localhost')
    elif args.backup:
        # To verify if issues.db exist, simply calling os.path.exists is not enough.
        # Both os.path.exists and os.path.isfile returns true even when file is not there in the path
        # Every time the script is re run, os.path.exists returns true because of cache.
        # To avoid this, we open the file in try catch - just to be sure
        if os.path.isfile(os.path.join(os.getcwd(), 'issues.db')):
            try:
                with open(os.path.join(os.getcwd(), 'issues.db')) as file:
                    if not os.path.exists(app.config['BACKUP_DEFAULT_DEST']):
                        print 'backup db folder does not exist'
                        os.makedirs(app.config['BACKUP_DEFAULT_DEST'])
                    else:
                        print 'backup db folder exists'
                        # Retain last 3 recent backup files
                        no_of_backup_files = len(os.listdir(app.config['BACKUP_DEFAULT_DEST']))
                        if no_of_backup_files > 3:
                            for idx, val in enumerate(os.listdir(app.config['BACKUP_DEFAULT_DEST'])):
                                if idx < no_of_backup_files - 2:
                                    os.remove(app.config['BACKUP_DEFAULT_DEST'] + val)
                    current_ts = time.time()
                    time_stamp = datetime.datetime.fromtimestamp(current_ts).strftime('%Y-%m-%d-%H:%M:%S')
                    issue_backup_db = 'issues_backup_' + time_stamp + '.db'
                    os.rename(os.getcwd() + '/issues.db', app.config['BACKUP_DEFAULT_DEST'] + issue_backup_db)
                    try:
                        os.remove(os.path.join(os.getcwd(), 'issues.db'))
                    except OSError:
                        print 'Backup issues.db complete'

            except IOError:
                sys.exit(FILE_NOT_FOUND_ERROR)

        else:
            sys.exit(FILE_NOT_FOUND_ERROR)
    else:
        if check_pip_deps():
            app.run(host='localhost')
