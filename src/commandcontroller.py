import logging

from plumbum import local

logger = logging.getLogger('cmdserver.commandcontroller')


class CommandController(object):

    def __init__(self, config):
        actualCommands = {commandId: command for commandId, command in config.commands.items() if commandId != 'defaults'}
        defaults = config.commands['defaults'] if 'defaults' in config.commands else None
        self._commands = {commandId: self._addDefaults(commandId, command, defaults) for commandId, command in actualCommands.items()}
        self._launchers = {commandId: self._getLauncher(command, defaults) for commandId, command in actualCommands.items()}

    def _addDefaults(self, commandId, command, defaults):
        if 'icon' not in command:
            command['icon'] = commandId + '.ico'
        if 'zoneId' not in command and 'zoneId' in defaults:
            command['zoneId'] = defaults['zoneId']
        if 'volume' not in command and 'volume' in defaults:
            command['volume'] = defaults['volume']
        if 'stopAll' not in command and 'stopAll' in defaults:
            command['stopAll'] = defaults['stopAll']
        return command

    def _getLauncher(self, command, defaults):
        exe = defaults['exe'] if defaults is not None and 'exe' in defaults else command['exe']
        return local[exe][command['args']] if 'args' in command else local[exe]

    def getCommands(self):
        return self._commands

    def getCommand(self, commandId):
        return self._commands[commandId] if commandId in self._commands else None

    def executeCommand(self, commandId):
        command = self.getCommand(commandId)
        if command is not None:
            result = self._launchers[commandId]['executor'].run(retcode=None)
            return result
        return None
