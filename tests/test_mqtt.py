import logging
import warnings
from unittest.mock import MagicMock

import pytest
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

from cmdserver.mqtt import MQTT


@pytest.fixture
def broker_less(monkeypatch):
    # no broker: stop the client actually connecting or starting its network thread
    import paho.mqtt.client as paho
    monkeypatch.setattr(paho.Client, 'connect_async', lambda *a, **kw: None)
    monkeypatch.setattr(paho.Client, 'loop_start', lambda *a, **kw: None)


def connack(name: str) -> ReasonCode:
    return ReasonCode(PacketTypes.CONNACK, name)


def client_of(m: MQTT):
    return m._MQTT__client


def test_client_uses_current_callback_api(broker_less):
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        m = MQTT('127.0.0.1')
    client = client_of(m)
    # paho calls the v2 callbacks with these arguments
    client.on_connect(client, None, {}, connack('Success'), None)
    client.on_disconnect(client, None, {}, connack('Success'), None)


def test_rejected_connection_is_logged_as_error(broker_less, caplog):
    m = MQTT('127.0.0.1')
    client = client_of(m)
    with caplog.at_level(logging.INFO, logger='mqtt'):
        client.on_connect(client, None, {}, connack('Not authorized'), None)
    assert [r.levelno for r in caplog.records if 'MQTT' in r.message] == [logging.ERROR]
    assert 'Failed to connect' in caplog.text


def test_successful_connection_is_logged_as_info(broker_less, caplog):
    m = MQTT('127.0.0.1')
    client = client_of(m)
    with caplog.at_level(logging.INFO, logger='mqtt'):
        client.on_connect(client, None, {}, connack('Success'), None)
    assert [r.levelno for r in caplog.records if 'Connected' in r.message] == [logging.INFO]


def test_last_will_marks_pj_offline(broker_less):
    client = client_of(MQTT('127.0.0.1'))
    will = client._will
    assert client._will_topic == b'cmdserver/pj/available'
    assert client._will_payload == b'offline'
    assert client._will_retain is True
    assert client._will_qos == 1
    assert will


def test_no_last_will_when_disabled(broker_less):
    client = client_of(MQTT('127.0.0.1', will_source=None))
    assert not client._will


def test_shutdown_when_not_connected(broker_less):
    MQTT('127.0.0.1').shutdown()


def test_shutdown_publishes_offline_and_disconnects(broker_less, monkeypatch):
    m = MQTT('127.0.0.1')
    client = client_of(m)
    published = []
    info = MagicMock()

    def publish(topic, qos=0, payload=None, retain=False):
        published.append((topic, payload, qos, retain))
        return info

    monkeypatch.setattr(client, 'publish', publish)
    monkeypatch.setattr(client, 'is_connected', lambda: True)
    disconnect = MagicMock()
    monkeypatch.setattr(client, 'disconnect', disconnect)
    loop_stop = MagicMock()
    monkeypatch.setattr(client, 'loop_stop', loop_stop)

    m.online('pj')
    published.clear()
    m.shutdown()
    m.shutdown()  # atexit may call it again; second call is a no-op

    assert published == [('cmdserver/pj/available', 'offline', 1, True)]
    info.wait_for_publish.assert_called_once()
    disconnect.assert_called_once()
    loop_stop.assert_called_once()


def test_shutdown_skips_sources_already_offline(broker_less, monkeypatch):
    m = MQTT('127.0.0.1')
    client = client_of(m)
    published = []
    monkeypatch.setattr(client, 'publish', lambda topic, **kw: published.append(topic) or MagicMock())
    monkeypatch.setattr(client, 'is_connected', lambda: True)
    monkeypatch.setattr(client, 'disconnect', MagicMock())

    m.online('pj')
    m.offline('pj')
    published.clear()
    m.shutdown()

    assert published == []


def test_shutdown_survives_failed_offline_publish(broker_less, monkeypatch):
    m = MQTT('127.0.0.1')
    client = client_of(m)
    info = MagicMock()
    info.wait_for_publish.side_effect = RuntimeError('Message publish failed')
    monkeypatch.setattr(client, 'publish', lambda *a, **kw: info)
    monkeypatch.setattr(client, 'is_connected', lambda: True)
    disconnect = MagicMock()
    monkeypatch.setattr(client, 'disconnect', disconnect)

    m.online('pj')
    m.shutdown()

    disconnect.assert_called_once()
