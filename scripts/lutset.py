"""LUT 清单的唯一真源读取：`assets/lutset.csv` → 有序的行。"""
import csv
import io
import os
import re
import sys

from paths import ROOT

CSV_FILE = os.environ.get('OCLUT_LUTSET') or os.path.join(ROOT, 'assets', 'lutset.csv')

REQUIRED = ('name', 'desc')
OPTIONAL = ('label',)

COLUMNS = ('name', 'label', 'desc')
assert set(COLUMNS) == set(REQUIRED + OPTIONAL)

STEM_STRIP = re.compile(r'[^0-9A-Za-z]')

NAME_WARN_CHARS = 16

LABEL_WARN_FULLWIDTH = 8

_CACHE = []

class LutsetError(SystemExit):
    """清单本身有问题 —— 直接终止（带可读原因），不做静默降级。"""

def _clean_lines(path):
    """读 CSV，丢掉 `#` 注释行与空行（csv 模块不认识注释）。"""
    if not os.path.isfile(path):
        raise LutsetError(
            '找不到 LUT 清单: %s\n'
            '清单是一份 CSV（必填列 name/desc）；\n'
            '可以用 `./build.sh --init <cube目录>` 从现成的 .cube 生成骨架。'
            % path)
    out = []
    with io.open(path, encoding='utf-8-sig') as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith('#'):
                continue
            out.append(ln.rstrip('\n').rstrip('\r'))
    return out

def _width(s):
    """近似视觉宽度：全角字符算 1，半角算 0.5。"""
    return sum(1.0 if ord(c) > 0x2000 else 0.5 for c in s)

def stem_of(name):
    """名字 → 词干（内部 id 与资产文件名）：去掉非字母数字后大写。"""
    return STEM_STRIP.sub('', name).upper()

def rows():
    """解析并校验清单，返回有序的行（dict）列表。结果缓存，重复调用零成本。"""
    if _CACHE:
        return _CACHE
    lines = _clean_lines(CSV_FILE)
    if not lines:
        raise LutsetError('清单是空的: %s' % CSV_FILE)

    rd = csv.DictReader(io.StringIO('\n'.join(lines)))
    cols = [c.strip() for c in (rd.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in cols]
    unknown = [c for c in cols if c not in COLUMNS]
    if 'stem' in cols:
        raise LutsetError(
            '清单里不需要 stem 列 —— id 由 name 推导（去掉非字母数字后大写）。\n'
            '例：name = `Portra 400` → id = PORTRA400（菜单 lut-portra400、\n'
            '资产 assets/cub/PORTRA400.CUB）。把表头与每行的 stem 那列删掉即可。')
    if 'source' in cols:
        raise LutsetError(
            '清单里不需要 source 列 —— cube 一律从 assets/cub/<name 推导出的 id>.CUB 取。\n'
            '把 .cube 放到那个文件名下（`./build.sh --init <目录>` 可自动摆好），'
            '然后删掉表头与每行的 source 那列。')
    if missing or unknown:
        raise LutsetError(
            '清单表头不对: %s\n  缺列: %s\n  未知列: %s\n  可用列: %s'
            % (CSV_FILE, ', '.join(missing) or '（无）',
               ', '.join(unknown) or '（无）', ', '.join(COLUMNS)))

    seen = {}
    out = []
    for n, raw in enumerate(rd, 1):

        r = dict((k, (raw.get(k) or '').strip()) for k in COLUMNS)
        name = r['name']
        where = '清单第 %d 行' % (n + 1)
        if not name:
            raise LutsetError('%s: name 不能为空' % where)
        stem = stem_of(name)
        if len(stem) < 2 or not re.search(r'[A-Z]', stem):
            raise LutsetError(
                '%s: name = %r 里取不出可用的 id（去掉非字母数字后是 %r）。\n'
                'name 会同时用作内部 id 与资产文件名：菜单 id = lut-<小写>，\n'
                'cube/LTC/图标 = assets/cub/<ID>.CUB / assets/luts/<ID>.LTC / icons/<id>.png。\n'
                '可行的改法：\n'
                '  ① name 里带一段 ASCII 字母，如 `Portra 400`（→ id PORTRA400）；\n'
                '  ② 纯中文名放 label 列，name 仍用英文；\n'
                '  ③ 把 assets/cub 里的 cube 命名成 `PORTRA400.CUB`，name 写 `Portra 400`。'
                % (where, name, stem))
        where = '%s（name=%s）' % (where, name)
        if stem != name.upper():

            print('ℹ️  %s: id = %s（菜单里显示的名字用 name，资产文件名用这个 id）'
                  % (where, stem), file=sys.stderr)
        if stem in seen:
            raise LutsetError(
                '%s: 与前面的 %r 推出来同一个 id %s —— 名字需要互不冲突'
                % (where, seen[stem], stem))
        seen[stem] = name

        desc = r['desc']
        if not desc:
            raise LutsetError('%s: desc（简介）不能为空' % where)
        label = r['label'] or name
        if len(name) > NAME_WARN_CHARS:
            print('⚠️  %s: 显示名较长（>%d 字符），列表行可能被截断'
                  % (where, NAME_WARN_CHARS), file=sys.stderr)
        if _width(label) > LABEL_WARN_FULLWIDTH:
            print('⚠️  %s: 图标短名 %r 较宽（>%d 个全角字），图标会自动缩字号'
                  % (where, label, LABEL_WARN_FULLWIDTH), file=sys.stderr)

        out.append({'name': name, 'label': label, 'desc': desc,
                    'stem': stem, 'id': 'lut-' + stem.lower()})
    assert out, '清单里一支 LUT 都没有: %s' % CSV_FILE
    assert len(out) < 400, '清单 %d 支 —— 菜单项上限约 100，请先确认' % len(out)
    _CACHE.extend(out)
    return _CACHE

def stems():
    """按清单顺序返回词干列表（由 `name` 推导；= 菜单 id 与资产文件名用的那截）。"""
    return [r['stem'] for r in rows()]

def names():
    """stem → 菜单/预览页显示名。"""
    return dict((r['stem'], r['name']) for r in rows())

def labels():
    """stem → 图标下方那行短名。"""
    return dict((r['stem'], r['label']) for r in rows())

def descs():
    """stem → 预览页小字说明。"""
    return dict((r['stem'], r['desc']) for r in rows())

def ids():
    """菜单项 id 全集（含 OFF），顺序 = 菜单顺序。"""
    return ['lut-off'] + [r['id'] for r in rows()]

CSV_HEADER = u"""# LUT 清单（唯一真源）：一行一支 LUT，**行顺序 = 菜单顺序**。
#
# 必填列：name / desc
#   name —— LUT 的名字。菜单与预览页显示的就是它；**并同时决定内部 id 与资产文件名**：
#           取「去掉非字母数字后大写」，例如 `Portra 400` → PORTRA400
#           ⇒ 菜单 id = lut-portra400，cube/LTC = assets/cub/PORTRA400.CUB、
#             assets/luts/PORTRA400.LTC，图标 = assets/icons/lut-portra400.png
#           （所以名字里要有一段 ASCII 字母；纯中文名请放 label/desc）
#   desc —— 预览页当前项名下的小字说明（写一句「厂商 + 胶片名 + 风格」最好）
# 可选列（整列删掉也行，默认取 name）：
#   label  —— 图标下方那行的中文短名（建议 ≤7 个全角字）
#
# LUT 文件放 assets/cub/<id>.CUB（id 就是上面推导出来的那截，全大写）。
# 收一支自己的 .cube：python3 scripts/import_cube.py 你的.cube --name "名字"
# （它会分解成 assets/luts/<id>.LTC、生成图标，并往这份清单追加一行）
# 增删一支：改这份清单 + 放好/删掉对应的 .LTC（与图标），然后跑 ./build.sh
"""

def write_csv(path, rs):
    """按规范表头写回清单（列顺序固定 name,label,desc）。"""
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(CSV_HEADER)
        w = csv.writer(f)
        w.writerow(list(COLUMNS))
        for r in rs:
            w.writerow([r.get(k, '') for k in COLUMNS])
    print('已写出 %s：%d 支' % (path, len(rs)))

def main():
    rs = rows()
    print('清单: %s' % CSV_FILE)
    print('LUT: %d 支  菜单: %d 项（OFF + %d）' % (len(rs), len(rs) + 1, len(rs)))
    for r in rs[:3] + rs[-2:]:
        print('  %-12s %-12s %s' % (r['id'], r['name'], r['desc'][:26] + '…'))
    print('校验通过 ✓')
    return 0

if __name__ == '__main__':
    sys.exit(main())
