import logging
import re
import socket
import threading
import time
from typing import Optional

from cmdserver.zeroconf import Zeroconf, ServiceBrowser
from cmdserver.config import Config

logger = logging.getLogger('tivocontroller')


# Mapping of commands to remote codes
CODES = {
    # teleport
    'Home': 'TIVO',
    'My Shows': 'NOWSHOWING',
    'LiveTV': 'LIVETV',
    'Info': 'INFO',
    'Guide': 'GUIDE',
    'Back': 'BACK',
    'Thumbs Up': 'THUMBSUP',
    'Thumbs Down': 'THUMBSDOWN',
    # navigation
    'Up': 'UP',
    'Down': 'DOWN',
    'Left': 'LEFT',
    'Right': 'RIGHT',
    'Return': 'SELECT',
    'Ch+': 'CHANNELUP',
    'Ch-': 'CHANNELDOWN',
    # Play, Pause, FF, Rew
    'Stop': 'STOP',
    'Play': 'PLAY',
    'Rewind': 'REVERSE',
    'Pause': 'PAUSE',
    'FF': 'FORWARD',
    # Skip Back, Slow Motion, Skip Forward
    'Replay': 'REPLAY',
    'Slow': 'SLOW',
    'Advance': 'ADVANCE',
    # Record
    'Record': 'RECORD',
    # colour keys
    'Red': 'ACTION_A',
    'Green': 'ACTION_B',
    'Yellow': 'ACTION_C',
    'Blue': 'ACTION_D',
    # channel selection
    'Clear': 'CLEAR',
    'Enter': 'ENTER',
    # subtitles
    'Subtitles Off': 'CC_OFF',
    'Subtitles On': 'CC_ON'
}

# Named symbols for direct text input -- these work with IRCODE and
# KEYBOARD commands
SYMBOLS = {'-': 'MINUS', '=': 'EQUALS', '[': 'LBRACKET',
           ']': 'RBRACKET', '\\': 'BACKSLASH', ';': 'SEMICOLON',
           "'": 'QUOTE', ',': 'COMMA', '.': 'PERIOD', '/': 'SLASH',
           '`': 'BACKQUOTE', ' ': 'SPACE', '1': 'NUM1', '2': 'NUM2',
           '3': 'NUM3', '4': 'NUM4', '5': 'NUM5', '6': 'NUM6',
           '7': 'NUM7', '8': 'NUM8', '9': 'NUM9', '0': 'NUM0'}

# When in shift mode (with KEYBOARD command only), the same names
# map to a different set of symbols
SHIFT_SYMS = {'_': 'MINUS', '+': 'EQUALS', '{': 'LBRACKET',
              '}': 'RBRACKET', '|': 'BACKSLASH', ':': 'SEMICOLON',
              '"': 'QUOTE', '<': 'COMMA', '>': 'PERIOD', '?': 'SLASH',
              '~': 'BACKQUOTE', '!': 'NUM1', '@': 'NUM2', '#': 'NUM3',
              '$': 'NUM4', '%': 'NUM5', '^': 'NUM6', '&': 'NUM7',
              '*': 'NUM8', '(': 'NUM9', ')': 'NUM0'}


class Tivo:

    def __init__(self, tivo: dict):
        self.__sock = None
        self.__tivo = tivo
        self.__messages = [''] * 5
        self.__message_idx = 0
        self.current_channel = ''
        if ':' in tivo['address']:
            address, port = tivo['address'].split(':')
            try:
                port = int(port)
                self.__tivo['address'] = address
                self.__tivo['port'] = port
            except:
                pass
        self.__connect()

    @property
    def name(self):
        return self.__tivo['name']

    @property
    def port(self):
        return self.__tivo['port']

    @property
    def address(self):
        return self.__tivo['address']

    @property
    def version(self):
        return self.__tivo['version']

    def get_tivo_properties(self):
        return {**self.__tivo}

    @property
    def connected(self):
        return self.__sock is not None

    def __connect(self):
        """ Connect to the TiVo within five seconds or report error. """
        self.__messages = [''] * 5
        self.__message_idx = 0
        try:
            self.__sock = socket.socket()
            self.__sock.settimeout(5)
            self.__sock.connect((self.address, self.port))
            self.__sock.settimeout(None)
            self.__status_thread = threading.Thread(name='TivoStatusReader', target=self.__read_from_socket, daemon=True)
            self.__status_thread.start()
        except Exception as e:
            self.__record_message('Unable to connect - ' + str(e))
            self.disconnect()

    def disconnect(self):
        if self.__sock:
            self.__record_message('Stopping on disconnect')
            self.__sock.close()
            self.__record_message('Disconnected')
            self.__sock = None
        else:
            logger.info(f"Ignoring disconnect {self.name} has no socket")

    def __send(self, message):
        """ The core output function. Re-connect if necessary, send message, sleep, and check for errors. """
        if not self.__sock:
            self.__connect()
        try:
            self.__sock.sendall(message.encode())
            time.sleep(0.1)
        except Exception as e:
            logger.error(e)
            self.__record_message('Failed to send ' + str(message) + ' - ' + str(e))
            self.disconnect()
            raise e

    def send_ir(self, sent, *codes):
        """ Expand a command sequence for send(). """
        for each in codes:
            if type(each) == list:
                self.send_ir(sent, *each)
            else:
                if each in CODES:
                    actual = CODES[each]
                    if type(actual) == list:
                        self.send_ir(sent, *actual)
                    else:
                        to_send = 'IRCODE %s\r' % actual
                        sent.append(to_send)
                        self.__send(to_send)
                else:
                    raise ValueError('Unknown IR Code ' + each)
        return {'channel': self.current_channel, 'sent': sent}

    def set_channel(self, channel):
        """ Sends a single SETCH. """
        toSend = 'SETCH %s\r' % channel
        self.__send(toSend)
        return {'channel': self.current_channel, 'sent': [toSend]}

    def send_text(self, text):
        """ Expand a KEYBOARD command sequence for send(). """
        sent = []
        for ch in text:
            if 'A' <= ch <= 'Z':
                self.__send_keyboard(sent, 'LSHIFT', ch)
            elif 'a' <= ch <= 'z':
                self.__send_keyboard(sent, ch.upper())
            elif ch in SYMBOLS:
                self.__send_keyboard(sent, SYMBOLS[ch])
            elif ch in SHIFT_SYMS:
                self.__send_keyboard(sent, 'LSHIFT', SHIFT_SYMS[ch])
        return {'channel': self.current_channel, 'sent': sent}

    def __send_keyboard(self, sent, *codes):
        for each in codes:
            to_send = 'KEYBOARD %s\r' % each
            sent.append(to_send)
            self.__send(to_send)

    def __record_message(self, msg):
        idx = self.__message_idx % 5
        self.__message_idx += 1
        self.__messages[idx] = msg

    def __read_from_socket(self):
        """ Read incoming messages from the socket in a separate thread.
        """
        logger.info(f"[{self.name}] Initialising status reader")
        while self.__sock is not None:
            logger.info(f'[{self.name}] Reading from socket')
            try:
                status = self.__sock.recv(80).decode()
            except Exception as e:
                status = str(e)
                logger.warning(f"Failed to read - {status}")
            status = status.strip().title()
            if not status:
                self.__record_message('No status read from socket')
                self.disconnect()
            else:
                self.current_channel = status
        logger.info(f"[{self.name}] Exiting status reader")

    @property
    def messages(self):
        return self.__messages


class TivoController(object):

    def __init__(self, cfg: Config):
        if cfg.tivo:
            logger.info(f"Using static tivo config: {cfg.tivo}")
            self.__tivos = [Tivo(cfg.tivo)]
        elif cfg.find_tivo:
            logger.info(f"Discovering Tivos")
            self.__tivos = [Tivo(t) for t in self.__find_tivos()]
            self.__ping()
        else:
            logger.info(f"Tivo support disabled")
            self.__tivos = []

    def __ping(self, delay=15):
        time.sleep(delay)
        worker = threading.Thread(name='TivoPinger', target=self.__ping0, daemon=True)
        worker.start()

    def __ping0(self):
        try:
            tivos = self.__find_tivos()
            logger.debug(f"Found {len(tivos)} tivos")
            for new_tivo in tivos:
                existing_tivo = next((t for t in self.__tivos if t.name == new_tivo['name']), None)
                if existing_tivo is None:
                    logger.info(f"Connecting new Tivo {new_tivo['name']} @ {new_tivo['address']}:{new_tivo['port']}")
                    self.__tivos.append(Tivo(new_tivo))
            for old_tivo in self.__tivos:
                dead_tivo = next((t for t in tivos if t['name'] == old_tivo.name), None)
                if dead_tivo is None:
                    logger.info(f"Disconnecting old Tivo {old_tivo.name} @ {old_tivo.address}:{old_tivo.port}")
                    old_tivo.disconnect()
        except:
            logger.exception('Unexpected failure during ping')
        finally:
            self.__ping()

    def has_tivo(self, tivo_name: str) -> bool:
        return True if next((t for t in self.__tivos if t.name == tivo_name), None) else False

    def get_tivo(self, tivo_name: str) -> Optional[Tivo]:
        return next((t for t in self.__tivos if t.name == tivo_name), None)

    def send(self, tivo_name, cmd_type, command):
        tivo = self.get_tivo(tivo_name)
        if tivo is not None:
            if cmd_type == 'keyboard':
                return tivo.send_text(command)
            elif cmd_type == 'ir':
                return tivo.send_ir([], command)
            elif cmd_type == 'setch':
                return tivo.set_channel(command)
            else:
                raise ValueError('Unknown command type ' + cmd_type)
        else:
            raise ValueError('Unknown tivo ' + tivo_name)

    @property
    def tivos(self):
        return [
            {
                **t.get_tivo_properties(),
                **{'connected': t.connected, 'messages': t.messages, 'channel': t.current_channel}
            }
            for t in self.__tivos
        ]

    def __find_tivos(self):
        class ZCListener:
            def __init__(self, names):
                self.names = names

            def remove_service(self, server, type, name):
                self.names.remove(name)

            def add_service(self, server, type, name):
                self.names.append(name)

        REMOTE = '_tivo-remote._tcp.local.'

        tivos = []
        tivos_names = []

        # Get the names of TiVos offering network remote control
        serv = Zeroconf()
        try:
            browser = ServiceBrowser(serv, REMOTE, ZCListener(tivos_names))
            # Give them a second to respond
            time.sleep(1)

            # For proxied TiVos, remove the original
            # for t in tivos_names[:]:
            #     if t.startswith('Proxy('):
            #         try:
            #             t = t.replace('.' + REMOTE, '')[6:-1] + '.' + REMOTE
            #             tivos_names.remove(t)
            #         except:
            #             pass

            # Now get the addresses -- this is the slow part
            swversion = re.compile('(\d*.\d*)').findall
            for t in tivos_names:
                s = serv.get_service_info(REMOTE, t)
                if s:
                    name = t.replace('.' + REMOTE, '')
                    address = socket.inet_ntoa(s.address)
                    try:
                        versionProperty = s.properties.get(str.encode('swversion'))
                        if (versionProperty):
                            version = float(swversion(versionProperty.decode())[0])
                        else:
                            version = 0.0
                    except Exception as e:
                        print(e)
                        version = 0.0
                    tivos.append({
                        'name': name,
                        'port': s.port,
                        'version': version,
                        'address': address
                    })

            # For proxies with numeric names, remove the original
            # for name, tivo in tivos.items():
            #     if name.startswith('Proxy('):
            #         address = name.replace('.' + REMOTE, '')[6:-1]
            #         if address in tivos_rev:
            #             tivos.pop(tivos_rev[address])
            return tivos
        except Exception as e:
            print(e)
            return tivos
        finally:
            serv.close()
