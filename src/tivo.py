import logging

from flask import request
from flask_restful import Resource

logger = logging.getLogger('cmdserver.tivo')


class Tivos(Resource):

    def __init__(self, **kwargs):
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


class Tivo(Resource):

    def __init__(self, **kwargs):
        self.__controller = kwargs['tivoController']

    def get(self, tivo):
        tivo = self.__controller.get_tivo(tivo)
        if tivo is None:
            return 404
        else:
            return {'channel': tivo.currentChannel, 'messages': tivo.messages, 'connected': tivo.connected}, 200
