#!/bin/bash
# 一条命令：原版「镜头补偿」APK → 改装后的 APK（落在 dist/）。
#
#   ./build.sh                  全流程：展开原版 → 套补丁 → 打包签名 → dist/
#   ./build.sh --apk <原版.apk>  指定原版 APK（默认取 assets/ 下那份）
#   ./build.sh --check          只体检：工具与素材齐不齐
#
# 换滤镜不用改代码：把 assets/luts/<STEM>.LTC（可选 assets/icons/lut-<stem>.png）
# 替换掉，再跑一次 ./build.sh。见 README_ZH.md（英文版 README.md）。
set -e
ROOT="${OCLUT_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
PY="${OCLUT_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "找不到 python3（可用 OCLUT_PYTHON 指定）" >&2; exit 1; }
export OCLUT_ROOT="$ROOT"
exec "$PY" "$ROOT/scripts/build_app.py" "$@"
