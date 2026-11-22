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

from cmdserver.jvc import CommandExecutor, CommandNack
from cmdserver.jvccommands import Command, load_all_commands, Numeric, PowerState, \
    READ_ONLY_RC, Model, InstallationMode, RemoteCode
from cmdserver.mqtt import MQTT

logger = logging.getLogger('pjcontroller')

# close the PJ connection once it has been unused for this long
IDLE_DISCONNECT_SECS = 4
# a command the PJ refuses (e.g. while it is still applying a picture mode change) is retried this many times in all
COMMAND_ATTEMPTS = 3
RETRY_DELAY_SECS = 1.5
# remote codes that must only ever be sent once: a retry after a lost ack would act twice (toggles, menu navigation)
NO_RETRY_RC = frozenset(READ_ONLY_RC) | frozenset(rc for rc in RemoteCode if rc.name.endswith('Toggle')) | {
    RemoteCode.Back, RemoteCode.Input, RemoteCode.LensMenu, RemoteCode.Info_PictureAdjust, RemoteCode.Hide}


class UnknownCommand(Exception):
    pass


@dataclass
class SendResult:
    values: list = field(default_factory=list)
    unknown: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    errors: list = field(default_factory=list)


class PJController:

    def __init__(self, config, mqtt: Optional[MQTT]):
        self.__pj_macros = config.pj_macros
        self.__mqtt = mqtt
        self.__executor = CommandExecutor(host=config.pj_ip, password=config.pj_password) if config.pj_ip else None
        self.__commands = load_all_commands()
        self.__queue = Queue()
        self.__lock = Lock()
        self.__activity = 0
        self.__idle_timer: Optional[threading.Timer] = None
        self.__idle_timer_lock = Lock()
        self.__attributes = {
            'anamorphicMode': '',
            'installationMode': '',
            'pictureMode': ''
        }
        self.__last_updated_at = time.time()
        # the one pending state refresh, only ever read or changed on the reactor thread
        self.__next_update = None
        if self.__mqtt:
            logger.info("MQTT is enabled, refreshing PJ state in 20s")
            self.__running = threading.Event()
            self.__running.set()
            self.__worker = threading.Thread(target=self.__do_work, daemon=True)
            self.__worker.start()
            self.__update_state_in(update_in=20, reason='startup')

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
            # keep the refresh cycle going, nothing else will schedule the next one
            self.__update_state_in(update_in=1, reason='suppressed refresh')
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
                    cmd = Command.Model
                    md = self.__executor.get(cmd)
                    if md != Model.DLA_NZ700:
                        cmd = Command.InstallationMode
                        install = self.__executor.get(cmd)
                    else:
                        install = InstallationMode.ONE.name
                    self.__attributes = {
                        'anamorphicMode': ana.name,
                        'installationMode': install,
                        'pictureMode': pic.name,
                        'model': md.name,
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
        """
        Asks for a state refresh in update_in seconds. Safe to call from any thread: the reactor is not thread safe so
        the scheduling itself is handed to the reactor thread.
        """
        from twisted.internet import reactor
        reactor.callFromThread(self.__schedule_update, update_in, reason)

    def __schedule_update(self, update_in: float, reason: str = None):
        """
        Runs on the reactor thread. Only one refresh is ever pending: a request for a sooner one replaces it, a request
        for a later one is dropped, so each refresh schedules exactly one successor and the cycles never multiply.
        """
        from twisted.internet import reactor
        pending = self.__next_update
        if pending is not None and pending.active():
            if pending.getTime() <= reactor.seconds() + update_in:
                logger.debug(f'Update already due sooner than {update_in}s, ignoring request [{reason}]')
                return
            pending.cancel()
        logger.debug(f'Scheduling update in {update_in}s {"due to " if reason else ""}{reason}')
        self.__next_update = reactor.callLater(update_in, self.__enqueue_update)

    def __enqueue_update(self):
        self.__next_update = None
        self.__queue.put_nowait(self.__update_state)

    @property
    def state(self):
        return self.__attributes

    @property
    def enabled(self):
        return self.__executor is not None

    def __connect(self):
        self.__executor.connect()

    def __disconnect(self):
        """
        Schedules the connection to close once it has been idle for IDLE_DISCONNECT_SECS. The caller must hold
        self.__lock. Each call bumps the activity counter so a close scheduled by an earlier call is skipped if any
        command has run since; the close itself also takes the lock so it can never cut off a command in flight.
        """
        self.__activity += 1
        activity = self.__activity
        with self.__idle_timer_lock:
            if self.__idle_timer is not None:
                self.__idle_timer.cancel()
            self.__idle_timer = threading.Timer(IDLE_DISCONNECT_SECS, self.__close_if_idle, args=(activity,))
            self.__idle_timer.daemon = True
            self.__idle_timer.start()

    def __close_if_idle(self, activity: int):
        with self.__lock:
            if activity == self.__activity:
                self.__executor.disconnect(fail=False)
            else:
                logger.debug('Skipping idle disconnect, the connection has been used since it was scheduled')

    def __hard_disconnect(self):
        """ Closes the connection now. The caller must hold self.__lock. """
        self.__activity += 1
        self.__executor.disconnect(fail=False)

    def get(self, command):
        with self.__lock:
            try:
                cmd = Command[command]
                self.__connect()
                val = self.__executor.get(cmd)
                self.__disconnect()
                return self.__to_response(val)
            except KeyError:
                logger.warning(f"Ignoring unknown command {command}")
                return None
            except CommandNack:
                logger.exception(f"Command NACKed - GET {command}")
                self.__hard_disconnect()
                return -1
            except:
                logger.exception(f"Unexpected failure while executing cmd: {command}")
                self.__hard_disconnect()
                return -1

    @staticmethod
    def __to_response(val):
        """ Converts a value read from the PJ into something JSON serialisable. """
        if val is None or isinstance(val, Enum):
            return val.name if val is not None else None
        if isinstance(val, str):
            return val.replace('"', '').strip()
        if isinstance(val, int):
            # Numeric and its subclasses
            return int(val)
        if isinstance(val, list):
            # binary data e.g. gamma tables
            return list(val)
        return str(val)

    def send(self, commands) -> SendResult:
        """
        Sends the commands to the PJ, one at a time, in order. Concurrent callers are serialised by self.__lock so the
        PJ only ever sees one command at a time. A command that fails (NACK, timeout, dropped connection) is retried
        up to COMMAND_ATTEMPTS times, RETRY_DELAY_SECS apart, since the PJ refuses commands while it is still applying
        the previous one (e.g. a picture mode change).
        """
        result = SendResult()
        with self.__lock:
            sent = []
            for command in commands:
                if command[0:5] == 'PAUSE':
                    try:
                        sleep_secs = float(command[5:])
                    except ValueError:
                        logger.error(f"Ignoring invalid pause {command}")
                        result.unknown.append(command)
                        continue
                    logger.info(f"Sleeping for {sleep_secs:.3f}")
                    sleep(sleep_secs)
                    continue
                for cmd in self.__pj_macros.get(command, [command]):
                    try:
                        c, e, v = self.__execute_with_retry(cmd)
                    except UnknownCommand:
                        result.unknown.append(cmd)
                        continue
                    except Exception as ex:
                        result.failed.append(cmd)
                        result.errors.append(f'{cmd}: {ex!r}')
                        continue
                    sent.append((c, e))
                    if v:
                        result.values.append(v)
            self.__disconnect()
        if self.__mqtt and sent:
            self.__update_state_if_necessary(sent)
        return result

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

    def __execute_with_retry(self, cmd) -> Tuple[Command, Union[Enum, Numeric], Any]:
        """ The caller must hold self.__lock. Raises UnknownCommand, or the last error once all attempts fail. """
        cmd_enum, tok = self.__parse(cmd)
        # setting a value is idempotent so a failed attempt can safely be repeated, a toggle or navigation key isn't
        attempts = 1 if cmd_enum == Command.Remote and tok in NO_RETRY_RC else COMMAND_ATTEMPTS
        for attempt in range(1, attempts + 1):
            try:
                logger.info(f"Executing {cmd}{f' (attempt {attempt})' if attempt > 1 else ''}")
                self.__connect()  # no-op when already connected
                return cmd_enum, tok, self.__executor.set(cmd_enum, tok)
            except Exception:
                if attempt == attempts:
                    logger.exception(f"Failed to execute {cmd} after {attempt} attempts")
                    self.__hard_disconnect()
                    raise
                logger.warning(f"Failed to execute {cmd} (attempt {attempt}), retrying in {RETRY_DELAY_SECS}s",
                               exc_info=True)
                self.__hard_disconnect()
                sleep(RETRY_DELAY_SECS)

    @staticmethod
    def __parse(cmd) -> Tuple[Command, Union[Enum, Numeric]]:
        """ Turns e.g. PictureMode.PictureMode.Natural into (Command.PictureMode, PictureMode.Natural). """
        tokens = cmd.split('.')
        if len(tokens) != 3:
            logger.error(f"Ignoring unknown command {cmd}")
            raise UnknownCommand(cmd)
        try:
            cmd_enum = Command[tokens[0]]
        except KeyError:
            logger.error(f"Ignoring unknown command {cmd}")
            raise UnknownCommand(cmd)
        if not isinstance(cmd_enum.value, tuple) or cmd_enum.value[1].__name__ != tokens[1]:
            logger.error(f"Ignoring unknown command {cmd}")
            raise UnknownCommand(cmd)
        cmd_arg_enum = cmd_enum.value[1]
        try:
            if issubclass(cmd_arg_enum, Enum):
                return cmd_enum, cmd_arg_enum[tokens[2]]
            if issubclass(cmd_arg_enum, Numeric):
                return cmd_enum, Numeric(int(tokens[2]))
        except (KeyError, ValueError):
            logger.error(f"Ignoring unknown value in {cmd}")
            raise UnknownCommand(cmd)
        logger.warning(f"Unsupported value type for {cmd} - {cmd_arg_enum.__name__}")
        raise UnknownCommand(cmd)
