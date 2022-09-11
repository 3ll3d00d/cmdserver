import logging
from enum import Enum
from threading import Lock
from time import sleep

from cmdserver.debounce import debounce
from cmdserver.jvc import CommandExecutor, CommandNack
from cmdserver.jvccommands import Command, load_all_commands, Numeric

logger = logging.getLogger('pjcontroller')


class PJController:

    def __init__(self, config):
        self.__pj_macros = config.pj_macros
        self.__executor = CommandExecutor(host=config.pj_ip) if config.pj_ip else None
        self.__commands = load_all_commands()
        self.__lock = Lock()

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
