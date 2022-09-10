import logging

from flask_restx import Resource, Namespace

from cmdserver.infoprovider import InfoProvider

logger = logging.getLogger('playingnow')

api = Namespace('1/playingnow', description='Gets info about what is playing now')


@api.route('')
class PlayingNow(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__info_provider: InfoProvider = kwargs['info_provider']

    def get(self):
        return self.__info_provider.info, 200
