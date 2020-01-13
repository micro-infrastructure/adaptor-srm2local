#!/bin/bash

export SRM_PATH=/opt/srmclient-2.6.28/usr/share/srm
export PATH=/opt/srmclient-2.6.28/usr/bin:$PATH

# Unpack arguments (proxy and copyjobfile)
python3 /var/local/unpack_args.py $1 $PWD

# Perform copying (+ stopwatch)
date
srmcp -server_mode=passive -x509_user_proxy=proxy -copyjobfile=copyjobfile
date

# Execute webhook
python3 /var/local/execute_webhook.py $1  

# Cleanup
rm copyjobfile proxy