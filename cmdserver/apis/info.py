import logging

from flask_restx import Resource, Namespace

from cmdserver.jvccommands import get_all_command_info

logger = logging.getLogger('info')

api = Namespace('1/info', description='Gets info about what is playing now')


@api.route('')
class Info(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pj_controller = kwargs['pj_controller']
        self.__supported = get_all_command_info()

    def get(self):
        if self.__supported is None:
            return None, 500
        else:
            return self.__supported, 200
