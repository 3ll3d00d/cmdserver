import logging

from flask import request
from flask_restful import Resource

from jvccommands import get_all_command_info

logger = logging.getLogger('pyjvcpj.pj')


class Info(Resource):

    def __init__(self, **kwargs):
        self.__pj_controller = kwargs['pj_controller']
        self.__supported = get_all_command_info()

    def get(self):
        if self.__supported is None:
            return None, 500
        else:
            return self.__supported, 200


class PJ(Resource):
    def __init__(self, **kwargs):
        self.__pj_controller = kwargs['pj_controller']

    def get(self, command):
        logger.info(f"GET {command}")
        result = self.__pj_controller.get(command)
        if result is None:
            return None, 404
        else:
            return result, 200


class UpdatePJ(Resource):
    def __init__(self, **kwargs):
        self.__pj_controller = kwargs['pj_controller']

    def put(self):
        payload = request.get_json()
        logger.info(f"Executing {payload}")
        result = self.__pj_controller.send(payload)
        if result is None:
            logger.info(f"Unknown command {payload}")
            return None, 404
        else:
            return None, 200
