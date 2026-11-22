import threading
import time
from types import SimpleNamespace

import pytest
from flask import Flask
from flask_restx import Api

import cmdserver.pjcontroller as pjc
from cmdserver.apis import pj as pj_api
from cmdserver.jvc import CommandNack
from cmdserver.jvccommands import Command, PictureMode

NATURAL = 'PictureMode.PictureMode.Natural'
USER2 = 'PictureMode.PictureMode.User2'


class FakeExecutor:
    """ Stands in for jvc.CommandExecutor: one connection, records what the PJ would see. """

    def __init__(self, host=None, password=None):
        self.connected = False
        self.connects = 0
        self.disconnects = 0
        self.sent = []
        self.set_delay = 0.0
        self.failures_left = 0
        self.active = 0
        self.max_active = 0
        self.dropped_mid_command = False
        self.__guard = threading.Lock()

    def connect(self):
        if not self.connected:
            self.connected = True
            self.connects += 1

    def disconnect(self, fail=True):
        if self.connected:
            self.connected = False
            self.disconnects += 1

    def set(self, cmd, val, verify=True):
        assert self.connected, 'command sent on a closed connection'
        with self.__guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.set_delay:
                time.sleep(self.set_delay)
            if not self.connected:
                self.dropped_mid_command = True
            if self.failures_left:
                self.failures_left -= 1
                raise CommandNack('busy')
            self.sent.append((cmd, val))
        finally:
            with self.__guard:
                self.active -= 1


@pytest.fixture
def fast_timings(monkeypatch):
    monkeypatch.setattr(pjc, 'IDLE_DISCONNECT_SECS', 0.05)
    monkeypatch.setattr(pjc, 'RETRY_DELAY_SECS', 0.01)


@pytest.fixture
def executor(monkeypatch, fast_timings):
    fake = FakeExecutor()
    monkeypatch.setattr(pjc, 'CommandExecutor', lambda host, password=None: fake)
    return fake


def make_controller(macros=None):
    cfg = SimpleNamespace(pj_ip='127.0.0.1', pj_password=None, pj_macros=macros or {})
    return pjc.PJController(cfg, None)


def test_sends_command(executor):
    result = make_controller().send([NATURAL])
    assert result.failed == [] and result.unknown == []
    assert executor.sent == [(Command.PictureMode, PictureMode.Natural)]


def test_concurrent_sends_are_serialised(executor):
    executor.set_delay = 0.05
    controller = make_controller()
    threads = [threading.Thread(target=controller.send, args=([cmd],)) for cmd in (NATURAL, USER2, NATURAL)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert executor.max_active == 1
    assert len(executor.sent) == 3


def test_idle_disconnect_does_not_cut_off_a_command_in_flight(executor):
    controller = make_controller()
    controller.send([NATURAL])
    # the next command starts before the idle close is due and is still running when it fires
    time.sleep(0.03)
    executor.set_delay = 0.1
    result = controller.send([USER2])
    assert result.failed == []
    assert not executor.dropped_mid_command
    assert executor.connects == 1


def test_connection_closes_once_idle(executor):
    make_controller().send([NATURAL])
    assert executor.connected
    time.sleep(0.15)
    assert not executor.connected
    assert executor.disconnects == 1


def test_refused_command_is_retried(executor):
    executor.failures_left = 2
    result = make_controller().send([NATURAL])
    assert result.failed == []
    assert executor.sent == [(Command.PictureMode, PictureMode.Natural)]


def test_command_refused_on_every_attempt_is_reported(executor):
    executor.failures_left = pjc.COMMAND_ATTEMPTS
    result = make_controller().send([NATURAL, USER2])
    assert result.failed == [NATURAL]
    assert len(result.errors) == 1
    # the next command in the batch still goes out, on a fresh connection
    assert executor.sent == [(Command.PictureMode, PictureMode.User2)]


@pytest.mark.parametrize('cmd', ['Nope', 'Nope.Nope.Nope', 'PictureMode.Anamorphic.Off',
                                 'PictureMode.PictureMode.Nope', 'Power.PowerState'])
def test_unknown_command_is_reported_and_not_sent(executor, cmd):
    result = make_controller().send([cmd])
    assert result.unknown == [cmd]
    assert executor.sent == []


def test_macro_sends_every_command(executor):
    result = make_controller({'both': [NATURAL, USER2]}).send(['both'])
    assert result.failed == []
    assert [v for _, v in executor.sent] == [PictureMode.Natural, PictureMode.User2]


def test_pause(executor):
    start = time.monotonic()
    make_controller().send([NATURAL, 'PAUSE0.05', USER2])
    assert time.monotonic() - start >= 0.05
    assert len(executor.sent) == 2


@pytest.fixture
def client(executor):
    app = Flask('test')
    api = Api(app, prefix='/api')
    for r in pj_api.api.resources:
        r.kwargs['resource_class_kwargs'] = {'pj_controller': make_controller()}
    api.add_namespace(pj_api.api)
    return app.test_client()


def test_api_ok(client):
    assert client.put('/api/1/pj', json=[NATURAL]).status_code == 200


def test_api_unknown_is_404(client):
    resp = client.put('/api/1/pj', json=['Nope.Nope.Nope'])
    assert resp.status_code == 404
    assert resp.json == {'unknown': ['Nope.Nope.Nope']}


def test_api_failure_is_500(client, executor):
    executor.failures_left = pjc.COMMAND_ATTEMPTS
    resp = client.put('/api/1/pj', json=[NATURAL])
    assert resp.status_code == 500
    assert resp.json['failed'] == [NATURAL]


def test_idempotent_remote_code_is_retried(executor):
    executor.failures_left = 1
    result = make_controller().send(['Remote.RemoteCode.InstallationMode1'])
    assert result.failed == []
    assert len(executor.sent) == 1


@pytest.mark.parametrize('cmd', ['Remote.RemoteCode.Anamorphic_Toggle', 'Remote.RemoteCode.Up',
                                 'Remote.RemoteCode.Menu', 'Remote.RemoteCode.Back'])
def test_toggle_or_navigation_is_never_retried(executor, cmd):
    executor.failures_left = 1
    result = make_controller().send([cmd])
    assert result.failed == [cmd]
    assert executor.sent == []
