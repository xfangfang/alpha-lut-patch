"""用 apktool 把原版「镜头补偿」APK 展开到 work/apktool_out（补丁的工作目录）。"""
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import APK_DIR, ROOT, TOOLS, TREE

JAR = os.path.join(TOOLS, 'apktool.jar')


def find_apk(argv):
    if '--apk' in argv:
        return argv[argv.index('--apk') + 1]
    found = sorted(glob.glob(os.path.join(ROOT, 'assets', '*.apk')))
    return found[0] if found else None


def run(apk=None):
    apk = apk or find_apk([])
    if not apk:
        raise SystemExit('assets/ 下没有原版 APK：把原版放进 assets/，或用 --apk <路径> 指定')
    if not os.path.isfile(apk):
        raise SystemExit('APK 不存在: %s' % apk)
    if not os.path.isfile(JAR):
        raise SystemExit('缺 %s（说明见 README_ZH.md「准备」一节）' % JAR)

    os.makedirs(APK_DIR, exist_ok=True)
    if os.path.isdir(TREE):
        shutil.rmtree(TREE)

    print('apktool d -f -r %s' % os.path.relpath(apk, ROOT))
    r = subprocess.run(['java', '-jar', JAR, 'd', '-f', '-r', apk, '-o', TREE],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        raise SystemExit(1)
    if not os.path.isdir(os.path.join(TREE, 'smali')):
        raise SystemExit('展开后没有 smali/ 目录: %s' % TREE)
    print('展开树就绪 -> %s' % os.path.relpath(TREE, ROOT))
    return TREE


def main():
    run(find_apk(sys.argv))


if __name__ == '__main__':
    main()
