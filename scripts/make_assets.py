"""按清单把 assets/cub/*.CUB 分解成 assets/luts/*.LTC，并生成菜单图标。

`.LTC` 与图标都**不入库**（是生成物）：真源 = assets/lutset.csv + assets/cub/*.CUB + assets/icon.jpg。

    python3 scripts/make_assets.py           只补缺的（已有的不动，方便你手换某一支）
    python3 scripts/make_assets.py --force   全部重做

顺带清掉清单之外的陈旧 .LTC / 图标。图标需要 numpy + Pillow（缺了会跳过并提示）。
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lutset
from paths import CUBDIR, ICONS, LUTS, ROOT

JAR = os.path.join(ROOT, 'tools', 'lutbuild.jar')
OFF_ICON = 'lut-off.png'


def cube_of(stem):
    return os.path.join(CUBDIR, stem + '.CUB')


def ltc_of(stem):
    return os.path.join(LUTS, stem + '.LTC')


def build_ltc(rows, force):
    todo = [r['stem'] for r in rows if force or not os.path.isfile(ltc_of(r['stem']))]
    if not todo:
        print('.LTC 都在（要重做就加 --force）')
        return
    missing = [s for s in todo if not os.path.isfile(cube_of(s))]
    if missing:
        raise SystemExit('缺 cube：%s\n'
                         '放到 assets/cub/<STEM>.CUB，或用 scripts/import_cube.py 把 .cube 收进来'
                         % ', '.join(missing))
    if not os.path.isfile(JAR):
        raise SystemExit('缺 %s' % JAR)
    os.makedirs(LUTS, exist_ok=True)
    r = subprocess.run(['java', '-cp', JAR, 'BuildLuts', CUBDIR, LUTS] + todo,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1500:])
        print(r.stderr[-2000:])
        raise SystemExit('分解失败：cube 格式对不对？（只支持 3D LUT、DOMAIN 0..1）')
    print('分解 %d 支 cube → assets/luts/*.LTC' % len(todo))


def build_icons(rows, force):
    try:
        import make_icon
    except ImportError as e:
        print('跳过图标生成（需要 numpy + Pillow）：%s' % e)
        return
    items = [('OFF', 'OFF', None)] + [(r['stem'], r['label'] or r['stem'], None) for r in rows]
    made = 0
    for stem, label, _ in items:
        itemid = 'lut-' + stem.lower()
        out = os.path.join(ICONS, itemid + '.png')
        if not force and os.path.isfile(out):
            continue
        if stem == 'OFF':
            src = None
        elif os.path.isfile(cube_of(stem)):
            src = cube_of(stem)
        else:
            src = ltc_of(stem)
        make_icon.make(stem, label, src, out=out)
        made += 1
    print('图标：新生成 %d 张（其余沿用现有；要重做就加 --force）' % made)


def prune(rows):
    keep_ltc = {r['stem'] + '.LTC' for r in rows}
    keep_png = {OFF_ICON} | {'lut-%s.png' % r['stem'].lower() for r in rows}
    for d, keep, ext in ((LUTS, keep_ltc, '.LTC'), (ICONS, keep_png, '.png')):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(ext) and f not in keep:
                os.remove(os.path.join(d, f))
                print('清掉清单外的陈旧件:', os.path.relpath(os.path.join(d, f), ROOT))


def main():
    force = '--force' in sys.argv
    rows = lutset.rows()
    build_ltc(rows, force)
    build_icons(rows, force)
    prune(rows)
    n_l = len([f for f in os.listdir(LUTS) if f.endswith('.LTC')]) if os.path.isdir(LUTS) else 0
    n_i = len([f for f in os.listdir(ICONS) if f.endswith('.png')]) if os.path.isdir(ICONS) else 0
    print('素材就绪：.LTC %d 个（应 %d）｜图标 %d 张（应 %d）'
          % (n_l, len(rows), n_i, len(rows) + 1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
