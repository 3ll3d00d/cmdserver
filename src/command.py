import logging

from flask_restx import Resource

logger = logging.getLogger('cmdserver.command')


class Commands(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__controller = kwargs['command_controller']

    def get(self):
        return {'commands': self.__controller.commands}


class Command(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__controller = kwargs['command_controller']

    def put(self, command):
        logger.info('Executing ' + command)
        result = self.__controller.execute(command)
        if result is None:
            logger.info('Executed ' + command + ' successfully')
            return None, 404
        else:
            if result[0] == 0:
                logger.info('Executed ' + command + ' successfully')
                return None, 200
            else:
                logger.info('Executed ' + command + ' with unexpected result ' + result[0])
                return {'errorCode': result[0]}, 500
