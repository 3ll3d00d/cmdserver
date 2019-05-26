import logging
from flask_restful import Resource

from plumbum import local

logger = logging.getLogger('cmdserver.playingnow')


class PlayingNow(Resource):

    def __init__(self, **kwargs):
        config = kwargs['config']
        self._launcher = local[config.playingNowExe]
        self._byPlayingNowId = {value['playingNowId']: value['title']
                                for key, value in config.commands.items() if 'playingNowId' in value}

    def get(self):
        playing_now = self._launcher.run(retcode=None)
        playing_now_id = playing_now[0]
        logger.debug("playingNow:" + str(playing_now_id))
        if playing_now_id in self._byPlayingNowId:
            return {'title': self._byPlayingNowId[playing_now_id]}, 200
        elif playing_now_id == 0:
            return {'title': ''}, 200
        else:
            return {'id': playing_now_id}, 500
