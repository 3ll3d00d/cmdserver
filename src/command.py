import logging

from flask_restful import Resource

logger = logging.getLogger('cmdserver.command')


class Commands(Resource):
    def __init__(self, **kwargs):
        self._commandController = kwargs['commandController']

    def get(self):
        return {'commands': self._commandController.getCommands()}


class Command(Resource):
    def __init__(self, **kwargs):
        self._commandController = kwargs['commandController']

    def put(self, command):
        logger.info('Executing ' + command)
        result = self._commandController.executeCommand(command)
        if result is None:
            logger.info('Executed ' + command + ' successfully')
            return None, 404
        else:
            if result[0] == 0:
                logger.info('Executed ' + command + ' successfully')
                return None, 200
            else:
                logger.info('Executed ' + command + ' with unexpected result ' + result[0])
                return {'errorCode': result[0]}, 500
