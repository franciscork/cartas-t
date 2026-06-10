# -*- mode: python ; coding: utf-8 -*-
import os, site
from PyInstaller.utils.hooks import collect_all, collect_submodules

project_dir = SPECPATH  # PyInstaller defines SPECPATH as the spec file's directory

# Collect pygame binaries, datas, and submodules
datas_pygame, binaries_pygame, hiddenimports_pygame = collect_all('pygame')

# Collect juego_simmoon submodules too
hiddenimports_juego = collect_submodules('juego_simmoon')

user_site = site.getusersitepackages()
pathex = [user_site] if user_site else []

base_datas = [
    ('buildings_misc_pixel', 'buildings_misc_pixel'),
    ('businesses_pixel', 'businesses_pixel'),
    ('characters_pixel', 'characters_pixel'),
    ('civic_pixel', 'civic_pixel'),
    ('decorations_pixel', 'decorations_pixel'),
    ('government_pixel', 'government_pixel'),
    ('greenhouses_pixel', 'greenhouses_pixel'),
    ('housing_pixel', 'housing_pixel'),
    ('industry_pixel', 'industry_pixel'),
    ('infrastructure_pixel', 'infrastructure_pixel'),
    ('life_support_pixel', 'life_support_pixel'),
    ('lunar_flora_pixel', 'lunar_flora_pixel'),
    ('lunar_map_pixel', 'lunar_map_pixel'),
    ('lunar_sites_pixel', 'lunar_sites_pixel'),
    ('risk_management_pixel', 'risk_management_pixel'),
    ('roads_pixel', 'roads_pixel'),
    ('solar_energy_pixel', 'solar_energy_pixel'),
    ('transport_pixel', 'transport_pixel'),
    ('ui_elements_pixel', 'ui_elements_pixel'),
    ('vehicles_pixel', 'vehicles_pixel'),
    ('votes.json', '.'),
]

a = Analysis(
    [os.path.join(project_dir, 'simmoon_menu.py')],
    pathex=pathex,
    binaries=binaries_pygame,
    datas=base_datas + datas_pygame,
    hiddenimports=['pygame', 'juego_simmoon', 'simmoon_mecanicas'] + hiddenimports_pygame + hiddenimports_juego,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SIMMOON_1_4_0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
