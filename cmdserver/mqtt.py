import atexit
import logging

import paho.mqtt.client as mqtt

logger = logging.getLogger('mqtt')


class MQTT:
    def __init__(self, ip: str, port: int = 1883, user: str = None, cred: str = None):
        import socket
        hostname = socket.gethostname()
        client_id = f'cmdserver-{hostname}'
        logger.info(f'Initialising MQTT client {client_id} to {ip}:{port}')
        self.__client = mqtt.Client(client_id=client_id)
        self.__client.on_connect = self.__on_connect
        self.__client.on_message = self.__on_message
        self.__client.on_disconnect = self.__on_disconnect
        if user and cred:
            self.__client.username_pw_set(user, password=cred)
        self.__client.enable_logger(logger)
        self.__client.connect_async(ip, port, 60)
        self.__client.loop_start()
        import atexit
        atexit.register(self.shutdown)

    def shutdown(self):
        logger.info('Shutting down MQTT client')
        self.__client.loop_stop(force=True)

    def __on_connect(self, client, userdata, flags, rc):
        logger.info(f'Connected to MQTT [result: {rc}]')

    def __on_message(self, client, userdata, msg):
        logger.info(f'Received from {msg.topic} {msg.payload}')

    def __on_disconnect(self, client, userdata, rc):
        logger.warning(f'Disconnected from MQTT [result: {rc}]')

    def __publish(self, source: str, payload):
        logger.info(f'Publishing {source} -- {payload}')
        self.__client.publish(f'cmdserver/{source}', qos=1, payload=payload, retain=True)

    def state(self, source: str, payload):
        self.__publish(f'{source}/state', payload)

    def attributes(self, source: str, payload):
        self.__publish(f'{source}/attributes', payload)

    def online(self, source: str):
        self.__publish(f'{source}/available', 'online')

    def offline(self, source: str):
        self.__publish(f'{source}/available', 'offline')
