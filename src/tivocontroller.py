import logging
import re
import socket
import threading
import time

import zeroconf

logger = logging.getLogger('cmdserver.tivocontroller')

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


class Tivo(object):
    def __init__(self, tivo):
        self._sock = None
        self._tivo = tivo
        self._messages = [''] * 5
        self._messageIdx = 0
        self.currentChannel = ''
        if ':' in tivo['address']:
            address, port = tivo['address'].split(':')
            try:
                port = int(port)
                self._tivo['address'] = address
                self._tivo['port'] = port
            except:
                pass
        self._connect()

    def _connect(self):
        """ Connect to the TiVo within five seconds or report error. """
        self._messages = [''] * 5
        self._messageIdx = 0
        try:
            self._sock = socket.socket()
            self._sock.settimeout(5)
            self._sock.connect((self._tivo['address'], self._tivo['port']))
            self._sock.settimeout(None)
            self._statusThread = threading.Thread(name='TivoStatusReader', target=self._readFromSocket, daemon=True)
            self._statusThread.start()
        except Exception as e:
            self._recordMessage('Unable to connect - ' + str(e))
            self.disconnect()

    def disconnect(self):
        if self._sock:
            self._disconnect0()

    def _send(self, message):
        """ The core output function. Re-connect if necessary, send message, sleep, and check for errors. """
        if not self._sock:
            self._connect()
        try:
            self._sock.sendall(message.encode())
            time.sleep(0.1)
        except Exception as e:
            logger.error(e)
            self._recordMessage('Failed to send ' + str(message) + ' - ' + str(e))
            self.disconnect()
            raise e

    def sendIR(self, sent, *codes):
        """ Expand a command sequence for send(). """
        for each in codes:
            if type(each) == list:
                self.sendIR(sent, *each)
            else:
                if each in CODES:
                    actual = CODES[each]
                    if type(actual) == list:
                        self.sendIR(sent, *actual)
                    else:
                        toSend = 'IRCODE %s\r' % actual
                        sent.append(toSend)
                        self._send(toSend)
                else:
                    raise ValueError('Unknown IR Code ' + each)
        return {'channel': self.currentChannel, 'sent': sent}

    def setChannel(self, channel):
        """ Sends a single SETCH. """
        toSend = 'SETCH %s\r' % channel
        self._send(toSend)
        return {'channel': self.currentChannel, 'sent': [toSend]}

    def sendText(self, text):
        """ Expand a KEYBOARD command sequence for send(). """
        sent = []
        for ch in text:
            if 'A' <= ch <= 'Z':
                self._sendKeyboard(sent, 'LSHIFT', ch)
            elif 'a' <= ch <= 'z':
                self._sendKeyboard(sent, ch.upper())
            elif ch in SYMBOLS:
                self._sendKeyboard(sent, SYMBOLS[ch])
            elif ch in SHIFT_SYMS:
                self._sendKeyboard(sent, 'LSHIFT', SHIFT_SYMS[ch])
        return {'channel': self.currentChannel, 'sent': sent}

    def _sendKeyboard(self, sent, *codes):
        for each in codes:
            toSend = 'KEYBOARD %s\r' % each
            sent.append(toSend)
            self._send(toSend)

    def _recordMessage(self, msg):
        idx = self._messageIdx % 5
        self._messageIdx += 1
        self._messages[idx] = msg

    def _readFromSocket(self):
        """ Read incoming messages from the socket in a separate thread.
        """
        while self._sock is not None:
            try:
                status = self._sock.recv(80).decode()
            except Exception as e:
                status = str(e)
            status = status.strip().title()
            if not status:
                self.disconnect()
            else:
                self.currentChannel = status

    def _disconnect0(self):
        if not self._sock:
            self._recordMessage('Stopping on disconnect')
            self._sock.close()
            self._recordMessage('Disconnected')

    def getMessages(self):
        # TODO put the messages in the right order
        return self._messages


class TivoController(object):

    def __init__(self):
        self._tivos = [Tivo(t) for t in self._findTivos()]
        self._worker = threading.Thread(name='TivoPinger', target=self._refreshTivos, daemon=True)
        self._worker.start()

    def _refreshTivos(self):
        tivos = self._findTivos()
        logger.debug('Found ' + str(len(tivos)) + ' tivos')
        for newTivo in tivos:
            existingTivo = next((t for t in self._tivos if t._tivo['name'] == newTivo['name']), None)
            if existingTivo is None:
                self._tivos.append(Tivo(newTivo))
        for oldTivo in self._tivos:
            deadTivo = next((t for t in tivos if t['name'] == oldTivo._tivo['name']), None)
            if deadTivo is None:
                oldTivo.disconnect()
        time.sleep(15)

    def hasTivo(self, tivoName):
        return True if next((t for t in self._tivos if t._tivo['name'] == tivoName), None) else False

    def send(self, tivoName, type, command):
        tivo = next((t for t in self._tivos if t._tivo['name'] == tivoName), None)
        if tivo is not None:
            if type == 'keyboard':
                return tivo.sendText(command)
            elif type == 'ir':
                return tivo.sendIR([], command)
            elif type == 'setch':
                return tivo.setChannel(command)
            else:
                raise ValueError('Unknown command type ' + type)
        else:
            raise ValueError('Unknown tivo ' + tivoName)

    def getTivos(self):
        return [{**t._tivo.copy(), **{'connected': t._sock is not None, 'messages': t.getMessages(), 'channel': t.currentChannel}} for t in self._tivos]

    def _findTivos(self):
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
        serv = zeroconf.Zeroconf()
        try:
            browser = zeroconf.ServiceBrowser(serv, REMOTE, ZCListener(tivos_names))
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
