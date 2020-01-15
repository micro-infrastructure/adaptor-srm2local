#!/bin/bash
export SRM_PATH=/opt/srmclient-2.6.28/usr/share/srm
export PATH=/opt/srmclient-2.6.28/usr/bin:$PATH

python3 /var/local/download.py $1 $PWD