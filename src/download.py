from base64 import b64decode
from json import dumps, loads
from zlib import decompress
from subprocess import run
from sys import argv, exc_info
from os import path, remove

def decode_dict(d):
    return loads(b64decode(d).decode('UTF-8'))


def decode_str(s):
    return decompress(b64decode(s)).decode('UTF-8')


def post_json(payload, url):
    data = dumps(payload).encode('UTF-8')
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        request = Request(url, data, headers)
        urlopen(req)
    except:
        print('Failed to post JSON to: ' + url)


def create_copyjob(paths):
    src_dest = [join(f'{path} file:////local/', basename(path)) for path in paths]
    return base64_str('\n'.join(src_dest))


def create_partition(list, n):
    if list == []:
        return

    yield list[:n]
    yield from create_partition(list[n:], n)


def update_status(identifier, status, files, callback_url):
    payload = {
        'identifier': identifier,
        'status': status,
        'files': files
    }
    post_json(payload, callback_url)


if __name__ == '__main__':
    arguments = decode_dict(argv[1])
    working_dir = argv[2]

    # Unpack arguments
    callback_url = arguments['callback_url']
    destination = arguments['destination']
    files = arguments['files']
    identifier = arguments['identifier']
    parallelism = arguments['parallelism']
    partition_size = arguments['partition_size']
    proxy = decode_str(arguments['proxy'])

    # Write proxy to file
    proxy_file = path.join(working_dir, 'proxy')
    with open(proxy_file, 'w') as f:
        f.write(proxy)

    # Process files partition by partition
    for (p, partition) in enumerate(create_partition(files, partition_size)):
        copyjob = create_copyjob(partition)
        copyjob_file = path.join(destination, f'copyjob_{p}')

        # Write copyjob to file
        with open(copyjob_file, 'w') as f:
            f.write(copyjob)

        command = [
            'srmcp',
            '-debug',
            '-use_urlcopy_script=true',
            '-urlcopy=/var/local/lta-url-copy.sh',
            '-server_mode=passive',
            f'-x509_user_proxy={proxy_file}',
            f'-copyjobfile={copyjob_file}'
        ]

        try:
            update_status(identifier, 'downloading', partition, callback_url)
            run(command, env={ 'parallelism': parallelism })
            update_status(identifier, 'complete' partition, callback_url)
        except:
            update_status(identifier, 'failed', partition, callback_url)

        # Cleanup
        remove(copyjob_file)

    # Cleanup
    remove(proxy_file)
