import logging

from flask import request
from flask_restful import Resource

logger = logging.getLogger('cmdserver.pj')


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
            # if result[0] == 0:
            #     logger.info('Executed ' + command + ' successfully')
            #     return None, 200
            # else:
            #     logger.info('Executed ' + command + ' with unexpected result ' + result[0])
            #     return {'errorCode': result[0]}, 500
