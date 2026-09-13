"""把自己的 .cube 收进清单：拷进 assets/cub/ + 往 assets/lutset.csv 追加一行。

    python3 scripts/import_cube.py 我的片子.cube --name "My Film" \
        [--label 我的片子] [--desc "一句话说明"]

name 同时决定内部 id 与资产文件名（去非字母数字后大写，所以名字里要有一段 ASCII 字母）。
分解成 .LTC 与画图标会在 ./build.sh 里自动做（也可手动跑 scripts/make_assets.py）。
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lutset
from paths import ASSETS, CUBDIR, ROOT


def stem_of(name):
    s = re.sub(r'[^0-9A-Za-z]', '', name).upper()
    if not s:
        raise SystemExit('name 里要有一段 ASCII 字母或数字（它决定 id 与文件名）：%r' % name)
    return s


def append_row(row):
    rows = [r for r in lutset.rows() if r['stem'] != row['stem']]
    rows.append(row)
    lutset.write_csv(os.path.join(ASSETS, 'lutset.csv'), rows)
    print('清单已更新：%d 支（顺序 = 菜单顺序，想调位置就编辑 assets/lutset.csv 的行顺序）'
          % len(rows))


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split('\n')[0])
    ap.add_argument('cube', help='你的 .cube 文件')
    ap.add_argument('--name', required=True, help='菜单里显示的名字（也决定 id / 文件名）')
    ap.add_argument('--label', default='', help='图标下方的中文短名（默认取 name）')
    ap.add_argument('--desc', default='', help='预览页那行小字（默认取 name）')
    a = ap.parse_args()

    if not os.path.isfile(a.cube):
        raise SystemExit('cube 不存在: %s' % a.cube)
    stem = stem_of(a.name)

    os.makedirs(CUBDIR, exist_ok=True)
    dst = os.path.join(CUBDIR, stem + '.CUB')
    shutil.copy2(a.cube, dst)
    print('已拷入 %s (%d B)' % (os.path.relpath(dst, ROOT), os.path.getsize(dst)))

    append_row({'name': a.name, 'label': a.label or a.name,
                'desc': a.desc or a.name, 'stem': stem, 'id': 'lut-' + stem.lower()})

    print('\n现在跑：./build.sh（会自动分解成 .LTC 并画图标）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
