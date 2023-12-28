import logging
import re
import socket
import threading
import time
from typing import Optional

from cmdserver.zeroconf import Zeroconf, ServiceBrowser
from cmdserver.config import Config
from cmdserver.mqtt import MQTT

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

# generated from https://www.virginmedia.com/content/dam/virginmedia/dotcom/documents/Redwood/ChannelGuide_June2019.pdf
# linked from https://www.virginmedia.com/virgin-tv-edit/tips-and-tricks/virgin-tv-channel-guide
CHANNELS = {
    '100': 'Virgin TV Showcase',
    '101': 'BBC One HD',
    '102': 'BBC Two HD',
    '103': 'ITV1 HD & STV HD',
    '104': 'Channel 4/HD & S4C HD',
    '105': 'Channel 5 HD',
    '106': 'E4 HD',
    '107': 'BBC Three HD & BBC Four HD',
    '108': 'BBC Four HD/Channel 4 HD Wales',
    '109': 'Sky Showcase HD',
    '110': 'Sky Witness HD',
    '111': 'Sky Max HD',
    '112': 'Sky Comedy HD',
    '113': 'BBC Three HD Scotland & Wales',
    '114': 'alibi HD',
    '115': 'ITV2 HD',
    '116': 'Drama HD',
    '117': 'ITV3 HD',
    '118': 'ITV4 HD',
    '119': 'ITVBe HD',
    '120': '5 USA',
    '121': 'Sky Crime HD',
    '122': 'Sky Sci-Fi HD',
    '123': 'Sky Arts HD',
    '124': 'GOLD HD',
    '125': 'W HD',
    '126': '5STAR',
    '127': 'Dave HD',
    '128': 'Really',
    '129': 'Yesterday HD',
    '130': '5ACTION HD',
    '131': 'Sky HISTORYHD',
    '132': 'Comedy Central HD',
    '133': 'Crime + Investigation HD',
    '134': 'MTV HD',
    '135': 'Sky Mix',
    '136': 'Together',
    '137': 'Quest HD',
    '138': '5Select',
    '139': 'Challenge',
    '140': 'Sky Arts',
    '143': '4Seven HD',
    '144': 'E4 Extra',
    '147': 'More4 HD',
    '148': 'CBS Reality',
    '149': 'Legend',
    '150': 'That’s TV',
    '154': 'Comedy Central Extra',
    '156': 'Sky Replay',
    '159': 'Regional Channels',
    '160': 'E! HD',
    '161': 'BBC Alba',
    '162': '5USA',
    '164': 'S4C HD',
    '165': 'TLC HD',
    '166': 'Investigation Discovery',
    '168': 'Quest Red',
    '169': 'DMAX',
    '170': 'GREAT TV',
    '171': 'Horror Xtra',
    '172': 'RealityXtra',
    '174': 'BLAZE',
    '175': 'Virgin TV Ultra HD',
    '176': 'Eden HD',
    '177': 'Discovery HD',
    '178': 'Animal Planet HD',
    '179': 'Discovery Science',
    '180': 'Discovery Turbo',
    '181': 'Discovery History',
    '182': 'National Geographic WILD HD',
    '183': 'National Geographic HD',
    '186': 'Sky HISTORY2HD',
    '187': 'PBS America',
    '188': 'Sky Documentaries HD',
    '189': 'Sky Nature HD',
    '190': 'Food Network',
    '191': 'HGTV',
    '192': 'God TV',
    '360': 'Welcome',
    '204': 'Netflix',
    '205': 'Prime Video',
    '220': 'Inside Crime',
    '221': 'Real Wild',
    '222': 'Mystery TV',
    '223': 'Haunt TV',
    '224': 'History Hit',
    '230': 'Homes Under The Hammer',
    '231': 'Great British Menu',
    '232': 'Tastemade',
    '242': 'NextUp Live Comedy',
    '243': 'The Chat Show Channel',
    '244': 'Baywatch',
    '250': 'Deal Or No Deal',
    '251': 'Fear Factor',
    '252': 'Wipeout Xtra',
    '991': 'BBC Red Button HD',
    '998': 'Virgin TV Highlights',
    '999': 'Virgin TV Ultra HD',
    '280': 'MTV Music',
    '281': 'MTV Live HD',
    '282': 'MTV Hits',
    '283': 'MTV 90s',
    '284': 'MTV 80s',
    '285': 'The Box',
    '286': '4Music',
    '288': 'Kiss',
    '289': 'Magic',
    '290': 'Kerrang!',
    '291': 'Vevo',
    '292': 'Clubland TV',
    '293': 'Now 70s',
    '294': 'Now 80s',
    '295': 'Now Rock',
    '296': 'That’s 60s',
    '303': 'ITV1 +1 & STV +1',
    '304': 'Channel 4 +1',
    '305': 'Channel 5 +1',
    '306': 'E4 +1',
    '310': 'Sky Witness +1',
    '314': 'alibi +1',
    '315': 'ITV2 +1',
    '316': 'Drama HD +1',
    '317': 'ITV3 +1',
    '318': 'ITV4 +1',
    '319': 'ITVBe +1',
    '320': '5 USA +1',
    '321': 'Sky Crime +1',
    '324': 'GOLD +1',
    '325': 'W +1',
    '326': '5STAR +1',
    '327': 'Dave ja vu',
    '329': 'Yesterday HD +1',
    '331': 'Sky HISTORY +1',
    '332': 'Comedy Central +1',
    '333': 'Crime + Investigation +1',
    '337': 'Quest +1',
    '347': 'More4 +1',
    '348': 'CBS Reality +1',
    '365': 'TLC +1',
    '366': 'Investigation Discovery +1',
    '369': 'DMAX +1',
    '371': 'HorrorXtra +1',
    '376': 'Eden +1',
    '377': 'Discovery +1',
    '378': 'Animal Planet +1',
    '379': 'Discovery Science +1',
    '381': 'Discovery History +1',
    '383': 'National Geographic +1',
    '391': 'HGTV +1',
    '400': 'Virgin Movies & Store',
    '401': 'Sky Cinema Premiere HD',
    '402': 'Sky Cinema Select HD',
    '403': 'Sky Cinema Hits HD',
    '404': 'Sky Cinema Greats HD',
    '406': 'Sky Cinema Family HD',
    '407': 'Sky Cinema Action HD',
    '408': 'Sky Cinema Comedy HD',
    '409': 'Sky Cinema Thriller HD',
    '410': 'Sky Cinema Drama HD',
    '411': 'Sky Cinema Sci-Fi & Horror HD',
    '412': 'Sky Cinema Animation HD',
    '419': 'Movies 24',
    '420': 'Movies 24 +1',
    '424': 'Great! Romance',
    '425': 'Great! Movies',
    '426': 'Great! Action',
    '428': 'Film4 HD',
    '430': 'Film4 +1',
    '445': 'Talking Pictures TV',
    '501': 'Sky Sports Main Event/HD',
    '502': 'Sky Sports Premier League/HD',
    '503': 'Sky Sports Football/HD',
    '504': 'Sky Sports Cricket/HD',
    '505': 'Sky Sports Golf/HD',
    '506': 'Sky Sports F1®/HD',
    '507': 'Sky Sports Action/HD',
    '508': 'Sky Sports Arena/HD',
    '509': 'Sky Sports News HD',
    '510': 'Sky Sports Mix HD',
    '519': 'Sky Sports Racing HD',
    '521': 'Eurosport 1 HD',
    '522': 'Eurosport 2 HD',
    '526': 'MUTV',
    '527': 'TNT Sports 1 HD',
    '528': 'TNT Sports 2 HD',
    '529': 'TNT Sports 3 HD',
    '530': 'TNT Sports 4 HD',
    '531': 'TNT Sports Ultimate',
    '532': 'Sky Sports Main Event UHD',
    '533': 'Sky Sports F1® UHD',
    '534': 'Sky Sports UHD',
    '535': 'Sky Sports UHD 2',
    '536': 'Racing TV HD',
    '544': 'LFC TV HD',
    '551': 'Viaplay Sports 1 HD',
    '552': 'Viaplay Sports 2 HD',
    '553': 'Viaplay Xtra',
    '601': 'BBC News HD',
    '602': 'Sky News/HD',
    '604': 'GB News',
    '605': 'BBC Parliament',
    '606': 'TalkTV',
    '609': 'Bloomberg HD',
    '613': 'CNBC',
    '614': 'NBC News NOW HD',
    '620': 'Euronews',
    '621': 'NDTV 24x7',
    '622': 'Al Jazeera English',
    '624': 'France 24 English HD',
    '625': 'NHKworld HD',
    '700': 'Kids TV On Demand',
    '701': 'CBBC HD',
    '702': 'CBeebies HD',
    '703': 'Baby TV',
    '704': 'Cartoon Network HD',
    '702': 'CBeebies HD',
    '703': 'Baby TV',
    '704': 'Cartoon Network HD',
    '705': 'Cartoon Network +1',
    '706': 'Cartoonito',
    '707': 'Sky Kids HD',
    '712': 'Nickelodeon HD',
    '713': 'Nick +1',
    '715': 'Nick Jr.',
    '716': 'Nick Jr. Too',
    '717': 'Nicktoons',
    '730': 'Boomerang',
    '731': 'Boomerang +1',
    '736': 'Pop',
    '737': 'Tiny Pop',
    '740': 'QVC HD',
    '741': 'QVC Beauty',
    '742': 'QVC Style HD',
    '743': 'QVC Extra',
    '748': 'Create and Craft',
    '755': 'Gems TV',
    '757': 'TJC HD',
    '801': 'Utsav Gold HD',
    '802': 'Utsav Bharat',
    '803': 'Utsav Plus HD',
    '805': 'SONY TV HD',
    '806': 'SONY MAX HD',
    '807': 'SONY SAB',
    '808': 'SONY MAX 2',
    '809': 'Zee TV HD',
    '810': 'Zee Cinema HD',
    '815': 'B4U Movies',
    '816': 'B4U Music',
    '825': 'Colors Gujarati',
    '826': 'Colors TV HD',
    '827': 'Colors Rishtey',
    '828': 'Colors Cineplex',
    '829': 'NDTV Good Times',
    '831': 'Al Jazeera Arabic',
    '838': 'Islam Channel',
    '839': 'Islam Channel Urdu',
    '159': 'Regional Channels',
    '861': 'BBC One London HD',
    '862': 'BBC One Scotland HD',
    '863': 'BBC One NI HD',
    '864': 'BBC One Wales HD',
    '865': 'BBC Two England HD',
    '870': 'ITV1'
}


class Tivo:

    def __init__(self, tivo: dict, mqtt: MQTT):
        self.__sock = None
        self.__tivo = tivo
        self.__mqtt = mqtt
        self.__messages = [''] * 5
        self.__message_idx = 0
        self.current_channel = ''
        self.current_channel_num = -1
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
            if self.__mqtt:
                self.__mqtt.online(f'tivo/{self.name}')
            self.__status_thread = threading.Thread(name='TivoStatusReader', target=self.__read_from_socket,
                                                    daemon=True)
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
        if self.__mqtt:
            self.__mqtt.offline(f'tivo/{self.name}')

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
                last_ch = self.current_channel
                self.current_channel = status
                if status.startswith('Ch_Status'):
                    try:
                        self.current_channel_num = int(status.split()[1])
                    except:
                        self.current_channel_num = -1
                else:
                    self.current_channel_num = -1
                if last_ch != self.current_channel and self.__mqtt:
                    ch_name = CHANNELS.get(str(self.current_channel_num), 'Unknown')
                    self.__mqtt.state(f'tivo/{self.name}', ch_name)
        logger.info(f"[{self.name}] Exiting status reader")

    @property
    def messages(self):
        return self.__messages


class TivoController(object):

    def __init__(self, cfg: Config, mqtt: Optional[MQTT]):
        if cfg.tivo:
            logger.info(f"Using static tivo config: {cfg.tivo}")
            self.__tivos = [Tivo(cfg.tivo, mqtt)]
        elif cfg.find_tivo:
            logger.info(f"Discovering Tivos")
            self.__tivos = [Tivo(t, mqtt) for t in self.__find_tivos()]
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
            elif cmd_type == 'setchno':
                ch_num = next((k for k, v in CHANNELS.items() if v == command), '')
                if ch_num:
                    return tivo.set_channel(ch_num)
                else:
                    return ValueError(f'Unknown channel {command}')
            else:
                raise ValueError('Unknown command type ' + cmd_type)
        else:
            raise ValueError('Unknown tivo ' + tivo_name)

    @property
    def tivos(self):
        return [
            {
                **t.get_tivo_properties(),
                **{'connected': t.connected, 'messages': t.messages, 'channel': t.current_channel,
                   'channelNumber': t.current_channel_num}
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
            swversion = re.compile(r'(\d*.\d*)').findall
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
