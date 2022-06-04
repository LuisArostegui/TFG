import json
import signal
import time

from gpiozero import LED, CPUTemperature


def temp_data():
    cpu = CPUTemperature()
    return cpu.temperature


class KaaClient:

    def __init__(self, client, app_version, endpoint_token, host, port):
        self.client = client
        self.app_version = app_version
        self.endpoint_token = endpoint_token
        self.host = host
        self.port = port
        self.metadata_update_topic = f'kp1/{self.app_version}/epmx/{self.endpoint_token}/update/keys'
        self.data_collection_topic = f'kp1/{self.app_version}/dcx/{self.endpoint_token}/json'

        self.led = LED(17)

        command_turn_on_topic = f'kp1/{self.app_version}/cex/{self.endpoint_token}/command/turnon/status'
        self.client.message_callback_add(command_turn_on_topic, self.handle_turn_on_command)
        self.command_turn_on_result_topik = f'kp1/{self.app_version}/cex/{self.endpoint_token}/result/turnon'

        command_turn_off_topic = f'kp1/{self.app_version}/cex/{self.endpoint_token}/command/turnoff/status'
        self.client.message_callback_add(command_turn_off_topic, self.handle_turn_off_command)
        self.command_turn_off_result_topik = f'kp1/{self.app_version}/cex/{self.endpoint_token}/result/turnoff'

    def connect_to_server(self):
        print(
            f'Connecting to Kaa server at {self.host}:{self.port} using application version {self.app_version}'
            f' and endpoint token {self.endpoint_token}')
        self.client.connect(self.host, self.port, 60)
        print('Successfully connected')

    def disconnect_from_server(self):
        print(f'Disconnecting from Kaa server at {self.host}:{self.port}...')
        self.client.loop_stop()
        self.client.disconnect()
        print('Successfully disconnected')

    def compose_data_sample(self):
        return json.dumps([
            {
                "timestamp": int(round(time.time() * 1000)),
                "temperature": int(temp_data())
            }
        ])

    def on_message(client, userdata, message):
        print(f'<-- Received message on topic "{message.topic}":\n{str(message.payload.decode("utf-8"))}')

    def handle_turn_on_command(self, client, userdata, message):
        print(f'<--- Received "turn on" command on topic {message.topic} \nTurning on...')
        self.led.on()
        command_result = self.compose_command_result_payload(message)
        print(f'command result {command_result}')
        client.publish(topic=self.command_turn_on_result_topik, payload=command_result)
        # With below approach we don't receive the command confirmation on the server side.
        # self.client.disconnect()
        # time.sleep(5)  # Simulate the reboot
        # self.connect_to_server()

    def handle_turn_off_command(self, client, userdata, message):
        print(f'<--- Received "turn on" command on topic {message.topic} \nTurning off...')
        self.led.off()
        command_result = self.compose_command_result_payload(message)
        print(f'command result {command_result}')
        client.publish(topic=self.command_turn_on_result_topik, payload=command_result)

    def compose_command_result_payload(self, message):
        command_payload = json.loads(str(message.payload.decode("utf-8")))
        print(f'command payload: {command_payload}')
        command_result_list = []
        for command in command_payload:
            commandResult = {"id": command['id'], "statusCode": 200, "reasonPhrase": "OK", "payload": "Success"}
            command_result_list.append(commandResult)
        return json.dumps(
            command_result_list
        )


class SignalListener:
    keepRunning = True

    def __init__(self):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def stop(self, signum, frame):
        print('Shutting down...')
        self.keepRunning = False
