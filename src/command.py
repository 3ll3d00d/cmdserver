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
        result = self._commandController.executeCommand(command)
        if result is None:
            return None, 404
        else:
            if result[0] == 0:
                return None, 200
            else:
                return {'errorCode': result[0]}, 500
