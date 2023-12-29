import functools
import json
import logging
import re
from typing import Tuple, List, Optional

from plumbum import local
from pymcws import MediaServer, Zone
from requests import ConnectTimeout
from twisted.internet import task, threads
from twisted.internet.defer import Deferred

from cmdserver.config import Config
from cmdserver.ws import WsServer
from cmdserver.mqtt import MQTT

DEFAULT_ACTIVE_COMMAND = 'Music'

logger = logging.getLogger('infoprovider')


class InfoProvider:
    VOLUME_PATTERN = re.compile(r'.*\(([-+][0-9]+\.[0-9]) dB\)')

    def __init__(self, config: Config, ws_server: WsServer, mqtt: Optional[MQTT]):
        self.__ws_server = ws_server
        self.__mqtt = mqtt
        self.__interval = float(config.mcws.get('interval', 0.25))
        self.__launcher = local[config.playingNowExe] if config.playingNowExe else None
        self.__default_playing_now_id = None
        for key, value in config.commands.items():
            if 'playingNowId' in value:
                is_default = value.get('defaultPlayingNowId', False)
                if is_default is True:
                    self.__default_playing_now_id = value['playingNowId']
        self.__by_playing_now_id = {value['playingNowId']: value['title']
                                    for key, value in config.commands.items() if 'playingNowId' in value}
        self.__ms: MediaServer = MediaServer('localhost', config.mcws.get('user', None), config.mcws.get('pass', None))
        # make sure all calls in pymcws have a timeout not just connection checks
        self.__ms.session.request = functools.partial(self.__ms.session.request, timeout=2.5)
        self.__mqtt_name: str = f"mc/{config.mcws.get('name', 'mediacentre')}"
        self.__ms_mac: str = config.mcws.get('mac', '')
        self.__ms.port = int(config.mcws.get('port', 52199))
        self.__ms.local_ip_list = config.mcws.get('ip', '127.0.0.1')
        self.__ms.local_ip = self.__ms.local_ip_list
        self.__token = None
        self.__current_state = {
            'config': {
                'host': self.__ms.local_ip,
                'port': self.__ms.port,
                'token': '',
                'ssl': False,
                'alive': False
            },
            'zones': {}
        }
        self.__ws_server.factory.init(self.__state_to_str)
        logger.info(f'Refreshing MC state every {self.__interval}s')
        self.__refresh_task = task.LoopingCall(self.refresh)
        self.__deferred = self.__refresh_task.start(self.__interval)
        from twisted.python import log
        self.__deferred.addErrback(log.err)
        if self.__mqtt:
            self.__mqtt.offline(self.__mqtt_name)

    def __state_to_str(self) -> str:
        return json.dumps(self.info, ensure_ascii=False)

    @property
    def info(self):
        return self.__current_state

    def __get_token(self) -> str:
        if self.__token is None:
            response = self.__ms.send_request("Authenticate")
            response.raise_for_status()
            from pymcws.utils import transform_unstructured_response
            content = transform_unstructured_response(response)
            self.__token = content['Token']
        return self.__token

    def refresh(self) -> Deferred:
        return threads.deferToThread(self.__async_refresh)

    def __async_refresh(self):
        logger.debug(f'Refreshing MC state from {self.__ms.local_ip}')
        try:
            zones, active_zone = get_zones(self.__ms)
            playback_info = get_playback_info(self.__ms, active_zone)
            zones_data = {}
            for z in zones:
                if z == active_zone:
                    zd = self.__zone_to_dict(z, playback_info)
                else:
                    zd = self.__zone_to_dict(z, None)
                zones_data[z.id] = zd
            playing = self.info.get('playingCommand', {})
            was_alive = self.info['config']['alive']
            self.__current_state = {
                'config': {
                    'host': self.__ms.local_ip,
                    'port': self.__ms.port,
                    'token': self.__get_token(),
                    'ssl': False,
                    'alive': True
                },
                'zones': zones_data,
                'playingCommand': playing
            }
            last_active_zone_id = playing.get('id', '')
            playing['active'] = self.get_active_command(zones_data.get(active_zone.id, None))
            if active_zone.id:
                playing['id'] = active_zone.id
            self.__ws_server.broadcast(self.__state_to_str())
            if not was_alive:
                self.__mqtt.online(self.__mqtt_name)
            if active_zone.id != last_active_zone_id:
                self.__mqtt.state(self.__mqtt_name, active_zone.id)
                self.__mqtt.attributes(self.__mqtt_name, json.dumps({'zone_name': active_zone.name}))
        except ConnectTimeout as e:
            logger.warning(f"Unable to connect, MC probably sleeping {e.request.method} {e.request.url}")
            self.__broadcast_down()
        except OSError as e:
            if e.errno == 113:
                logger.warning(f"Unable to connect, MC probably sleeping ({self.__ms.address()})")
            else:
                e = e.__context__
                while e is not None and not isinstance(e, OSError):
                    e = e.__context__
                if e is not None and e.errno == 113:
                    logger.warning(f"Unable to connect, MC probably sleeping ({self.__ms.address()})")
                else:
                    logger.exception(f"Unknown OSError when refreshing current state of {self.__ms.address()}")
            self.__broadcast_down()
        except ConnectionRefusedError as e:
            logger.error(f"Unable to connect, MC appears down")
            self.__broadcast_down()
        except:
            logger.exception(f"Unexpected failure to refresh current state of {self.__ms.address()}")
            self.__broadcast_down()
        finally:
            logger.debug(f'Refreshed MC state from {self.__ms.local_ip}')

    def __broadcast_down(self):
        was_alive = self.__current_state['config']['alive'] is True or self.__current_state['config']['token'] == ''
        if was_alive:
            logger.warning(f"Broadcasting MC is DOWN")
        self.__current_state = {
            'config': {
                'host': self.__ms.local_ip,
                'port': self.__ms.port,
                'token': None,
                'ssl': False,
                'alive': False
            },
            'zones': self.__current_state['zones'] if self.__current_state else {},
            'playingCommand': {'active': DEFAULT_ACTIVE_COMMAND, 'id': ''}
        }
        self.__ws_server.broadcast(self.__state_to_str())
        if self.__mqtt:
            self.__mqtt.offline(self.__mqtt_name)

    def wake(self) -> bool:
        if self.__ms_mac:
            from wakeonlan import send_magic_packet
            logger.info(f"Sending magic packet to {self.__ms_mac}")
            send_magic_packet(self.__ms_mac)
            logger.info(f"Sent magic packet to {self.__ms_mac}")
            return True
        else:
            return False

    @staticmethod
    def __zone_to_dict(zone: Zone, playback_info):
        zd = {'name': zone.name, 'id': zone.id, 'active': playback_info is not None}
        pn = None
        if playback_info:
            InfoProvider.__extract_volume(playback_info, zd)
            pn = {
                'artist': playback_info.get('Artist', ''),
                'album': playback_info.get('Album', ''),
                'status': InfoProvider.__extract_status(playback_info),
                'fileKey': playback_info.get('FileKey', ''),
                'positionMillis': float(playback_info.get('PositionMS', 0)),
                'durationMillis': float(playback_info.get('DurationMS', 0)),
                'positionDisplay': playback_info.get('PlayingNowPositionDisplay', ''),
                'imageURL': playback_info.get('ImageURL', ''),
                'name': playback_info.get('Name', ''),
                'externalSource': playback_info.get('Name', '') == 'Ipc',
                'hdr': playback_info.get('HDR Format', ''),
                'ar': playback_info.get('Aspect Ratio', ''),
                'hdr_override': playback_info.get('hdr_override', ''),
            }
            zd['volumeRatio'] = float(playback_info.get('Volume', 0))
        zd['playingNow'] = pn
        return zd

    @staticmethod
    def __extract_volume(playback_info: dict, zd: dict):
        volume_display = playback_info.get('VolumeDisplay', None)
        if not volume_display or volume_display == 'Muted':
            zd['muted'] = True
            zd['volumedb'] = -100.0
        else:
            zd['muted'] = False
            if volume_display == '100%':
                zd['volumedb'] = 0.0
            else:
                m = InfoProvider.VOLUME_PATTERN.match(volume_display)
                if m:
                    zd['volumedb'] = float(m[1])
                else:
                    zd['volumedb'] = -100.0

    def get_active_command(self, zone: Optional[dict]):
        if zone:
            pn = zone.get('playingNow', None)
            if pn and pn['externalSource'] is True:
                if self.__launcher:
                    playing_now = self.__launcher.run(retcode=None)
                    playing_now_id = playing_now[0]
                    logger.debug("playingNow:" + str(playing_now_id))
                    if playing_now_id in self.__by_playing_now_id:
                        return self.__by_playing_now_id[playing_now_id]
                elif self.__default_playing_now_id:
                    return self.__by_playing_now_id[self.__default_playing_now_id]
        return zone['name'] if zone else DEFAULT_ACTIVE_COMMAND

    @staticmethod
    def __extract_status(playback_info):
        state = int(playback_info.get('State', -1))
        if state == 0:
            return 'Stopped'
        elif state == 1:
            return 'Paused'
        elif state == 2:
            return 'Playing'
        else:
            return 'Unknown'


def get_zones(media_server: MediaServer, see_hidden: bool = False) -> Tuple[List[Zone], Zone]:
    see_hidden = "1" if see_hidden else "0"
    payload = {"Hidden": see_hidden}
    response = media_server.send_request("Playback/Zones", payload)
    response.raise_for_status()
    from pymcws.utils import transform_unstructured_response
    content = transform_unstructured_response(response)
    num_zones = int(content["NumberZones"])
    active_zone_id = content['CurrentZoneID']
    active_zone = None
    zones = []
    for i in range(num_zones):
        zone = Zone()
        zone.index = i
        zone.id = content["ZoneID" + str(i)]
        zone.name = content["ZoneName" + str(i)]
        zone.guid = content["ZoneGUID" + str(i)]
        zone.is_dlna = True if (content["ZoneDLNA" + str(i)] == "1") else False
        zones.append(zone)
        if active_zone_id == zone.id:
            active_zone = zone
    if not active_zone:
        active_zone = zones[0]
    return zones, active_zone


def get_playback_info(media_server: MediaServer, active_zone: Zone) -> dict:
    payload = {
        'Fields': 'Aspect Ratio;HDR Format;Playback Info',
        'Zone': active_zone.best_identifier(),
        'ZoneType': active_zone.best_identifier_type()
    }
    response = media_server.send_request("Playback/Info", payload)
    response.raise_for_status()
    from pymcws.utils import transform_unstructured_response
    structured_resp = transform_unstructured_response(response)
    pi = structured_resp.get('Playback Info', '')
    hdr_override = ''
    if pi:
        try:
            pos = pi.index('JRVRProfiles')
            profiles = pi[pos + len('JRVRProfiles') + 1:]
            pos = profiles.index(':')
            profiles_len = profiles[1:pos]
            tokens = [x for x in re.split(r'[()]', profiles[pos + 1: pos + int(profiles_len) + 1]) if x]
            pos = tokens.index('1:3')
            selected = tokens[pos + 1].split(':', 2)
            hdr_override = selected[1]
        except:
            # can't parse so ignoring
            pass
    structured_resp['hdr_override'] = hdr_override
    return structured_resp
