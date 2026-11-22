import logging

from flask import request
from flask_restx import Resource, Namespace

from cmdserver.pjcontroller import PJController

logger = logging.getLogger('pj')

api = Namespace('1/pj', description='Controls a JVC PJ')


@api.route('/<string:command>')
class PJ(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pj_controller: PJController = kwargs['pj_controller']

    def get(self, command):
        if self.__pj_controller.enabled:
            logger.info(f">> GET {command}")
            result = self.__pj_controller.get(command)
            logger.info(f"<< GET {command} = {result}")
            if result is None:
                return None, 404
            elif result == -1:
                return None, 500
            else:
                return result, 200
        else:
            return None, 501


@api.route('')
class UpdatePJ(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pj_controller: PJController = kwargs['pj_controller']

    def put(self):
        if self.__pj_controller.enabled:
            payload = request.get_json()
            logger.info(f"Executing {payload}")
            result = self.__pj_controller.send(payload)
            if result.failed:
                # the PJ refused or never acknowledged a command, even after retries
                return {'failed': result.failed, 'unknown': result.unknown, 'errors': result.errors}, 500
            if result.unknown:
                logger.info(f"Unknown command(s) {result.unknown}")
                return {'unknown': result.unknown}, 404
            return None, 200
        else:
            return None, 501
