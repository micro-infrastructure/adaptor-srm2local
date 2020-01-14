BootStrap: docker
From: ubuntu:16.04

%files
    ./assets/srmclient-2.6.28.tar.gz    /var/local
    ./assets/voms.grid.sara.nl.lsc      /var/local
    ./assets/lta-url-copy.sh            /var/local
    ./assets/lofar.vo                   /var/local
    ./scripts/unpack_args.py            /var/local
    ./scripts/execute_webhook.py        /var/local

%post
    apt-get update && apt-get install -y wget curl python3 --no-install-recommends

    echo "deb [trusted=yes] http://repository.egi.eu/sw/production/cas/1/current egi-igtf core" >> /etc/apt/sources.list
    wget -q -O - http://repository.egi.eu/sw/production/cas/1/current/GPG-KEY-EUGridPMA-RPM-3 | apt-key add -
    
    apt-get update && apt-get install -y \
        openjdk-8-jdk-headless \
        globus-gass-copy-progs \
        voms-clients \
        ca-policy-egi-core \
        fetch-crl \
    && rm -rf /var/lib/apt/lists/*

    cd /var/local && tar -xzf srmclient-2.6.28.tar.gz \
        && mv srmclient-2.6.28 /opt/srmclient-2.6.28 \
        && mkdir -p /etc/grid-security/vomsdir/lofar \
        && mv voms.grid.sara.nl.lsc /etc/grid-security/vomsdir/lofar \
        && mkdir -p /etc/vomses \
        && mv lofar.vo /etc/vomses

%runscript
    export SRM_PATH=/opt/srmclient-2.6.28/usr/share/srm
    export PATH=/opt/srmclient-2.6.28/usr/bin:$PATH

    # Unpack arguments (proxy and copyjobfile)
    python3 /var/local/unpack_args.py $1 $PWD
    
    # Perform copying (+ stopwatch)
    date
    srmcp -use_urlcopy_script=true -urlcopy=/var/local/lta-url-copy.sh -server_mode=passive -x509_user_proxy=proxy -copyjobfile=copyjobfile
    date

    # Execute webhook
    python3 /var/local/execute_webhook.py $1  
    
    # Cleanup
    rm copyjobfile proxy