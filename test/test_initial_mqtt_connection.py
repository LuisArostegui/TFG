import unittest
import json
import random
import string
import sys
import time

import paho.mqtt.client as mqtt

# Paths Configuration
sys.path.append('./')
sys.path.append('./dasiot/')

from dasiot.initial_mqtt_connection import MetadataClient, KPC_PORT, KPC_HOST

def current_data(metadata_client):
    retrieved_metadata = metadata_client.get_metadata()
    return retrieved_metadata

def expected_data():
    data = json.dumps({"model":"BFG 9001","mac":"00-14-22-02-23-45"})
    string_data = str(data).casefold()
    string_data = string_data.replace(" ", "")
    return string_data


class TestDASIoT(unittest.TestCase):

    def test_update_device(self):
        client_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        client = mqtt.Client(client_id=client_id)
        client.connect(KPC_HOST, KPC_PORT, 60)
        client.loop_start()

        metadata_client = MetadataClient(client)

        # Actualización de datos
        metadata_to_report = json.dumps({"model": "BFG 9001", "mac": "00-14-22-02-23-45"})
        metadata_client.patch_metadata_unconfirmed(metadata_to_report)

        # Obtener datos actualizados
        current = current_data(metadata_client).casefold()
        current = current.replace(" ", "")

        assert current == expected_data()

        time.sleep(5)
        client.disconnect()
