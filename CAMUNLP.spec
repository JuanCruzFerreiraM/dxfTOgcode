# -*- mode: python ; coding: utf-8 -*-
# PyInstaller injects Analysis, PYZ, EXE, COLLECT into the namespace when processing this file.
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

block_cipher = None

ROOT = Path(SPECPATH).resolve()
SRC_MAIN = ROOT / "src" / "main.py"

datas = [
    (str(ROOT / "src" / "gui" / "icons"), "src/gui/icons"),
    (str(ROOT / "VERSION.txt"), "."),
    (str(ROOT / "Manual_de_usuario.pdf"), "."),
]

try:
    import ifcopenshell

    ifc_root = Path(ifcopenshell.__file__).resolve().parent
    for exp in ifc_root.rglob("*.exp"):
        rel_parent = exp.parent.relative_to(ifc_root)
        dest = Path("ifcopenshell") / rel_parent
        datas.append((str(exp), str(dest)))
except Exception as e:
    raise RuntimeError(
        "ifcopenshell is required to build; install project dependencies in the build venv."
    ) from e

datas += collect_data_files("matplotlib")

binaries = []
binaries += collect_dynamic_libs("shapely")
binaries += collect_dynamic_libs("rtree")

hiddenimports = [
    "contourpy",
    "contourpy._contourpy",
    "ezdxf",
    "lark",
    "ifcopenshell",
    "ifcopenshell.geom",
    "ifcopenshell.util",
    "ifcopenshell.util.placement",
    "shapely",
    "shapely.geometry",
    "rtree",
    "trimesh",
    "networkx",
    "PIL",
    "PIL.Image",
]
hiddenimports += collect_submodules("ifcopenshell.geom")
hiddenimports += collect_submodules("trimesh")

a = Analysis(
    [str(SRC_MAIN)],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Do not exclude numpy.testing: SciPy/Shapely and other deps import it at runtime.
    excludes=[
        "PyQt6.QtNetwork",
        "PyQt6.QtWebEngine",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "pytest",
        "numpy.tests",
        "scipy.tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CAMUNLP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "src" / "gui" / "icons" / "gcodegerator.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CAMUNLP",
)
