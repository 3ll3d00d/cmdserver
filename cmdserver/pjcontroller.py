import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from queue import Empty, Queue
from threading import Lock
from time import sleep
from typing import Optional, Tuple, Union, Any, Callable

from cmdserver.debounce import debounce
from cmdserver.jvc import CommandExecutor, CommandNack
from cmdserver.jvccommands import Command, load_all_commands, Numeric, PowerState, \
    READ_ONLY_RC
from cmdserver.mqtt import MQTT
from jvccommands import InstallationMode

logger = logging.getLogger('pjcontroller')


class PJController:

    def __init__(self, config, mqtt: Optional[MQTT]):
        self.__pj_macros = config.pj_macros
        self.__mqtt = mqtt
        self.__executor = CommandExecutor(host=config.pj_ip, password=config.pj_password) if config.pj_ip else None
        self.__commands = load_all_commands()
        self.__queue = Queue()
        self.__lock = Lock()
        self.__attributes = {
            'anamorphicMode': '',
            'installationMode': '',
            'pictureMode': ''
        }
        self.__last_updated_at = time.time()
        if self.__mqtt:
            logger.info("MQTT is enabled, refreshing PJ state in 20s")
            self.__running = threading.Event()
            self.__running.set()
            self.__worker = threading.Thread(target=self.__do_work, daemon=True).start()
            from twisted.internet import reactor
            reactor.callLater(20.0, lambda: self.__queue.put_nowait(self.__update_state))

    def __do_work(self):
        logger.info(f'Entering PJ executor thread')
        while self.__running.is_set():
            try:
                payload = self.__queue.get(timeout=5)
                if isinstance(payload, Callable):
                    payload()
                else:
                    logger.warning(f'Ignoring unknown item, should be Callable {payload}')
                self.__queue.task_done()
            except Empty:
                pass
        logger.info(f'Exiting PJ executor thread')

    def __update_state(self):
        last = self.__last_updated_at
        now = time.time()
        self.__last_updated_at = now
        if now - last < 0.5:
            logger.warning(f'Suppressing request, too soon since last update')
            return

        update_in = 1
        with self.__lock:
            logger.info('Refreshing PJ State')
            cmd = Command.Power
            try:
                self.__connect()
                self.__mqtt.online('pj')
                power = self.__executor.get(cmd)
                if power == PowerState.LampOn:
                    cmd = Command.Anamorphic
                    ana = self.__executor.get(cmd)
                    cmd = Command.PictureMode
                    pic = self.__executor.get(cmd)
                    # cmd = Command.InstallationMode
                    # install = self.__executor.get(cmd)
                    self.__attributes = {
                        'anamorphicMode': ana.name,
                        # 'installationMode': install.name,
                        'installationMode': InstallationMode.ONE.name,
                        'pictureMode': pic.name
                    }
                    update_in = 10
                else:
                    update_in = 1 if power == PowerState.Starting or power == PowerState.Cooling else 20
                self.__mqtt.state('pj', power.name)
                self.__mqtt.attributes('pj', json.dumps(self.__attributes))
                self.__update_state_in(update_in=update_in)
                self.__disconnect()
                logger.info('Refreshed PJ State')
            except CommandNack:
                # self.__update_state_in(update_in=10)
                # self.__hard_disconnect()
                self.__update_state_in(update_in=update_in)
                self.__disconnect()
                logger.exception(f"Command NACKed - GET {cmd}")
            except:
                self.__mqtt.offline('pj')
                self.__update_state_in(update_in=10)
                self.__hard_disconnect()
                logger.exception(f"Unexpected failure while executing cmd: {cmd}")

    def __update_state_in(self, update_in: float = 20, reason: str = None):
        logger.debug(f'Scheduling update in {update_in}s {"due to " if reason else ""}{reason}')
        from twisted.internet import reactor
        reactor.callLater(update_in, lambda: self.__queue.put_nowait(self.__update_state))

    @property
    def state(self):
        return self.__attributes

    @property
    def enabled(self):
        return self.__executor is not None

    def __connect(self):
        self.__executor.connect()

    @debounce(4)
    def __disconnect(self):
        self.__executor.disconnect(fail=False)

    @debounce(0.001)
    def __hard_disconnect(self):
        self.__executor.disconnect(fail=False)

    def get(self, command):
        with self.__lock:
            try:
                cmd = Command[command]
                self.__connect()
                val = self.__executor.get(cmd)
                self.__disconnect()
                if val is not None:
                    return val.name if isinstance(val, Enum) else val.replace('"', '').strip()
                return val
            except KeyError:
                logger.warning(f"Ignoring unknown command {command}")
                return None
            except CommandNack:
                logger.exception(f"Command NACKed - GET {command}")
                return -1
            except:
                logger.exception(f"Unexpected failure while executing cmd: {command}")
                return -1

    def send(self, commands):
        """ Sends the commands to the PJ """
        with self.__lock:
            sent = []
            vals = []
            self.__connect()
            for command in commands:
                if command[0:5] == 'PAUSE':
                    sleep_secs = float(command[5:])
                    logger.info(f"Sleeping for {sleep_secs:.3f}")
                    sleep(sleep_secs)
                else:
                    if command in self.__pj_macros:
                        for cmd in self.__pj_macros[command]:
                            c, e, v = self.__execute(cmd)
                        if c and e:
                            sent.append((c, e))
                        if v:
                            vals.append(v)
                    else:
                        c, e, v = self.__execute(command)
                        if c and e:
                            sent.append((c, e))
                        if v:
                            vals.append(v)
            self.__disconnect()
            if self.__mqtt:
                self.__update_state_if_necessary(sent)
            return vals

    def __update_state_if_necessary(self, sent):
        mutate_cmd = None
        for c, e in sent:
            if c != Command.Remote:
                mutate_cmd = f'{c} - {e}'
                break
            else:
                if e not in READ_ONLY_RC:
                    mutate_cmd = f'{c} - {e}'
                    break
        if mutate_cmd:
            self.__update_state_in(update_in=1, reason=f'{mutate_cmd}')
        else:
            logger.info(f'Info only, PJ state will not be updated')

    def __execute(self, cmd) -> Tuple[Optional[Command], Optional[Union[Enum, Numeric]], any]:
        tokens = cmd.split('.')
        if len(tokens) > 1:
            try:
                cmd_enum = Command[tokens[0]]
                if isinstance(cmd_enum.value, tuple):
                    cmd_arg_enum = cmd_enum.value[1]
                    if cmd_arg_enum.__name__ == tokens[1]:
                        logger.info(f"Executing {cmd}")
                        if issubclass(cmd_arg_enum, Enum):
                            tok = cmd_arg_enum[tokens[2]]
                            return cmd_enum, tok, self.__executor.set(cmd_enum, tok)
                        elif issubclass(cmd_arg_enum, Numeric):
                            tok = Numeric(int(tokens[2]))
                            return cmd_enum, tok, self.__executor.set(cmd_enum, tok)
                        else:
                            logger.warning(f"Unsupported value type for {cmd} - {cmd_arg_enum.__name__}")
            except (AttributeError, KeyError):
                logger.exception(f"Ignoring unknown command {cmd}")
            except:
                logger.exception(f"Unexpected exception while processing {cmd}")
        else:
            logger.error(f"Ignoring unknown command {cmd}")
        return None, None, None
