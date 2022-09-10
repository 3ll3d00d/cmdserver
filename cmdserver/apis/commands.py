import logging

from flask_restx import Resource, Namespace

logger = logging.getLogger('command')

api = Namespace('1/commands', description='States all configured commands')


@api.route('')
class Commands(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__controller = kwargs['command_controller']

    def get(self):
        return {'commands': self.__controller.commands}
