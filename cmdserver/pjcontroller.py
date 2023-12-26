import json
import logging
from enum import Enum
from threading import Lock
from time import sleep
from typing import Optional

from cmdserver.debounce import debounce
from cmdserver.jvc import CommandExecutor, CommandNack
from cmdserver.jvccommands import Command, load_all_commands, Numeric, PictureMode, Anamorphic, PowerState, \
    InstallationMode
from cmdserver.mqtt import MQTT

logger = logging.getLogger('pjcontroller')


class PJController:

    def __init__(self, config, mqtt: Optional[MQTT]):
        self.__pj_macros = config.pj_macros
        self.__mqtt = mqtt
        self.__executor = CommandExecutor(host=config.pj_ip) if config.pj_ip else None
        self.__commands = load_all_commands()
        self.__lock = Lock()
        self.__state = {
            'powerState': '',
            'anamorphicMode': '',
            'installationMode': '',
            'pictureMode': '',
            'power': False,
            'hdr': '',
            'anamorphic': ''
        }
        if mqtt:
            from twisted.internet import reactor
            reactor.callLater(0.5, self.__update_state)

    def __update_state(self):
        updated = False
        with self.__lock:
            cmd = Command.Power
            try:
                self.__connect()
                power = self.__executor.get(cmd)
                if power == PowerState.LampOn:
                    cmd = Command.Anamorphic
                    ana = self.__executor.get(cmd)
                    cmd = Command.PictureMode
                    pic = self.__executor.get(cmd)
                    cmd = Command.InstallationMode
                    install = self.__executor.get(cmd)
                    self.__state = {
                        'powerState': power.name,
                        'anamorphicMode': ana.name,
                        'installationMode': install.name,
                        'pictureMode': pic.name,
                        'power': power == PowerState.LampOn,
                        'hdr': pic == PictureMode.User5,
                        'anamorphic': 'A' if ana == Anamorphic.A else 'B' if install == InstallationMode.TWO else None
                    }
                    self.__mqtt.online('pj')
                    self.__mqtt.publish('pj/state', power.name)
                    self.__mqtt.publish('pj/attributes', json.dumps(self.__state))
                else:
                    self.__state = {**self.__state, 'powerState': power.name}
                    self.__mqtt.offline('pj')
                updated = True
                self.__disconnect()
            except CommandNack:
                logger.exception(f"Command NACKed - GET {cmd}")
            except:
                logger.exception(f"Unexpected failure while executing cmd: {cmd}")
                return -1
        from twisted.internet import reactor
        reactor.callLater(0.5 if not updated else 30, self.__update_state)

    @property
    def state(self):
        return self.__state

    @property
    def enabled(self):
        return self.__executor is not None

    def __connect(self):
        self.__executor.connect()

    @debounce(4)
    def __disconnect(self):
        self.__executor.disconnect(fail=False)

    def get(self, command):
        with self.__lock:
            try:
                cmd = Command[command]
                self.__connect()
                val = self.__executor.get(cmd)
                self.__disconnect()
                if val is not None:
                    return val.name if isinstance(val, Enum) else val.replace('"', '').strip()
                return val
            except KeyError:
                logger.warning(f"Ignoring unknown command {command}")
                return None
            except CommandNack:
                logger.exception(f"Command NACKed - GET {command}")
                return -1
            except:
                logger.exception(f"Unexpected failure while executing cmd: {command}")
                return -1

    def send(self, commands):
        """ Sends the commands to the PJ """
        with self.__lock:
            vals = []
            self.__connect()
            for command in commands:
                if command[0:5] == 'PAUSE':
                    sleep_secs = float(command[5:])
                    logger.info(f"Sleeping for {sleep_secs:.3f}")
                    sleep(sleep_secs)
                else:
                    if command in self.__pj_macros:
                        for cmd in self.__pj_macros[command]:
                            vals.append(self.__execute(cmd))
                    else:
                        vals.append(self.__execute(command))
            self.__disconnect()
            return vals

    def __execute(self, cmd):
        tokens = cmd.split('.')
        if len(tokens) > 1:
            try:
                cmd_enum = Command[tokens[0]]
                if isinstance(cmd_enum.value, tuple):
                    cmd_arg_enum = cmd_enum.value[1]
                    if cmd_arg_enum.__name__ == tokens[1]:
                        logger.info(f"Executing {cmd}")
                        if issubclass(cmd_arg_enum, Enum):
                            return self.__executor.set(cmd_enum, cmd_arg_enum[tokens[2]])
                        elif issubclass(cmd_arg_enum, Numeric):
                            return self.__executor.set(cmd_enum, Numeric(int(tokens[2])))
                        else:
                            logger.warning(f"Unsupported value type for {cmd} - {cmd_arg_enum.__name__}")
            except (AttributeError, KeyError):
                logger.exception(f"Ignoring unknown command {cmd}")
            except:
                logger.exception(f"Unexpected exception while processing {cmd}")
        else:
            logger.error(f"Ignoring unknown command {cmd}")
