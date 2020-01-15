from os import environ
from os.path import basename, join
from urllib.parse import urljoin
from uuid import uuid4

from paramiko import AutoAddPolicy, SSHClient

from helpers import base64_dict, base64_str


def copy_entrypoint(payload, db):
    command = payload['cmd']

    # Generate job identifier
    identifier = str(uuid4().hex[0:6])

    # Run container
    container = Srm2Local(identifier, command)
    container.run()

    # Record keeping
    files = [basename(path) for path in command['src']['paths']]

    db.set(f'{identifier}_status', 'queued')
    db.set(f'{identifier}_files', files)
    for f in files:
        db.set(f'{identifier}_files_{f}', 'pending')

    db.dump()

    return ({'requestId': identifier}, 202)


def status_entrypoint(payload, db):
    identifier = payload['identifier']
    status = db.get(f'{identifier}_status')

    files = db.get(f'{identifier}_files')
    files = {
        f: db.get(f'{identifier}_files_{f}') for f in files
    }

    return ({
        'requestId': identifier,
        'status': status,
        'files': files
    }, 200)


def callback_entrypoint(payload, db):
    identifier = payload['identifier']
    status = payload['status']
    files = payload.get('files')

    if files is not None:
        for f in files:
            filename = basename(f)
            db.set(f'{identifier}_files_{filename}', status)
    else:
        db.set(f'{identifier}_status', status)

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

        options = self.command.get('options', {})
        parallelism = options.get('parallelism', 1)
        partition_size = options.get('partition_size', 5)

        # Prepare arguments
        callback_url = urljoin('http://' + environ.get('SRM2LOCAL_SERVICE'), '/callback')
        arguments = base64_dict({
            'identifier': self.identifier,
            'callback_url': callback_url,
            'files': srm_paths,
            'parallelism': parallelism,
            'partition_size': partition_size,
            'proxy': srm_certificate
        })

        print(arguments)

        # Open SSH connection to HPC
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(hpc_host, 22, hpc_username, hpc_password)

        # Run Singuliarty container using Slurm
        filename = f'job-{self.identifier}.sh'
        bash = f'singularity run -B {hpc_path}:/local {self.container_uri} {arguments}'
        sbatch = 'sbatch -t 0-1:00 --ntasks=1 --cpus-per-task=8 --mem=8gb'

        if hpc_host == 'pro.cyfronet.pl':
            sbatch += ' --partition=plgrid-testing'
            bash = 'module add plgrid/tools/singularity/stable' + '\n' + bash

        if hpc_host.endswith('lrz.de'):
            sbatch += ' --cluster mpp2'
            bash =  'module load slurm_setup/default' + '\n'
            bash += 'module load charliecloud/0.10' + '\n'
            bash += 'curl -L https://git.io/JvvIy -o chaplin && chmod +x chaplin' + '\n'
            bash += './chaplin -n -d microinfrastructure/adaptor-srm2local-hpc' + '\n'
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
