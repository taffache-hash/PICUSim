# -*- mode: python ; coding: utf-8 -*-
# PICUSim.spec — PyInstaller build specification for PICUSim v3.2.0
# Entry point: start_pdt_api.py  |  Output: dist/PICUSim.exe (one-file, Windows x64)

block_cipher = None

added_datas = [
    ('ui',                  'ui'),
    ('scenarios',           'scenarios'),
    ('authored_scenarios',  'authored_scenarios'),
    ('benchmarks',          'benchmarks'),
    ('data',                'data'),
    ('metadata',            'metadata'),
    ('events',              'events'),
    ('reference_ranges.yaml', '.'),
    ('VERSION',             '.'),
]

hidden_imports = [
    # uvicorn
    'uvicorn', 'uvicorn.main', 'uvicorn.config', 'uvicorn.server',
    'uvicorn.loops', 'uvicorn.loops.asyncio', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off',
    'uvicorn.logging', 'uvicorn.middleware', 'uvicorn.middleware.proxy_headers',
    # fastapi / starlette
    'fastapi', 'fastapi.staticfiles', 'fastapi.templating', 'fastapi.responses',
    'fastapi.middleware', 'fastapi.middleware.cors',
    'starlette', 'starlette.routing', 'starlette.responses', 'starlette.staticfiles',
    'starlette.templating', 'starlette.middleware', 'starlette.middleware.cors',
    'starlette.websockets',
    # async / http
    'anyio', 'anyio._backends._asyncio', 'anyio._backends._trio',
    'h11', 'websockets', 'wsproto', 'httptools',
    # scientific
    'numpy', 'scipy', 'scipy.special', 'scipy.integrate', 'scipy.interpolate',
    'scipy.optimize', 'scipy.signal', 'scipy.stats', 'scipy.linalg',
    'pandas', 'yaml', 'plotly',
    # PICUSim internals
    'core', 'modules', 'api', 'events',
    'modules.acidbase', 'modules.airway', 'modules.analgosedation',
    'modules.cardiovascular', 'modules.coagulation', 'modules.decision',
    'modules.endocrine', 'modules.hematology', 'modules.hepatic',
    'modules.infection', 'modules.metabolism', 'modules.neurology',
    'modules.nutrition', 'modules.perfusion', 'modules.pharmacology',
    'modules.renal', 'modules.respiratory', 'modules.sepsis',
    'modules.thermoregulation', 'modules.ventilator',
    # misc
    'multipart', 'pydantic', 'pydantic.v1',
    'importlib.metadata', 'importlib.resources', 'pkg_resources',
    'packaging', 'charset_normalizer', 'idna', 'certifi', 'sniffio',
    'typing_extensions', 'logging.handlers',
]

a = Analysis(
    ['start_pdt_api.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'wx', 'PyQt5', 'PyQt6',
              'PySide2', 'PySide6', 'IPython', 'notebook',
              'jupyter', 'sphinx', 'docutils', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PICUSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
