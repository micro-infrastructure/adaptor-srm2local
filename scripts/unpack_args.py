from base64 import b64decode
from json import loads
from zlib import decompress
from sys import argv
from os import path

def decode_dict(d):
    return loads(b64decode(d).decode('UTF-8'))

def decode_str(s):
    return decompress(b64decode(s)).decode('UTF-8')

arguments = decode_dict(argv[1])
destination = argv[2]

copyjobfile = decode_str(arguments['copyjobfile'])
proxy = decode_str(arguments['proxy'])

with open(path.join(destination, 'copyjobfile'), 'w') as f1:
    f1.write(copyjobfile)

with open(path.join(destination, 'proxy'), 'w') as f2:
    f2.write(proxy)
