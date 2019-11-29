from json import dumps, loads
from os import environ
from threading import Thread

from flask import Flask, request
from pika import BlockingConnection, ConnectionParameters
from pickledb import load as pickle

from helpers import json_respone
from srm2local import execute_entrypoint

### Config

amqp_host = environ.get('AMQP_HOST')
amqp_exchange = 'function_proxy'
amqp_routingkey = 'functions.srm2local.*'

db = pickle('srm2local.db', False)

### Shared Entrypoints (Pika/Flask) 

functions = {
    'execute': execute_entrypoint,
}

### Pika

if amqp_host is not None:
    connection = BlockingConnection(ConnectionParameters(host=amqp_host))
    channel = connection.channel()
    channel.exchange_declare(amqp_exchange, 'topic')

    result = channel.queue_declare(queue='', exclusive=True)
    queue = result.method.queue
    channel.queue_bind(queue, amqp_exchange, amqp_routingkey)

    def callback(_ch, method, properties, message):
        print(f'Incoming AMQP message: {message}.')

        message = loads(message)
        function_name = method.routing_key.split('.')[-1]

        function = functions[function_name]
        result, status = function(message['body'], db)

        # Reply to sender over message queue
        reply = dumps({
            'id': message['id'],
            'status': status,
            'body': result,
        })
        channel.basic_publish(amqp_exchange, message['replyTo'], reply)

    channel.basic_consume(queue, callback, auto_ack=True)

### Flask

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute():
    payload = request.get_json()
    result, status = functions.get('execute')(payload, db)

    return json_respone(result, status)

### Main

if __name__ == '__main__':
    if amqp_host is not None:
        # Listen for AMQP messages in the background
        Thread(target=channel.start_consuming).start()

    app.run(host='0.0.0.0', threaded=True)
