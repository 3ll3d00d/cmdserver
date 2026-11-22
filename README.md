Configuration
-------------

Example config

    # commands can have defaults added via the defaults item
    # if icon is not supplied then it is defaulted to <item name>.ico
    # command title must be a zone name if it is played by jriver
    commands:
      defaults:
        exe: 'x:\mc_scripts\ezmote.exe'
        volume: 0.40
        stopAll: true
      close:
        args: ['CloseAll']
        # icons prefixed with mi are special cased to be a material-ui icon 
        icon: 'mi/close'
        # idx is the order in which the commands will be listed in the ui
        idx: 0
        title: 'Close'
      music:
        args: ['jriver', 'Music']
        icon: 'mi/library_music'
        idx: 1
        title: 'Music'
        # sets the top appbar to the jriver selector which is based on MCWS browseChildren 
        control: 'jriver'
        # nodeId is the start point to navigate through MCWS browseChildren
        nodeId: 1
        stopAll: false
      video:
        args: ['jriver', 'Film']
        icon: 'mi/movie'
        idx: 2
        title: 'Films'
        control: 'jriver'
        nodeId: 3
        stopAll: false
      netflix:
        args: ['netflix']
        idx: 3
        title: 'Netflix'
        playingNowId: 5000
        # if zoneId is provided, the specified zone will be activated when the command is sent 
        zoneId: 10009
      virgin:
        args: ['tivo']
        idx: 4
        title: 'Virgin'
        control: 'tivo'
        playingNowId: 6000
        zoneId: 10009
      iplayer:
        args: ['iplayer']
        idx: 5
        title: 'BBC iPlayer'
        playingNowId: 1000
        zoneId: 10009
      amazon:
        args: ['amazon']
        idx: 6
        title: 'Amazon Video'
        playingNowId: 4000
        zoneId: 10009
      all4:
        args: ['all4']
        idx: 7
        title: 'All4'
        playingNowId: 3000
        zoneId: 10009
      itv:
        args: ['itv']
        idx: 8
        title: 'ITV'
        playingNowId: 2000
        zoneId: 10009
      radio:
        args: ['jriver', 'Radio']
        icon: 'mi/radio'
        idx: 9
        title: 'Radio'
        control: 'jriver'
        nodeId: 1000
        stopAll: false
      playlists:
        args: ['jriver', 'Playlist']
        icon: 'mi/playlist play'
        idx: 10
        title: 'Playlists'
        control: 'jriver'
        nodeId: 4
        stopAll: false
    iconPath: 'x:\mc_scripts\icons'
    playingNowExe: 'x:\mc_scripts\getPlayingNow.exe'
    debug: false
    debugLogging: true
    host: megatron
    port: 53199
    # use for debug
    webappPath: 'C:\Users\mattk\github\ezmote\build'

Install
-------

* PyPI: `pip install ezmote-cmdserver`, then run `cmdserver`
* Windows: `cmdserver.exe` is attached to each [release](https://github.com/3ll3d00d/cmdserver/releases)
* Docker: `ghcr.io/3ll3d00d/cmdserver` (`latest` = last release, `edge` = master, or a version e.g. `2.1.0`), for
  linux/amd64 and linux/arm64. It listens on 53199 and reads `cmdserver.yml` from `$CMDSERVER_CONFIG_HOME` if set,
  else `~/.cmdserver` (`/root/.cmdserver` in the container), so map a volume to one of those. It replaces
  `ghcr.io/3ll3d00d/cmdserver-image`.

Config is read from `$CMDSERVER_CONFIG_HOME/cmdserver.yml`, else `~/.cmdserver/cmdserver.yml`. A default config is
written there on first start.

Projector commands
------------------

`PUT /api/1/pj` takes a JSON list of commands, e.g. `["PictureMode.PictureMode.Natural", "PAUSE2.5",
"Remote.RemoteCode.InstallationMode1"]`, or the names of `pjmacros`. Commands go to the projector one at a time,
in order; concurrent requests are queued so the projector only ever sees one command at a time. A command the
projector refuses (e.g. while it is still applying a picture mode change) is retried, 3 attempts in all, 1.5s
apart, except toggles and menu/navigation keys, which are only ever sent once. The response is:

* `200` – every command was acknowledged
* `404` – `{"unknown": [...]}`, commands that were not recognised (nothing failed)
* `500` – `{"failed": [...], "unknown": [...], "errors": [...]}`, commands the projector did not acknowledge even
  after retries
* `501` – no `pjip` is configured

Development
-----------

Uses [uv](https://docs.astral.sh/uv/):

    uv sync
    uv run pytest
    uv run cmdserver

Build the Windows exe with `uv sync --group exe && uv run pyinstaller cmdserver.spec`, and the image with
`docker build -f docker/Dockerfile .`.

Releases
--------

The version comes from the git tag (hatch-vcs), there is no version to bump. Pushing a tag such as `2.1.0` runs
`create-app.yaml` (tests, GitHub release, PyPI, Windows exe) and `docker.yaml` (versioned + `latest` image).
