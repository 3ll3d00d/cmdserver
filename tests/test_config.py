import os

from cmdserver.config import Config


def test_empty_config_file(tmp_path, monkeypatch):
    monkeypatch.setenv('CMDSERVER_CONFIG_HOME', str(tmp_path))
    (tmp_path / 'cmdserver.yml').write_text('')
    cfg = Config('cmdserver')
    assert cfg.commands == {}
    assert cfg.iconPath is None


def test_default_icon_path_is_not_the_home_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('CMDSERVER_CONFIG_HOME', str(tmp_path))
    cfg = Config('cmdserver')
    assert cfg.iconPath == os.path.join(str(tmp_path), 'icons')
    assert (tmp_path / 'cmdserver.yml').exists()
