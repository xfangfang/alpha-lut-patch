"""一条命令：原版 APK → 展开 → 套补丁 → 生成支位 → 分解 cube/画图标 → 打包签名 → dist/。

    ./build.sh                  全流程
    ./build.sh --apk <原版.apk>  指定原版 APK（默认取 assets/ 下那份）
    ./build.sh --check          只体检：工具与真源齐不齐
    ./build.sh --force-assets   素材（.LTC / 图标）全部重做，不沿用现有的
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apply_patch
import decompile_apk
import lutset
import make_assets
import make_slots
import repack
from paths import CUBDIR, PATCHES, ROOT, TOOLS

# 这两个 jar 不随仓库走（体积大、各有发布页），缺了就把地址打出来让用户自己下
JARS = {
    'apktool.jar':
        'https://github.com/iBotPeaches/Apktool/releases/download/v2.10.0/apktool_2.10.0.jar',
    'uber-apk-signer.jar':
        'https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar',
}


def check(apk):
    bad = []
    for j in JARS:
        if not os.path.isfile(os.path.join(TOOLS, j)):
            bad.append('缺 tools/%s —— 需自行下载（README_ZH.md「准备」一节有现成命令）：\n'
                       '      curl -fL -o tools/%s %s' % (j, j, JARS[j]))
    if shutil.which('java') is None:
        bad.append('找不到 java（apktool / 签名 / 分解 cube 都要用它，装 JDK 8+ 即可）')
    if not shutil.which('git') and not shutil.which('patch'):
        bad.append('套补丁需要 git 或 patch 二者之一')
    diffs = [f for f in os.listdir(PATCHES) if f.endswith('.diff')] if os.path.isdir(PATCHES) else []
    if not diffs:
        bad.append('patch/ 下没有 *.diff')
    if not os.path.isfile(os.path.join(TOOLS, 'lutbuild.jar')):
        bad.append('缺 tools/lutbuild.jar（.cube → .LTC 分解器）')
    if not os.path.isfile(os.path.join(ROOT, 'assets', 'icon.jpg')):
        bad.append('缺 assets/icon.jpg（画菜单图标的底图）')

    rows = []
    try:
        rows = lutset.rows()
    except SystemExit as e:
        bad.append('清单读不了：%s' % e)
    miss = [r['stem'] for r in rows if not os.path.isfile(os.path.join(CUBDIR, r['stem'] + '.CUB'))]
    if miss:
        bad.append('清单里有 %d 支缺 cube：%s%s（用 scripts/import_cube.py 收进来）'
                   % (len(miss), ', '.join(miss[:4]), ' …' if len(miss) > 4 else ''))

    if not decompile_apk.find_apk([] if not apk else ['--apk', apk]):
        bad.append('assets/ 下没有原版 APK —— 从相机里拉出厂自带那份（见 README_ZH.md「准备」）')

    if bad:
        print('体检不通过：')
        for b in bad:
            print('  ✗', b)
        return 1
    print('体检通过：原版 APK、工具、%d 支 cube、补丁 %d 份，都在' % (len(rows), len(diffs)))
    return 0


def main():
    args = sys.argv[1:]
    apk = args[args.index('--apk') + 1] if '--apk' in args else None
    if '--check' in args:
        return check(apk)

    print('=== 1/5  展开原版 APK ===')
    tree = decompile_apk.run(apk)
    print('=== 2/5  套用 patch/*.diff ===')
    apply_patch.run()
    print('=== 3/5  分解 cube → .LTC、画菜单图标 ===')
    sys.argv = [sys.argv[0]] + (['--force'] if '--force-assets' in args else [])
    make_assets.main()
    print('=== 4/5  按 assets/lutset.csv 生成支位 ===')
    make_slots.main()
    print('=== 5/5  装素材 + 打包 + 签名 ===')
    repack.run(tree)
    print('=== 完成 ===')
    return 0


if __name__ == '__main__':
    sys.exit(main())
