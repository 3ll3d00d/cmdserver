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
    
    
    
Configuration
-------------

Example config

    # commands can have defaults added via the defaults item
    # if icon is not supplied then it is defaulted to <item name>.ico
    commands:
      defaults:
        exe: 'x:\mc_scripts\launch_player.exe'
      music:
        args: ['jriver', 'Music']
        icon: 'Audio_sm.ico'
        nodeId: 1
        idx: 0
        title: 'Music'
        control: 'jriver'
      video:
        args: ['jriver', 'Video']
        icon: 'Video_sm.ico'
        nodeId: 3
        idx: 1
        title: 'Video'
        control: 'jriver'
      netflix:
        args: ['netflix']
        idx: 2
        title: 'Netflix'
      virgin:
        args: ['tivo']
        idx: 3
        title: 'Virgin'
        control: 'tivo'
      iplayer:
        args: ['iplayer']
        idx: 4
        title: 'BBC iPlayer'
      amazon:
        args: ['amazon']
        idx: 5
        title: 'Amazon Video'
      all4:
        args: ['all4']
        idx: 6
        title: 'All4'
      itv:
        args: ['itv']
        idx: 7
        title: 'ITV'
    iconPath: 'x:\mc_scripts\icons'
    debug: false
    debugLogging: true
    host: megatron
    port: 53199
    useTwisted: true
    # use for debug
    webappPath: 'C:\Users\mattk\github\jravr\build'
