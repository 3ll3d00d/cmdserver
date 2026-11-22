import logging
from unittest.mock import MagicMock

import pytest

from cmdserver import jvc
from cmdserver.jvccommands import Command, RemoteCode

ACK_MENU = jvc.Header.ack.value + jvc.UNIT_ID + b'RC' + jvc.END


class FakeConnection:
    """ scripted stand in for jvc.Connection: each send/expect pops the next outcome """

    def __init__(self, send_outcomes=(), expect_outcomes=()):
        self.send_outcomes = list(send_outcomes)
        self.expect_outcomes = list(expect_outcomes)
        self.sent = []
        self.reconnects = 0

    def send(self, data):
        outcome = self.send_outcomes.pop(0) if self.send_outcomes else None
        if outcome:
            raise outcome
        self.sent.append(data)

    def expect(self, expected, timeout=1):
        outcome = self.expect_outcomes.pop(0) if self.expect_outcomes else 0
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def reconnect(self):
        self.reconnects += 1


def executor_on(conn):
    protocol = jvc.Protocol.__new__(jvc.Protocol)
    protocol.conn = conn
    protocol.reconnect = False
    executor = jvc.CommandExecutor.__new__(jvc.CommandExecutor)
    executor.conn = protocol
    return executor


def test_command_that_was_never_sent_is_resent_on_a_new_connection():
    conn = FakeConnection(send_outcomes=[jvc.Closed('reset')])
    executor_on(conn).set(Command.Remote, RemoteCode.Menu)
    assert conn.reconnects == 1
    assert len(conn.sent) == 1


def test_connection_closed_while_waiting_for_ack_is_an_error_not_a_success():
    conn = FakeConnection(expect_outcomes=[jvc.Closed('Connection closed by projector')])
    with pytest.raises(jvc.Closed):
        executor_on(conn).set(Command.Remote, RemoteCode.Menu)
    # it may have reached the PJ, so it is not resent
    assert len(conn.sent) == 1
    assert conn.reconnects == 0


def test_command_is_not_resent_more_than_once():
    conn = FakeConnection(send_outcomes=[jvc.Closed('reset'), jvc.Closed('reset')])
    with pytest.raises(jvc.Closed):
        executor_on(conn).set(Command.Remote, RemoteCode.Menu)
    assert conn.sent == []


def test_next_command_reconnects_after_a_closed_connection():
    conn = FakeConnection(expect_outcomes=[jvc.Closed('closed')])
    executor = executor_on(conn)
    with pytest.raises(jvc.Closed):
        executor.set(Command.Remote, RemoteCode.Menu)
    executor.set(Command.Remote, RemoteCode.Menu)
    assert conn.reconnects == 1


@pytest.mark.parametrize('error', [ConnectionResetError, BrokenPipeError, ConnectionAbortedError])
def test_dropped_socket_is_reported_as_closed(error):
    conn = jvc.Connection('127.0.0.1')
    sock = MagicMock()
    sock.sendall.side_effect = error()
    conn._Connection__socket = sock
    with pytest.raises(jvc.Closed):
        conn.send(b'data')


def test_password_is_not_logged(caplog):
    with caplog.at_level(logging.DEBUG, logger='jvc'):
        jvc.Connection('127.0.0.1', password='s3cret-pw')
    assert 's3cret-pw' not in caplog.text
