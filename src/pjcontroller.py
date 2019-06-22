import logging
from enum import Enum

from debounce import debounce
from jvc import CommandExecutor
from jvccommands import Command, PowerState, load_all_commands

logger = logging.getLogger('cmdserver.pjcontroller')


class PJController:

    def __init__(self, config):
        self.__pj_macros = config.pj_macros
        self.__executor = CommandExecutor(host=config.pj_ip)
        self.__commands = load_all_commands()

    def __connect(self):
        self.__executor.connect()

    @debounce(4)
    def __disconnect(self):
        self.__executor.disconnect(fail=False)

    def get(self, command):
        try:
            cmd = Command[command]
            self.__connect()
            val = self.__executor.get(cmd)
            self.__disconnect()
            if val is not None and isinstance(val, Enum):
                return val.name
            return val
        except KeyError:
            logger.warning(f"Ignoring unknown command {command}")
            return None
        except:
            logger.exception(f"Unexpected failure while executing {command}")
            return None

    def send(self, commands):
        """ Sends the commands to the PJ """
        vals = []
        self.__connect()
        for command in commands:
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
                if len(cmd_enum.value) == 2:
                    cmd_arg_enum = cmd_enum.value[1]
                    if cmd_arg_enum.__name__ == tokens[1]:
                        logger.info(f"Executing {cmd}")
                        return self.__executor.set(cmd_enum, cmd_arg_enum[tokens[2]])
            except KeyError:
                logger.warning(f"Ignoring unknown command {cmd}")
            except:
                logger.exception(f"Unexpected exception while processing {cmd}")
        logger.error(f"Ignoring unknown command {cmd}")
