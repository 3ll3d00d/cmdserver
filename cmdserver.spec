# -*- mode: python -*-
import os

# work-around for https://github.com/pyinstaller/pyinstaller/issues/4064
import distutils

distutils_dir = getattr(distutils, 'distutils_path', None)
if distutils_dir is not None and distutils_dir.endswith('__init__.py'):
    distutils.distutils_path = os.path.dirname(distutils.distutils_path)


# helper functions
block_cipher = None
spec_root = os.path.abspath(SPECPATH)

a = Analysis(['src/cmdserver.py'],
             pathex=[spec_root],
             binaries=[],
             datas=[
                 ('src/VERSION', '.'),
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['pkg_resources'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          Tree(f"{spec_root}/ezmote", prefix='ui'),
          a.zipfiles,
          a.datas,
          name='cmdserver',
          debug=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=True)
