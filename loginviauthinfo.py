#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# IMPORTANT: calls the sas-admin CLI. Change the variable below if your CLI is not
# installed in the default location.
#
# Login as the user specified in the .authinfo file. If no file is specifiied use the .authinfo file in
# the users current home-directory
#
# Will only actually logon if:
# 1) the current token is within 15 minutes of expiring OR
# 2) the user changes
# 3) --forcelogin is specified
#
# usage python loginviauthinfo.py
#              loginviauthinfo.py -f /tmp/myfile
#
#
# Authinfo file uses .netrc format https://www.ibm.com/support/knowledgecenter/en/ssw_aix_71/filesreference/netrc.html
#
# Example of file. First line specifies the default userid and password if no machine is specified. Second line specifies a machine and the
# userid and password for that machine,
#
# default user sasadm1 password mypass
# machine sasviya01.race.sas.com user sasadm2 password mpass2
#
# Change History
#
# 25AUG2019 modified to logon to the host in the profile and support multiple lines in authinfo
# 10OCT2019 minor edits to header, no code changes
# 18OCT2019 quote the password in the CLI step to deal with special characters
# 12NOV2019 do quote the password for windows
# 12NOV2019 deal with urlparse on python 3
# 10OCT2020 only logon if the token is close to expiry or user changes
#
# Copyright © 2018, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the License);
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from __future__ import print_function

import netrc
import subprocess
import platform
import os
import argparse
import json
import time
from datetime import datetime as dt, timedelta as td

from sharedfunctions import file_accessible, getprofileinfo

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse


# CHANGE THIS VARIABLE IF YOUR CLI IS IN A DIFFERENT LOCATION
clidir='/opt/sas/viya/home/bin/'
#clidir='c:\\admincli\\'

debug=0
profileexists=0

# get input parameters
parser = argparse.ArgumentParser(description="Optionally specify an authinfo file")
parser.add_argument("-f","--file", help="Enter the path to the authinfo file.",default='.authinfo')
parser.add_argument("--forcelogin", help="Force login to happen.",action="store_true")

args = parser.parse_args()
authfile=args.file
forcelogin=args.forcelogin

now=dt.today()

# Read from the authinfo file in your home directory
fname=os.path.join(os.path.expanduser('~'),authfile)

# get current profile from ENV variable or if not set use default
myprofile=os.environ.get("SAS_CLI_PROFILE","Default")
print("Logging in with profile: ",myprofile )

# get hostname from profile
endpointfile=os.path.join(os.path.expanduser('~'),'.sas','config.json')
access_file=file_accessible(endpointfile,'r')
badprofile=0

#profile does not exist
if access_file==False:
    badprofile=1
    host='default'


#profile is empty file
if os.stat(endpointfile).st_size==0:
    badprofile=1
    host='default'

# get json from profile

if not badprofile:

    with open(endpointfile) as json_file:
        data = json.load(json_file)

    # get the hostname from the current profile
    if myprofile in data:
        urlparts=urlparse(data[myprofile]['sas-endpoint'])
        host=urlparts.netloc
        print("Getting Credentials for: "+host)
        profileexists=1

    else: #without a profile don't know the hostname
        profileexists=0
        print("ERROR: profile "+myprofile+" does not exist. Recreate profile with sas-admin profile init.")


if profileexists:

    # based on the hostname get the credentials and login
    if os.path.isfile(fname):

       secrets = netrc.netrc(fname)
       username, account, password = secrets.authenticators( host )

       if debug:
          print('user: '+username)
          print('profile: '+myprofile)
          print('host: '+host)

       current_info=getprofileinfo(myprofile)

       expiry=current_info["expiry"][:-1]
       cur_user=current_info["cur_user"]

       expiry_dt=dt.strptime(expiry,"%Y-%m-%dT%H:%M:%S")

       howlongleft=expiry_dt - now
       timeleft_in_s = howlongleft.total_seconds()

       #print ('Token expires in ' + str(timeleft_in_s))

       # if token expires in under 15 minutes re-authenticate or if user has changed or if forced to
       if ((timeleft_in_s < 900) or (cur_user != username) or forcelogin):

          #quote the password string for posix systems
          print ("NOTE: logging on as "+ username )
          if (os.name =='posix'): command=clidir+"sas-admin  --profile "+myprofile+ " auth login -u "+username+ " -p '"+password+"'"
          else: command=clidir+'sas-admin --profile '+myprofile+ ' auth login -u '+username+ ' -p '+password

          subprocess.call(command, shell=True)

       else:
          print("NOTE: token expires in approximately " +str(int(timeleft_in_s/3600))+  " hours at " + expiry )
          print("NOTE: no logon required")

    else:
       print('ERROR: '+fname+' does not exist')


