import faulthandler
import os
from os import path
from typing import Tuple

from autobahn.twisted.resource import WebSocketResource
from flask import Flask
from flask_restx import Api

from cmdserver.pjcontroller import PJController
from cmdserver.apis import command, commands, playingnow, tivo, tivos, pj, info, version, wake
from cmdserver.commandcontroller import CommandController
from cmdserver.config import Config
from cmdserver.infoprovider import InfoProvider
from cmdserver.tivocontroller import TivoController
from cmdserver.ws import WsServer
from cmdserver.mqtt import MQTT

API_PREFIX = '/api/1'

faulthandler.enable()
if hasattr(faulthandler, 'register'):
    import signal

    faulthandler.register(signal.SIGUSR2, all_threads=True)


def create_app(cfg: Config) -> Tuple[Flask, 'WsServer']:
    ws_server = WsServer()
    mqtt = None
    if cfg.mqtt:
        mqtt = MQTT(cfg.mqtt['ip'], cfg.mqtt.get('port', 1883), cfg.mqtt.get('user', None), cfg.mqtt.get('cred', None))
    info_provider = InfoProvider(cfg, ws_server, mqtt)
    resource_args = {
        'command_controller': CommandController(cfg),
        'tivoController': TivoController(cfg, mqtt),
        'pj_controller': PJController(cfg, mqtt),
        'info_provider': info_provider,
        'mqtt': mqtt,
        'config': cfg,
        'version': cfg.version
    }
    app = Flask('cmdserver')
    api = Api(app, prefix='/api', doc='/api/doc/', version=resource_args['version'], title='cmdserver',
              description='Backend api for cmdserver')

    def decorate_ns(ns, p=None):
        for r in ns.resources:
            r.kwargs['resource_class_kwargs'] = resource_args
        api.add_namespace(ns, path=p)

    decorate_ns(commands.api)
    decorate_ns(command.api)
    decorate_ns(playingnow.api)
    decorate_ns(tivos.api)
    decorate_ns(tivo.api)
    decorate_ns(info.api)
    decorate_ns(pj.api)
    decorate_ns(version.api)
    decorate_ns(wake.api)
    return app, ws_server


def main(args=None):
    """ The main routine. """
    cfg = Config('cmdserver')
    logger = cfg.configure_logger()
    app, ws_server = create_app(cfg)

    import logging
    logger = logging.getLogger('twisted')
    from twisted.internet import reactor
    from twisted.web.resource import Resource
    from twisted.web import static, server
    from twisted.web.wsgi import WSGIResource
    from twisted.application import service
    from twisted.internet import endpoints

    class ReactApp:
        """
        Handles the react app (excluding the static dir).
        """

        def __init__(self, path):
            # TODO allow this to load when in debug mode even if the files don't exist
            self.publicFiles = {f: static.File(os.path.join(path, f)) for f in os.listdir(path) if
                                os.path.exists(os.path.join(path, f))} if os.path.exists(path) else {}
            self.indexHtml = ReactIndex(os.path.join(path, 'index.html'))

        def get_file(self, path):
            """
            overrides getChild so it always just serves index.html unless the file does actually exist (i.e. is an
            icon or something like that)
            """
            return self.publicFiles.get(path.decode('utf-8'), self.indexHtml)

    class ReactIndex(static.File):
        """
        a twisted File which overrides getChild so it always just serves index.html (NB: this is a bit of a hack,
        there is probably a more correct way to do this but...)
        """

        def getChild(self, path, request):
            return self

    class FlaskAppWrapper(Resource):
        """
        wraps the flask app as a WSGI resource while allow the react index.html (and its associated static content)
        to be served as the default page.
        """

        def __init__(self):
            super().__init__()
            self.wsgi = WSGIResource(reactor, reactor.getThreadPool(), app)
            import sys
            if getattr(sys, 'frozen', False):
                # pyinstaller lets you copy files to arbitrary locations under the _MEIPASS root dir
                uiRoot = os.path.join(sys._MEIPASS, 'ui')
            elif cfg.webappPath is not None:
                uiRoot = cfg.webappPath
            else:
                # release script moves the ui under the analyser package because setuptools doesn't seem to include
                # files from outside the package
                uiRoot = os.path.join(os.path.dirname(__file__), 'ui')
            if os.path.exists(uiRoot):
                logger.info(f'Serving ui from {uiRoot}')
            else:
                logger.info('No UI, API only')
            self.react = ReactApp(uiRoot)
            self.static = static.File(os.path.join(uiRoot, 'static'))
            self.icons = static.File(cfg.iconPath)
            ws_server.factory.startFactory()
            self.ws_resource = WebSocketResource(ws_server.factory)

        def getChild(self, path, request):
            """
            Overrides getChild to allow the request to be routed to the wsgi app (i.e. flask for the rest api
            calls), the static dir (i.e. for the packaged css/js etc), the various concrete files (i.e. the public
            dir from react-app), the command icons or to index.html (i.e. the react app) for everything else.
            :param path:
            :param request:
            :return:
            """
            # allow CORS (CROSS-ORIGIN RESOURCE SHARING) for debug purposes
            request.setHeader('Access-Control-Allow-Origin', '*')
            request.setHeader('Access-Control-Allow-Methods', 'GET, PUT')
            request.setHeader('Access-Control-Allow-Headers', 'x-prototype-version,x-requested-with')
            request.setHeader('Access-Control-Max-Age', '2520')  # 42 hours
            logger.debug(f"Handling {path}")
            if path == b'ws':
                return self.ws_resource
            elif path == b'api':
                request.prepath.pop()
                request.postpath.insert(0, path)
                return self.wsgi
            elif path == b'static':
                return self.static
            elif path == b'icons':
                return self.icons
            else:
                return self.react.get_file(path)

        def render(self, request):
            return self.wsgi.render(request)

    application = service.Application('cmdserver')
    if cfg.is_access_logging is True:
        site = server.Site(FlaskAppWrapper(), logPath=path.join(cfg.config_path, 'access.log').encode())
    else:
        site = server.Site(FlaskAppWrapper())
    logger.info(f'Listening on 0.0.0.0:{cfg.port}')
    endpoint = endpoints.TCP4ServerEndpoint(reactor, cfg.port, interface='0.0.0.0')
    endpoint.listen(site)
    reactor.run()


if __name__ == '__main__':
    main()
