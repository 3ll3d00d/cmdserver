from flask_restful import Resource


class PlayingNow(Resource):

    # @marshal_with(targetStateFields)
    def get(self):
        return {}
