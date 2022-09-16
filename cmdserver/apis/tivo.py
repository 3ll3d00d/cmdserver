import logging

from flask_restx import Resource, Namespace
from cmdserver.tivocontroller import Tivo as tivo_data

logger = logging.getLogger('tivo')

api = Namespace('1/tivo', description='Gets info about a named tivo')


@api.route('/<string:tivo_name>')
class Tivo(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__controller = kwargs['tivoController']

    def get(self, tivo_name):
        tivo: tivo_data = self.__controller.get_tivo(tivo_name)
        if tivo is None:
            return 404
        else:
            return {'channel': tivo.current_channel, 'messages': tivo.messages, 'connected': tivo.connected}, 200
