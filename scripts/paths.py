"""路径真源：全部相对「仓库根」推导，不含绝对路径。

可用环境变量覆盖：OCLUT_ROOT / OCLUT_WORK / OCLUT_TOOLS / OCLUT_TREE / OCLUT_PYTHON
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _p(env, default):
    return os.path.abspath(os.environ.get(env) or default)


ROOT = _p('OCLUT_ROOT', os.path.join(_HERE, os.pardir))
TOOLS = _p('OCLUT_TOOLS', os.path.join(ROOT, 'tools'))
WORK = _p('OCLUT_WORK', os.path.join(ROOT, 'work'))
APK_DIR = os.path.join(WORK, 'apk')
TREE = _p('OCLUT_TREE', os.path.join(WORK, 'apktool_out'))

PATCHES = os.path.join(ROOT, 'patch')
ASSETS = os.path.join(ROOT, 'assets')
CUBDIR = os.path.join(ASSETS, 'cub')
LUTS = os.path.join(ASSETS, 'luts')
ICONS = os.path.join(ASSETS, 'icons')
DIST = os.path.join(ROOT, 'dist')


def rel(p):
    return os.path.relpath(p, ROOT)
