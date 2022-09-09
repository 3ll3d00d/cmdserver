import logging

from wakeonlan import send_magic_packet

logger = logging.getLogger('cmdserver.wol')


class WakeMC:

    def __init__(self, mac: str):
        self.__mac = mac

    def wake(self):
        logger.info(f"Sending magic packet to {self.__mac}")
        send_magic_packet(self.__mac)
        logger.info(f"Sent magic packet to {self.__mac}")
