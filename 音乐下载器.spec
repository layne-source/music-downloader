# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\Program Files\\Python\\Python313\\Lib\\site-packages\\fake_useragent\\data', 'fake_useragent\\data'), ('D:\\Program Files\\Python\\Python313\\Lib\\site-packages\\PyQt5\\Qt5\\plugins\\platforms', 'PyQt5\\Qt5\\plugins\\platforms'), ('D:\\Program Files\\Python\\Python313\\Lib\\site-packages\\PyQt5\\Qt5\\bin', 'PyQt5\\Qt5\\bin')],
    hiddenimports=['PyQt5.sip', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'requests', 'bs4', 'lxml', 'Crypto'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['D:\\Music downloader\\pyqt5_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='音乐下载器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='音乐下载器',
)
