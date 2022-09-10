import logging

import requests
from plumbum import local


logger = logging.getLogger('commandcontroller')


class CommandController:

    def __init__(self, config):
        actual_commands = {commandId: command for commandId, command in config.commands.items() if commandId != 'defaults'}
        defaults = config.commands['defaults'] if 'defaults' in config.commands else None
        self.__commands = {command_id: self.__add_defaults(command_id, command, defaults) for command_id, command in actual_commands.items()}
        self.__launchers = {command_id: self.__get_launcher(command_id, command, defaults) for command_id, command in actual_commands.items()}

    @staticmethod
    def __add_defaults(command_id, command, defaults):
        if 'icon' not in command:
            command['icon'] = command_id + '.ico'
        if 'zoneId' not in command and 'zoneId' in defaults:
            command['zoneId'] = defaults['zoneId']
        if 'volume' not in command and 'volume' in defaults:
            command['volume'] = defaults['volume']
        if 'stopAll' not in command and 'stopAll' in defaults:
            command['stopAll'] = defaults['stopAll']
        return command

    @staticmethod
    def __get_launcher(command_id, command, defaults):
        if 'remote' in command:
            return RemoteCommandExecutor(f"{defaults['remote_prefix']}/{command_id}")
        else:
            exe = defaults['exe'] if defaults is not None and 'exe' in defaults else command['exe']
            return local[exe][command['args']] if 'args' in command else local[exe]

    @property
    def commands(self):
        return self.__commands

    def get_command(self, command_id):
        return self.__commands[command_id] if command_id in self.__commands else None

    def execute(self, command_id):
        command = self.get_command(command_id)
        if command is not None:
            result = self.__launchers[command_id]['executor'].run(retcode=None)
            logger.info(f"Executed command {command_id}, result is {result[0]}")
            logger.info('Command output: ')
            logger.info(result[1])
            return result
        return None


class RemoteCommandExecutor:

    def __init__(self, address: str):
        self.__address = address
        logger.info(f"Created RemoteCommandExecutor for {self.__address}")

    def __getitem__(self, item):
        # hack to allow the execute command to work as expected
        return self

    def run(self, **kwargs):
        r = requests.put(self.__address)
        if r.status_code == 200:
            return [0, '']
        else:
            return [2, f"{r.status_code} - {r.text}"]
