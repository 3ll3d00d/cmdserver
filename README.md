Getting Started
---------------

    conda create --name cmdserver python=3.6
    activate cmdserver
    pip install flask-restful
    conda install PyYAML
    conda install -c conda-forge plumbum
    conda install -c conda-forge netifaces
 
pyinstaller
-----------

    conda install -c conda-forge pyinstaller

Create a spec file changing the paths as appropriate

	# -*- mode: python -*-

	block_cipher = None

	a = Analysis(['cmdserver\\cmdserver.py'],
				 pathex=['C:\\Users\\mattk\\github\\cmdserver'],
				 binaries=[],
				 datas=[],
				 hiddenimports=[],
				 hookspath=[],
				 runtime_hooks=[],
				 excludes=['pkg_resources'],
				 win_no_prefer_redirects=False,
				 win_private_assemblies=False,
				 cipher=block_cipher)
	pyz = PYZ(a.pure, a.zipped_data,
				 cipher=block_cipher)
	exe = EXE(pyz,
			  a.scripts,
			  a.binaries,
			  Tree('c:\\Users\\mattk\github\ezmote\\build', prefix='ui'),
			  a.zipfiles,
			  a.datas,
			  name='ezmote_server',
			  debug=False,
			  strip=False,
			  upx=True,
			  runtime_tmpdir=None,
			  console=True )
    
Build the UI

    yarn build
    
Build the exe

    pyinstaller --clean --log-level=INFO ezmote.spec

    
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
    useTwisted: true
    # use for debug
    webappPath: 'C:\Users\mattk\github\ezmote\build'
