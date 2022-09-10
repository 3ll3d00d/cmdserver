import logging

from flask_restx import Resource, Namespace

logger = logging.getLogger('tivo')

api = Namespace('1/tivo', description='Gets info about a named tivo')


@api.route('/<string:tivo>')
class Tivo(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__controller = kwargs['tivoController']

    def get(self, tivo):
        tivo = self.__controller.get_tivo(tivo)
        if tivo is None:
            return 404
        else:
            return {'channel': tivo.currentChannel, 'messages': tivo.messages, 'connected': tivo.connected}, 200
