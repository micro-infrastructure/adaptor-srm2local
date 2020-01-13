from os import environ
from os.path import basename, join
from urllib.parse import urljoin
from uuid import uuid4

from paramiko import AutoAddPolicy, SSHClient

from helpers import base64_dict, base64_str


def copy(payload, db):
    command = payload['cmd']

    # Generate job identifier
    identifier = str(uuid4().hex[0:6])

    # Run container
    container = Srm2Local(identifier, command)
    container.run()

    db.set(identifier, 'active')
    db.dump()

    return ({'requestId': identifier}, 202)


def status(payload, db):
    identifier = payload['identifier']

    status = db.get(identifier)

    return ({'requestId': identifier, 'status': status}, 200)


def callback(payload, db):
    identifier = payload['identifier']

    db.set(identifier, 'finished')
    db.dump()

    return ({}, 200)


class Srm2Local():
    
    def __init__(self, identifier, command):
        self.identifier = identifier
        self.command = command

        self.container_uri = "shub://micro-infrastructure/adaptor-srm2local:latest"
    
    def run(self):
        srm_paths = self.command['src']['paths']
        srm_certificate = self.command['credentials']['srmCertificate']
        hpc_host = self.command['dest']['host']
        hpc_path = self.command['dest']['path']
        hpc_username = self.command['credentials']['hpcUsername']
        hpc_password = self.command['credentials']['hpcPassword']

        # Prepare webhook
        callback_url = urljoin(environ.get('SRM2LOCAL_SERVICE'), '/callback')
        webhook = {
            'url': callback_url,
            'headers': {},
            'response': {
                'identifier': self.identifier
            }    
        }

        # Prepare arguments
        arguments = base64_dict({
            'copyjobfile': self.as_copyjobfile(srm_paths),
            'proxy': srm_certificate,
            'webhook': base64_dict(webhook)
        })

        # Open SSH connection to HPC
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(hpc_host, 22, hpc_username, hpc_password)

        # Run Singuliarty container using Slurm
        filename = f'job-{self.identifier}.sh'
        bash = f'singularity run -B {hpc_path}:/local {self.container_uri} {arguments}'
        sbatch = 'sbatch -t 0-1:00'

        if hpc_host == 'pro.cyfronet.pl':
            sbatch += ' --partition=plgrid-testing'
            bash = 'module add plgrid/tools/singularity/stable' + '\n' + bash

        if hpc_host.endswith('lrz.de'):
            sbatch += ' --cluster mpp2'
            bash =  'module load slurm_setup/default' + '\n'
            bash += 'module load charliecloud/0.10' + '\n'
            bash += 'curl -L https://git.io/JvvIy -o chaplin && chmod +x chaplin' + '\n'
            bash += './chaplin -d microinfrastructure/adaptor-srm2local-hpc' + '\n'
            bash += f'ch-run -w adaptor-srm2local-hpc -b {hpc_path}:/local -- bash /var/local/entrypoint.sh {arguments}' + '\n'

        client.exec_command(f"""
            echo "$(date) {filename}" >> timestamps
        """)
        client.exec_command(f""" 
            echo "#!/bin/bash\n{bash}" > {filename} && {sbatch} {filename}
        """)

        # Close SSH connection to HPC
        client.close()

    def as_copyjobfile(self, paths):
        src_dest = [join(f'{path} file:////local/', basename(path)) for path in paths]
        return base64_str('\n'.join(src_dest))
