from flask_restful import Resource

from plumbum import local


class PlayingNow(Resource):

    def __init__(self, **kwargs):
        config = kwargs['config']
        self._launcher = local[config.playingNowExe]
        self._byPlayingNowId = {value['playingNowId']: value['title']
                                for key, value in config.commands.items() if 'playingNowId' in value}

    def get(self):
        playingNow = self._launcher.run(retcode=None)
        playingNowId = playingNow[0]
        if playingNowId in self._byPlayingNowId:
            return self._byPlayingNowId[playingNowId], 200
        elif playingNowId == 0:
            return '', 200
        else:
            return playingNowId, 500
