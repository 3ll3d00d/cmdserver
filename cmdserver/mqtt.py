import atexit
import logging
import socket

import paho.mqtt.client as mqtt

logger = logging.getLogger('mqtt')

SHUTDOWN_PUBLISH_TIMEOUT_SECS = 2.0


class MQTT:
    def __init__(self, ip: str, port: int = 1883, user: str = None, cred: str = None, will_source: str | None = 'pj'):
        client_id = f'cmdserver-{socket.gethostname()}'
        logger.info(f'Initialising MQTT client {client_id} to {ip}:{port}')
        self.__online: set[str] = set()
        self.__shut_down = False
        self.__client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.__client.on_connect = self.__on_connect
        self.__client.on_message = self.__on_message
        self.__client.on_disconnect = self.__on_disconnect
        if user and cred:
            self.__client.username_pw_set(user, password=cred)
        if will_source:
            # if cmdserver dies without a clean shutdown, the broker tells subscribers it is no longer available
            self.__client.will_set(self.__topic(f'{will_source}/available'), 'offline', qos=1, retain=True)
        self.__client.enable_logger(logger)
        self.__client.connect_async(ip, port, 60)
        self.__client.loop_start()
        atexit.register(self.shutdown)

    def shutdown(self):
        if self.__shut_down:
            return
        self.__shut_down = True
        logger.info('Shutting down MQTT client')
        if self.__client.is_connected():
            pending = [self.__publish(f'{source}/available', 'offline') for source in sorted(self.__online)]
            for info in pending:
                try:
                    info.wait_for_publish(timeout=SHUTDOWN_PUBLISH_TIMEOUT_SECS)
                except (ValueError, RuntimeError) as e:
                    logger.warning(f'Unable to publish offline state on shutdown: {e}')
            self.__client.disconnect()
        self.__client.loop_stop()

    def __on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error(f'Failed to connect to MQTT [result: {reason_code}]')
        else:
            logger.info(f'Connected to MQTT [result: {reason_code}]')

    def __on_message(self, client, userdata, msg):
        logger.info(f'Received from {msg.topic} {msg.payload}')

    def __on_disconnect(self, client, userdata, flags, reason_code, properties):
        logger.warning(f'Disconnected from MQTT [result: {reason_code}]')

    @staticmethod
    def __topic(suffix: str) -> str:
        return f'cmdserver/{suffix}'

    def __publish(self, source: str, payload) -> mqtt.MQTTMessageInfo:
        logger.info(f'Publishing {source} -- {payload}')
        return self.__client.publish(self.__topic(source), qos=1, payload=payload, retain=True)

    def state(self, source: str, payload):
        self.__publish(f'{source}/state', payload)

    def attributes(self, source: str, payload):
        self.__publish(f'{source}/attributes', payload)

    def online(self, source: str):
        self.__online.add(source)
        self.__publish(f'{source}/available', 'online')

    def offline(self, source: str):
        self.__online.discard(source)
        self.__publish(f'{source}/available', 'offline')
