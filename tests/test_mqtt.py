import warnings

import pytest

from cmdserver.mqtt import MQTT


@pytest.fixture
def broker_less(monkeypatch):
    # no broker: stop the client actually connecting or starting its network thread
    import paho.mqtt.client as paho
    monkeypatch.setattr(paho.Client, 'connect_async', lambda *a, **kw: None)
    monkeypatch.setattr(paho.Client, 'loop_start', lambda *a, **kw: None)


def test_client_uses_current_callback_api(broker_less):
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        m = MQTT('127.0.0.1')
    client = m._MQTT__client
    # paho calls the v2 callbacks with these arguments
    client.on_connect(client, None, {}, 0, None)
    client.on_disconnect(client, None, {}, 0, None)


def test_shutdown(broker_less):
    MQTT('127.0.0.1').shutdown()
