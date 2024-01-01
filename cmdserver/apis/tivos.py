import logging
import time

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
        start = time.time()
        logger.debug('Sending ' + type + '/' + command + ' to ' + name)
        if self.__controller.has_tivo(name):
            try:
                sent = self.__controller.send(name, type, command)
                end = time.time()
                # sent: [] of commands, channel: current channel text, type, name, command
                logger.debug(f'Responding with {sent} in {round((end-start) / 1000, 3)} ms')
                return {**sent, **payload}, 200
            except Exception as e:
                return {'error': str(e), **payload}, 500
        else:
            return 404
