import itertools
import json
import queue
import random
import string
import sys
import time

import paho.mqtt.client as mqtt
from decouple import config

KPC_HOST = config('KPC_HOST', cast=str)
KPC_PORT = config('KPC_PORT', cast=int)

APPLICATION_VERSION = config('APPLICATION_VERSION', cast=str)
ENDPOINT_TOKEN = config('ENDPOINT_TOKEN', cast=str)


class MetadataClient:

    def __init__(self, client):
        self.client = client
        self.metadata_by_request_id = {}
        self.global_request_id = itertools.count()
        get_metadata_subscribe_topic = f'kp1/{APPLICATION_VERSION}/epmx/{ENDPOINT_TOKEN}/get/#'
        self.client.message_callback_add(get_metadata_subscribe_topic, self.handle_metadata)

    def handle_metadata(self, client, userdata, message):
        request_id = int(message.topic.split('/')[-2])
        if message.topic.split('/')[-1] == 'status' and request_id in self.metadata_by_request_id:
            print(f'<--- Received metadata response on topic {message.topic}')
            metadata_queue = self.metadata_by_request_id[request_id]
            metadata_queue.put_nowait(message.payload)
        else:
            print(
                f'<--- Received bad metadata response on topic {message.topic}:\n{str(message.payload.decode("utf-8"))}')

    def get_metadata(self):
        request_id = next(self.global_request_id)
        get_metadata_publish_topic = f'kp1/{APPLICATION_VERSION}/epmx/{ENDPOINT_TOKEN}/get/{request_id}'

        metadata_queue = queue.Queue()
        self.metadata_by_request_id[request_id] = metadata_queue

        print(f'---> Requesting metadata by topic {get_metadata_publish_topic}')
        self.client.publish(topic=get_metadata_publish_topic, payload=json.dumps({}))
        try:
            metadata = metadata_queue.get(True, 5)
            del self.metadata_by_request_id[request_id]
            return str(metadata.decode("utf-8"))
        except queue.Empty:
            print('Timed out waiting for metadata response from server')
            sys.exit()

    def patch_metadata_unconfirmed(self, metadata):
        partial_metadata_udpate_publish_topic = f'kp1/{APPLICATION_VERSION}/epmx/{ENDPOINT_TOKEN}/update/keys'

        print(f'---> Reporting metadata on topic {partial_metadata_udpate_publish_topic}\nwith payload {metadata}')
        self.client.publish(topic=partial_metadata_udpate_publish_topic, payload=metadata)


def main():
    # Iniciar la conexion con el servidor
    print(
        f'Connecting to Kaa server at {KPC_HOST}:{KPC_PORT} using application version {APPLICATION_VERSION} and endpoint token {ENDPOINT_TOKEN}')

    client_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    client = mqtt.Client(client_id=client_id)
    client.connect(KPC_HOST, KPC_PORT, 60)
    client.loop_start()

    metadata_client = MetadataClient(client)

    # Obtener los atributos de los metadatos del endpoint actual
    retrieved_metadata = metadata_client.get_metadata()
    print(f'Retrieved metadata from server: {retrieved_metadata}')

    # Actualizar parcialmente los metadatos del endpoint
    metadata_to_report = json.dumps({"model": "BFG 9001", "mac": "00-15-22-02-23-45"})
    metadata_client.patch_metadata_unconfirmed(metadata_to_report)

    time.sleep(5)
    client.disconnect()


if __name__ == '__main__':
    main()
