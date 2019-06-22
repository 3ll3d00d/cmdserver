import logging

from plumbum import local


logger = logging.getLogger('cmdserver.commandcontroller')


class CommandController:

    def __init__(self, config):
        actual_commands = {commandId: command for commandId, command in config.commands.items() if commandId != 'defaults'}
        defaults = config.commands['defaults'] if 'defaults' in config.commands else None
        self.__commands = {commandId: self.__add_defaults(commandId, command, defaults) for commandId, command in actual_commands.items()}
        self._launchers = {commandId: self.__get_launcher(command, defaults) for commandId, command in actual_commands.items()}

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
    def __get_launcher(command, defaults):
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
            result = self._launchers[command_id]['executor'].run(retcode=None)
            logger.info(f"Executed command {command_id}, result is {result[0]}")
            logger.info('Command output: ')
            logger.info(result[1])
            return result
        return None
