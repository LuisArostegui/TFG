import itertools
import json
import queue
import sys
from subprocess import Popen, PIPE


class MetadataClient:

    def __init__(self, client, app_version, endpoint_token):
        self.client = client
        self.app_version = app_version
        self.endpoint_token = endpoint_token
        self.metadata_by_request_id = {}
        self.global_request_id = itertools.count()
        get_metadata_subscribe_topic = f'kp1/{self.app_version}/epmx/{self.endpoint_token}/get/#'
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
        get_metadata_publish_topic = f'kp1/{self.app_version}/epmx/{self.endpoint_token}/get/{request_id}'

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
        partial_metadata_update_publish_topic = f'kp1/{self.app_version}/epmx/{self.endpoint_token}/update/keys'

        print(f'---> Reporting metadata on topic {partial_metadata_update_publish_topic}\nwith payload {metadata}')
        self.client.publish(topic=partial_metadata_update_publish_topic, payload=metadata)

    def hardware_devices(self):
        return Popen(['lsusb'], stdout=PIPE, encoding='utf-8').communicate()[0]

    def set_metadata(self):
        metadata_to_report = json.dumps(
            {"model": "Raspberry PI",
             "mac": "b8-27-eb-f8-00-af",
             "devices": self.hardware_devices()
             }
        )
        return metadata_to_report

