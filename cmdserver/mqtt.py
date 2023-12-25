import logging

import paho.mqtt.client as mqtt

logger = logging.getLogger('mqtt')


class MQTT:
    def __init__(self, ip: str, port: int = 1883, user: str = None, cred: str = None):
        logger.info(f'Initialising MQTT client {ip}:{port}')
        self.__client = mqtt.Client(client_id='cmdserver')
        self.__client.on_connect = self.__on_connect
        self.__client.on_message = self.__on_message
        self.__client.on_disconnect = self.__on_disconnect
        if user and cred:
            self.__client.username_pw_set(user, password=cred)
        self.__client.enable_logger(logger)
        self.__client.connect_async(ip, port, 60)
        from twisted.internet import reactor
        reactor.callInThread(lambda: self.__client.loop_forever(timeout=5))

    def __on_connect(self, client, userdata, flags, rc):
        logger.info(f'Connected to MQTT [result: {rc}]')

    def __on_message(self, client, userdata, msg):
        logger.info(f'Received from {msg.topic} {msg.payload}')

    def __on_disconnect(self, client, userdata, rc):
        logger.warning(f'Disconnected from MQTT [result: {rc}]')

    def publish(self, source: str, payload):
        logger.info(f'Publishing {source} -- {payload}')
        self.__client.publish(f'cmdserver/{source}', qos=2, payload=payload)
