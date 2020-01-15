from base64 import b64decode
from json import dumps, loads
from zlib import decompress
from subprocess import run, PIPE
from sys import argv, exc_info
from os import path, remove, environ
from urllib.request import Request, urlopen
from multiprocessing import Pool
from uuid import uuid4

def decode_dict(d):
    return loads(b64decode(d).decode('UTF-8'))


def decode_str(s):
    return decompress(b64decode(s)).decode('UTF-8')


def post_json(payload, url):
    print(payload)

    data = dumps(payload).encode('UTF-8')
    headers = { 'Content-Type': 'application/json' }

    try:
        request = Request(url, data, headers)
        urlopen(request)
    except:
        print(f'Failed to post JSON to: {url}')


def create_copyjob(paths):
    src_dest = [path.join('{p} file:////local/', path.basename(p)) for p in paths]
    return '\n'.join(src_dest)


def create_partitions(list, n):
    if list == []:
        return

    yield list[:n]
    yield from create_partition(list[n:], n)


def callback(identifier, status, files, callback_url, error=None):
    payload = {
        'identifier': identifier,
        'status': status,
    }

    if files is not None:
        payload['files'] = files

    if error is not None:
        payload['error'] = error

    post_json(payload, callback_url)


def download(files):
    copyjob = create_copyjob(files)
    random = str(uuid4().hex[0:4])
    copyjob_file = path.join(working_dir, f'copyjob_{random}')

    # Write copyjob to file
    with open(copyjob_file, 'w') as f:
        f.write(copyjob)

    command = [
        'srmcp',
        '-debug',
        '-use_urlcopy_script=true',
        '-urlcopy=/var/local/lta-url-copy.sh',
        '-server_mode=passive',
        '-x509_user_proxy={proxy_file}',
        '-copyjobfile={copyjob_file}'
    ]

    try:
        callback(identifier, 'downloading', files, callback_url)
        run(command, stdout=PIPE)
        callback(identifier, 'ready', files, callback_url)
    except Exception as e:
        error = str(e)
        callback(identifier, 'failed', files, callback_url, error)

    # Cleanup
    remove(copyjob_file)


if __name__ == '__main__':
    arguments = decode_dict(argv[1])
    working_dir = argv[2]

    # Unpack arguments
    callback_url = arguments['callback_url']
    files = arguments['files']
    identifier = arguments['identifier']
    parallelism = arguments['parallelism']
    partition_size = arguments['partition_size']
    proxy = decode_str(arguments['proxy'])

    callback(identifier, 'running', None, callback_url)

    # Write proxy to file
    proxy_file = path.join(working_dir, 'proxy')
    with open(proxy_file, 'w') as f:
        f.write(proxy)

    # Process files partition by partition
    with Pool(processes=parallelism) as pool:
        partitions = create_partitions(files, partition_size)
        pool.map(download, partitions)

    callback(identifier, 'done', None, callback_url)

    # Cleanup
    remove(proxy_file)
