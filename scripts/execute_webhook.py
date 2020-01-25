from base64 import b64decode
from json import loads, dumps
from sys import argv
from urllib.request import Request, urlopen

def decode_dict(d):
    return loads(b64decode(d).decode('UTF-8'))

arguments = decode_dict(argv[1])
webhook = decode_dict(arguments['webhook'])

url = webhook['url']
data = dumps(webhook['response']).encode('UTF-8')
headers = webhook['headers']
headers['Content-Type'] = 'application/json'

req = Request(url, data, headers)

try:
    res = urlopen(req)
    print('Executed webhook with url: ' + url)
except:
    print('Failed to execute webhook with url: ' + url)