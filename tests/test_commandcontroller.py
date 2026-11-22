import sys
from types import SimpleNamespace

import pytest

from cmdserver.commandcontroller import CommandController, RemoteCommandExecutor

PRINT_ARGS = ['-c', 'import sys; print(sys.argv[1:])']


def controller(commands):
    return CommandController(SimpleNamespace(commands=commands))


def test_runs_without_a_defaults_block():
    c = controller({'cmd': {'exe': sys.executable, 'args': PRINT_ARGS}})
    assert c.get_command('cmd')['icon'] == 'cmd.ico'
    rc, out, _ = c.execute('cmd')
    assert rc == 0


def test_local_command_runs_with_only_its_configured_args():
    rc, out, _ = controller({'cmd': {'exe': sys.executable, 'args': PRINT_ARGS}}).execute('cmd')
    assert out.strip() == '[]'


def test_command_exe_wins_over_default_exe():
    c = controller({'defaults': {'exe': 'does-not-exist-anywhere'},
                    'cmd': {'exe': sys.executable, 'args': PRINT_ARGS}})
    assert c.execute('cmd')[0] == 0


def test_default_exe_used_when_command_has_none():
    c = controller({'defaults': {'exe': sys.executable, 'zoneId': 2}, 'cmd': {'args': PRINT_ARGS}})
    assert c.execute('cmd')[0] == 0
    assert c.get_command('cmd')['zoneId'] == 2


def test_unknown_command():
    assert controller({}).execute('nope') is None


def test_remote_command_needs_a_prefix():
    with pytest.raises(ValueError, match='remote_prefix'):
        controller({'cmd': {'remote': True}})


def test_remote_command(httpserver):
    httpserver.expect_request('/cmds/cmd', method='PUT').respond_with_data('')
    c = controller({'defaults': {'remote_prefix': httpserver.url_for('/cmds')}, 'cmd': {'remote': True}})
    assert c.execute('cmd') == [0, '']


def test_remote_executor_reports_failure(httpserver):
    httpserver.expect_request('/x', method='PUT').respond_with_data('boom', status=503)
    assert RemoteCommandExecutor(httpserver.url_for('/x')).run() == [2, '503 - boom']
