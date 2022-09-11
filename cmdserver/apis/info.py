import logging

from flask_restx import Resource, Namespace

from cmdserver.jvccommands import get_all_command_info
from cmdserver.pjcontroller import PJController

logger = logging.getLogger('info')

api = Namespace('1/info', description='Gets info about commands supported by the pj (if any)')


@api.route('')
class Info(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pj_controller: PJController = kwargs['pj_controller']
        self.__supported = get_all_command_info() if self.__pj_controller.enabled else []

    def get(self):
        if self.__supported is None:
            return None, 500
        else:
            return self.__supported, 200
