"""把 assets/lutset.csv 变成机器能读的东西：生成 LutManifest.smali 与菜单支项。

清单是唯一真源（列 name,label,desc，行顺序 = 菜单顺序；id 由 name 去掉非字母数字后大写）。
本脚本在**套完补丁的展开树**上工作：

  work/apktool_out/smali/com/sonylut/bridge/LutManifest.smali   ← 重新生成（四个字符串数组）
  work/apktool_out/assets/MenuData.xml                          ← 重新生成 PictureEffect 父块的支项

两者都是纯文本，所以增删支位不需要 Java 编译器：改 assets/lutset.csv 再跑一次就行。
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lutset
from paths import LUTS, TREE, WORK

XML = os.path.join(TREE, 'assets', 'MenuData.xml')
MANIFEST = os.path.join(TREE, 'smali', 'com', 'sonylut', 'bridge', 'LutManifest.smali')

PARENT_KEY = 'CAUTION_GRP_ID_PICTURE_EFFECT_INVALID_GUIDE'
SEL_ICON = ('android:drawable/p_16_dd_parts_fn_1_5_layer_sel_pictureeffect_'
            'high_contrast_monochrome')


def _esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def _array(out, field, vals):
    out.append('    const/16 v0, 0x%x\n\n' % len(vals))
    out.append('    new-array v0, v0, [Ljava/lang/String;\n\n')
    for i, v in enumerate(vals):
        out.append('    const/16 v1, 0x%x\n\n' % i)
        out.append('    const-string v2, "%s"\n\n' % _esc(v))
        out.append('    aput-object v2, v0, v1\n\n')
    out.append('    sput-object v0, Lcom/sonylut/bridge/LutManifest;->'
               '%s:[Ljava/lang/String;\n\n' % field)


def manifest(rows):
    ids = ['lut-off'] + [r['id'] for r in rows]
    out = ['.class public final Lcom/sonylut/bridge/LutManifest;\n',
           '.super Ljava/lang/Object;\n',
           '.source "LutManifest.java"\n\n\n',
           '# static fields\n']
    for f in ('DESC', 'IDS', 'NAMES', 'STEMS'):
        out.append('.field public static final %s:[Ljava/lang/String;\n\n' % f)
    out.append('\n# direct methods\n')
    out.append('.method static constructor <clinit>()V\n')
    out.append('    .locals 3\n\n')
    _array(out, 'IDS', ids)
    _array(out, 'STEMS', [r['stem'] for r in rows])
    _array(out, 'NAMES', [r['name'] for r in rows])
    _array(out, 'DESC', [r['desc'] for r in rows])
    out.append('    return-void\n')
    out.append('.end method\n')
    return ''.join(out)


def item_xml(iid, value, n):
    icon = 'android:drawable/p_picteffect_n_%03d' % (1 + (n % 5))
    return ('            <Layer2\n'
            '                CautionID="0"\n'
            '                ConfigClass="com.sony.imaging.app.base.shooting.camera.PictureEffectController"\n'
            '                ExecType="SET_VALUE"\n'
            '                GuideRes="lutstr/%s"\n'
            '                IconRes="%s"\n'
            '                ItemId="%s"\n'
            '                NextMenuID=""\n'
            '                SelectedIconRes="%s"\n'
            '                TextRes="lutstr/%s"\n'
            '                Value="%s" />\n' % (iid, icon, iid, SEL_ICON, iid, value))


def block_span(text, marker):
    """包含 marker 的那个 `<Layer1 ...>...</Layer1>` 的 (start, end) 半开区间。"""
    i = text.index(marker)
    start = text.rindex('<Layer1', 0, i)
    depth = 0
    for m in re.finditer(r'<Layer1\b|</Layer1>', text[start:]):
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                return start, start + m.end()
        else:
            depth += 1
    raise ValueError('unbalanced Layer1')


def parent_spans(s):
    out = []
    for m in re.finditer(PARENT_KEY, s):
        head = s.rfind('<Layer1', 0, m.start())
        start = s.index('<Layer2', m.start())
        end = s.index('</Layer1>', start)
        pid = re.search(r'ItemId="([^"]+)"', s[head:s.index('>', m.start())])
        out.append((start, end, pid.group(1) if pid else '?'))
    return out


def check_assets(rows):
    """每个支位都要有 LTC，图标建议有（缺了菜单里那行会没图标）。"""
    bad = []
    for r in rows:
        if not os.path.isfile(os.path.join(LUTS, r['stem'] + '.LTC')):
            bad.append('缺 assets/luts/%s.LTC（应由 scripts/make_assets.py 从 assets/cub/%s.CUB 分解出来）'
                       % (r['stem'], r['stem']))
    if bad:
        raise SystemExit('\n'.join(bad))


def main():
    if not os.path.isfile(XML):
        raise SystemExit('先跑 build.sh（或 decompile_apk.py + apply_patch.py）：没有 %s' % XML)
    rows = lutset.rows()
    check_assets(rows)

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    open(MANIFEST, 'w', encoding='utf-8').write(manifest(rows))
    print('LutManifest.smali: %d 支位（菜单 %d 项）' % (len(rows), len(rows) + 1))

    s = open(XML, encoding='utf-8').read()
    bak = os.path.join(WORK, 'backup')
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(XML, os.path.join(bak, 'MenuData.xml.bak_manifest'))

    if 'CreativeStyle' in s:
        start, end = block_span(s, 'CreativeStyle')
        s = s[:start] + s[end:]
        print('MenuData.xml: 已移除「创意风格」入口（只留「照片效果」= LUT 列表）')
    assert 'CreativeStyle' not in s

    spans = parent_spans(s)
    if not spans:
        raise SystemExit('MenuData.xml 里找不到 PictureEffect 父块（%s）' % PARENT_KEY)
    ids = lutset.ids()
    body = ''.join(item_xml(iid, 'off' if iid == 'lut-off' else iid, n)
                   for n, iid in enumerate(ids))
    for start, end, pid in reversed(spans):
        s = s[:start] + body + s[end:]
        print('MenuData.xml: 父块 %s → %d 项' % (pid, len(ids)))
    open(XML, 'w', encoding='utf-8').write(s)

    chk = open(XML, encoding='utf-8').read()
    for start, end, pid in parent_spans(chk):
        blk = chk[start:end]
        found = re.findall(r'ItemId="(lut-[a-z0-9]+)"', blk)
        assert found == ids, '父块 %s 的 id 顺序不符：%s' % (pid, found)
    print('自检通过：菜单 %d 项（OFF + %d LUT）' % (len(ids), len(rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
