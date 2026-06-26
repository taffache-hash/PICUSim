# -*- mode: python ; coding: utf-8 -*-
# PICUSim.spec — PyInstaller v3.2.0  |  entry: start_pdt_api.py

block_cipher = None

added_datas = [
    ('ui',                    'ui'),
    ('scenarios',             'scenarios'),
    ('authored_scenarios',    'authored_scenarios'),
    ('benchmarks',            'benchmarks'),
    ('data',                  'data'),
    ('metadata',              'metadata'),
    ('events',                'events'),
    ('reference_ranges.yaml', '.'),
    ('VERSION',               '.'),
]

hidden_imports = [
    # --- uvicorn ---
    'uvicorn', 'uvicorn.main', 'uvicorn.config', 'uvicorn.server',
    'uvicorn.loops', 'uvicorn.loops.asyncio', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off',
    'uvicorn.logging', 'uvicorn.middleware', 'uvicorn.middleware.proxy_headers',
    # --- fastapi / starlette ---
    'fastapi', 'fastapi.staticfiles', 'fastapi.templating', 'fastapi.responses',
    'fastapi.middleware', 'fastapi.middleware.cors',
    'starlette', 'starlette.routing', 'starlette.responses', 'starlette.staticfiles',
    'starlette.templating', 'starlette.middleware', 'starlette.middleware.cors',
    'starlette.websockets',
    # --- async / http ---
    'anyio', 'anyio._backends._asyncio', 'anyio._backends._trio',
    'h11', 'websockets', 'wsproto', 'httptools',
    # --- scientific ---
    'numpy', 'scipy', 'scipy.special', 'scipy.integrate', 'scipy.interpolate',
    'scipy.optimize', 'scipy.signal', 'scipy.stats', 'scipy.linalg',
    'pandas', 'yaml', 'plotly',
    # --- PICUSim: api ---
    'api', 'api.server', 'api.action_router', 'api.debrief', 'api.instructor',
    'api.methods_appendix', 'api.performance', 'api.reproducibility',
    'api.scenario_authoring', 'api.schemas', 'api.session', 'api.session_io',
    'api.state_profiles', 'api.training',
    # --- PICUSim: core ---
    'core', 'core.airway_events', 'core.base_module', 'core.bus',
    'core.cardiac_arrest_events', 'core.cardiovascular_scaling',
    'core.dependencies', 'core.engine', 'core.events', 'core.failure_to_rescue',
    'core.profile_scaling', 'core.profiles', 'core.quality',
    'core.recovery_engine', 'core.scenario', 'core.scenario_engine_v2',
    'core.scenario_timing',
    # --- PICUSim: modules ---
    'modules',
    'modules.acidbase', 'modules.acidbase.electrolytes',
    'modules.airway', 'modules.airway.intubation_physiology', 'modules.airway.obstruction',
    'modules.analgosedation', 'modules.analgosedation.pain_stress_sedation',
    'modules.cardiovascular', 'modules.cardiovascular.baroreflex',
    'modules.cardiovascular.circulation', 'modules.cardiovascular.heart',
    'modules.cardiovascular.heart_btb', 'modules.cardiovascular.shock',
    'modules.cardiovascular.shock_labels',
    'modules.coagulation', 'modules.coagulation.coagulation',
    'modules.decision', 'modules.decision.epals',
    'modules.endocrine', 'modules.endocrine.stress_axis',
    'modules.hematology', 'modules.hematology.oxygen_transport',
    'modules.hepatic', 'modules.hepatic.liver',
    'modules.infection', 'modules.infection.antimicrobial_basic',
    'modules.metabolism', 'modules.metabolism.metabolism',
    'modules.neurology', 'modules.neurology.functional', 'modules.neurology.icp',
    'modules.nutrition', 'modules.nutrition.catabolism', 'modules.nutrition.glucose',
    'modules.perfusion', 'modules.perfusion.organ_perfusion',
    'modules.pharmacology', 'modules.pharmacology.ino', 'modules.pharmacology.pk_pd',
    'modules.pharmacology.steroids', 'modules.pharmacology.transfusion',
    'modules.renal', 'modules.renal.aki_crrt', 'modules.renal.fluid_balance',
    'modules.respiratory', 'modules.respiratory.airway_interface',
    'modules.respiratory.chemoreflex', 'modules.respiratory.gas_exchange',
    'modules.respiratory.mechanics',
    'modules.sepsis', 'modules.sepsis.advanced_sepsis',
    'modules.thermoregulation', 'modules.thermoregulation.thermoregulation',
    'modules.ventilator', 'modules.ventilator.ventilator', 'modules.ventilator.waveforms',
    # --- events ---
    'events',
    # --- misc ---
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
