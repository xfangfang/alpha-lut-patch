"""把 assets/luts + assets/icons 装进展开树 → apktool b -r → 签名 → dist/，并做最小自检。

自检口径（任何一条不过就直接失败，不产出半成品）：
  · assets/luts/*.LTC 与 assets/icons/*.png 必须与 MenuData 里列出的支位一一对上
    （漏一个 → 机内那支加载失败；多一个 → 没人用得上）
  · dex 里必须有每个支位的 stem（清单是编译进 dex 的，只能换数据、不能改支位）
  · zip 无重名条目、无 .bak 混入
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import APK_DIR, DIST, ICONS, LUTS, ROOT, TOOLS, TREE

APKTOOL = os.path.join(TOOLS, 'apktool.jar')
SIGNER = os.path.join(TOOLS, 'uber-apk-signer.jar')


def slots(tree):
    """从套完补丁的 MenuData 里取支位（有序的 (stem, itemid) 列表）。"""
    md = open(os.path.join(tree, 'assets', 'MenuData.xml'), encoding='utf-8').read()
    m = re.search(r'ItemId="PictureEffect".*?</Layer1>', md, re.S)
    if not m:
        raise SystemExit('MenuData 里找不到 PictureEffect 父块')
    ids = re.findall(r'ItemId="(lut-[a-z0-9]+)"', m.group(0))
    out = []
    for i in ids:
        stem = i[4:]
        if stem == 'off':
            continue
        out.append((stem.upper(), i))
    return out


def pack(tree, slots_):
    os.makedirs(os.path.join(tree, 'assets', 'luts'), exist_ok=True)
    os.makedirs(os.path.join(tree, 'assets', 'icons'), exist_ok=True)
    for src, dst in ((LUTS, os.path.join(tree, 'assets', 'luts')),
                     (ICONS, os.path.join(tree, 'assets', 'icons'))):
        for f in sorted(os.listdir(src)):
            if f.startswith('.'):
                continue
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))

    name = 'OpticalCompensation_LUT%ds' % (len(slots_) + 1)
    os.makedirs(APK_DIR, exist_ok=True)
    raw = os.path.join(APK_DIR, name + '.apk')
    signed = os.path.join(APK_DIR, name + '-aligned-debugSigned.apk')

    r = subprocess.run(['java', '-jar', APKTOOL, 'b', '-r', tree, '-o', raw],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-3000:])
        raise SystemExit('apktool b 失败')
    print('apktool b rc=0 -> %s' % os.path.relpath(raw, ROOT))

    r = subprocess.run(['java', '-jar', SIGNER, '-a', raw], capture_output=True, text=True)
    if not os.path.isfile(signed):
        print(r.stdout[-2000:])
        raise SystemExit('签名产物缺失: %s' % signed)
    print('签名 rc=%d -> %s' % (r.returncode, os.path.relpath(signed, ROOT)))
    return raw, signed, name


def check(signed, slots_):
    z = zipfile.ZipFile(signed)
    names = z.namelist()
    dup = len(names) - len(set(names))
    assert not dup, 'zip 里有 %d 个重名条目' % dup
    stray = [n for n in names if '.bak' in n or n.endswith('.orig')]
    assert not stray, 'zip 里混入了备份文件: %s' % stray

    luts = sorted(n for n in names if n.startswith('assets/luts/'))
    icons = sorted(n for n in names if n.startswith('assets/icons/'))
    assert len(luts) == len(slots_), 'LTC 数 %d != 支位 %d' % (len(luts), len(slots_))
    assert len(icons) == len(slots_) + 1, '图标数 %d != 支位 %d + 1' % (len(icons), len(slots_))

    data = z.read('classes.dex')
    for k in (b'extendAvailable', b'menuCurrentValue', b'iconFor', b'saveApplied',
              b'LutManifest'):
        assert k in data, 'dex 缺少 %s' % k
    for stem, itemid in slots_:
        assert ('assets/luts/%s.LTC' % stem) in luts, '缺 assets/luts/%s.LTC' % stem
        assert ('assets/icons/%s.png' % itemid) in icons, '缺 assets/icons/%s.png' % itemid
        assert stem.encode() in data, 'dex 里没有 %s（清单是编译进 dex 的）' % stem

    md = z.read('assets/MenuData.xml').decode('utf-8')
    assert 'CreativeStyle' not in md, 'MenuData 里还有 CreativeStyle'
    print('自检通过：%d 支位；zip %d 条；dex 探针全中' % (len(slots_), len(names)))
    return len(names)


def publish(raw, signed):
    h = hashlib.sha256(open(signed, 'rb').read()).hexdigest()
    size = os.path.getsize(signed)
    os.makedirs(DIST, exist_ok=True)
    keep = {os.path.basename(raw), os.path.basename(raw) + '.idsig',
            os.path.basename(signed), os.path.basename(signed) + '.idsig'}
    for d in (DIST, APK_DIR):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.startswith('OpticalCompensation_LUT') and f not in keep:
                os.remove(os.path.join(d, f))
                print('清理旧产物:', os.path.relpath(os.path.join(d, f), ROOT))
    dst = os.path.join(DIST, os.path.basename(signed))
    shutil.copy2(signed, dst)
    with open(os.path.join(DIST, 'SHA256SUMS.txt'), 'w') as f:
        f.write('%s  %s\n' % (h, os.path.basename(dst)))
        f.write('# 装机命令: adb -s <camera-ip>:5555 install -r %s\n' % os.path.basename(dst))
    print('size = %d B' % size)
    print('sha256 = %s' % h)
    print('已发布 -> %s' % os.path.relpath(dst, ROOT))
    return dst


def run(tree):
    slots_ = slots(tree)
    print('支位 %d 个（菜单 %d 项）' % (len(slots_), len(slots_) + 1))
    raw, signed, name = pack(tree, slots_)
    check(signed, slots_)
    publish(raw, signed)


def main():
    run(TREE)


if __name__ == '__main__':
    main()
