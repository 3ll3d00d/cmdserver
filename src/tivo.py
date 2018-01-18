import logging

from flask import request
from flask_restful import Resource

logger = logging.getLogger('cmdserver.tivo')


class Tivo(Resource):

    def __init__(self, **kwargs):
        self._tivoController = kwargs['tivoController']

    def get(self):
        return self._tivoController.getTivos()

    def put(self):
        payload = request.get_json()
        type = payload['type']
        name = payload['name']
        command = payload['command']
        logger.debug('Sending ' + type + '/' + command + ' to ' + name)
        if self._tivoController.hasTivo(name):
            try:
                sent = self._tivoController.send(name, type, command)
                # sent: [] of commands, channel: current channel text, type, name, command
                return {**sent, **payload}, 200
            except Exception as e:
                return {'error': str(e), **payload}, 500
        else:
            return 404
