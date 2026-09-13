"""把 patch/*.diff 套到展开树上。

补丁相对展开树的根（-p1 去掉 a/ b/ 前缀），所以只用「同一版原版 APK」展开出来的树才能套上；
套不上会直接报错并指出是哪个文件，不会留下半套状态（失败前不会写任何文件）。
优先用 git apply（能识别「新增文件」），没有 git 时退回 patch -p1。
"""
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import PATCHES, TREE

MUST = [
    'smali/com/sonylut/bridge/LutBridge.smali',
    'smali/com/sonylut/bridge/LutParams.smali',
]
# note：LutManifest.smali 不在补丁里 —— 它由 scripts/make_slots.py 按 assets/lutset.csv 现生成


def _try(diff, cwd):
    """按顺序试 git apply / patch；返回 (工具名, 输出)。"""
    cmds = [
        ('git', ['git', 'apply', '-p1', '--whitespace=nowarn', diff]),
        ('patch', ['patch', '-p1', '-s', '--no-backup-if-mismatch', '-i', diff]),
    ]
    last = ''
    for name, cmd in cmds:
        if shutil.which(cmd[0]) is None:
            continue
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if r.returncode == 0:
            return name, (r.stdout + r.stderr).strip()
        last = '%s 失败:\n%s' % (name, (r.stdout + r.stderr).strip())
    raise SystemExit(last or '既没有 git 也没有 patch，无法套补丁')


def run():
    if not os.path.isdir(TREE):
        raise SystemExit('先跑 decompile_apk.py 展开原版 APK')
    diffs = sorted(glob.glob(os.path.join(PATCHES, '*.diff')))
    if not diffs:
        raise SystemExit('patch/ 下没有 *.diff')

    for d in diffs:
        name, out = _try(d, TREE)
        print('用 %-5s 套用 %s ... OK' % (name, os.path.basename(d)))

    miss = [p for p in MUST if not os.path.isfile(os.path.join(TREE, p))]
    if miss:
        raise SystemExit('套完仍缺这些文件（补丁不匹配？原版 APK 版本对不上）: %s' % miss)
    print('补丁全部套用完成')
    return TREE


def main():
    run()


if __name__ == '__main__':
    main()
