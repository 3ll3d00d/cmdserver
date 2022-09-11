import logging
import time

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
                return {'last': f'{time.time()}'}, 200
            else:
                return {'error': 'No MAC address'}, 501
        except Exception as e:
            return {'error': str(e)}, 500
