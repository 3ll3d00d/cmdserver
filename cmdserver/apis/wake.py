import logging

from flask_restx import Resource, Namespace

from cmdserver.infoprovider import InfoProvider

logger = logging.getLogger('wake')

api = Namespace('1/wake', description='Sends a WOL to the target MC server')


@api.route('')
class Wake(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__info_provider: InfoProvider = kwargs['info_provider']

    def get(self):
        try:
            if self.__info_provider.wake():
                return '', 200
            else:
                return 'No MAC address', 400
        except Exception as e:
            return str(e), 500
