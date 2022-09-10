import logging

from flask import request
from flask_restx import Resource, Namespace

logger = logging.getLogger('tivos')

api = Namespace('1/tivos', description='Access to the tivo api')


@api.route('')
class Tivos(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__controller = kwargs['tivoController']

    def get(self):
        return self.__controller.tivos

    def put(self):
        payload = request.get_json()
        type = payload['type']
        name = payload['name']
        command = payload['command']
        logger.debug('Sending ' + type + '/' + command + ' to ' + name)
        if self.__controller.has_tivo(name):
            try:
                sent = self.__controller.send(name, type, command)
                # sent: [] of commands, channel: current channel text, type, name, command
                return {**sent, **payload}, 200
            except Exception as e:
                return {'error': str(e), **payload}, 500
        else:
            return 404
