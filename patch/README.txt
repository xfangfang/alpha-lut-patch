补丁说明
========

01-smali.diff 是对原版「镜头补偿」应用做的**应用侧改动**（含我们注入的桥接层）。
它只含 smali，一共 13 个文件：10 个原有文件被改 + 3 个新增文件。

**LUT菜单（OFF + N 支 LUT）不在补丁里** —— 那份清单由 `scripts/make_slots.py`
按 `assets/lutset.csv` 现生成，所以你增删LUT、换名字都不需要碰这份补丁，也不需要 Java 编译器。

基线（必须是这一版，否则补丁套不上）
------------------------------------
  包名      com.sony.imaging.app.manuallenscompensation
  版本      v2.40
  sha256    2c5a4d6dae5dff9cb342e8d04e2dd90fff702f4e5814510dd754bdd41bd29d22

先确认你手上的原版 APK 是这一份：

  shasum -a 256 assets/<你的原版>.apk

怎么生成的
----------
  （apktool 不随仓库提供，先自行下载到 tools/，见 README_ZH.md「准备」）
  1. apktool 2.10 展开原版：`java -jar tools/apktool.jar d -f -r <原版>.apk -o a`
  2. 另取一份同样的展开树，做完应用侧改动（改 smali、加入桥接层）得到 b
  3. `diff -ruN a/smali b/smali`（已排除 LutManifest.smali —— 那个由脚本生成）

  note：`-r` = 不重编资源表，所以只动 smali；res/ 与清单原样。

怎么套用
--------
在**展开后的树根目录**下套（`-p1` 去掉 diff 里的 a/ b/ 前缀）：

  git apply -p1 --whitespace=nowarn patch/01-smali.diff    # 有 git 时优先
  patch  -p1 -s --no-backup-if-mismatch < patch/01-smali.diff

`scripts/apply_patch.py` 就是干这件事的（两个都试，谁通用谁），套完会检查桥接层在不在。

改动清单
--------
改动原有的（10 个）：

  base/common/ExitScreenState.smali                  退出确认页 → 释放伽马表
  base/common/ForceExitScreenState.smali             强制退出页 → 同上
  base/menu/BaseMenuService.smali                    菜单文案 / 当前值 / 合法性放行
  base/menu/layout/BaseMenuAdapter.smali             LUT 列表项的图标
  base/menu/layout/SpecialScreenMenuLayout.smali     预览页项名下那行小字 + 放开行数
  base/shooting/camera/PictureEffectController.smali 拦截 setValue、包装支持列表、相机就绪/移除
  base/shooting/trigger/custom/NormalFunctionTable.smali  自定义键那条记录重定向到照片效果
  fw/AppRoot.smali                                   关停入口 → 释放伽马表
  fw/CustomKeyMgr.smali                              自定义键（左键）一律进 LUT 列表
  manuallenscompensation/OpticalCompensation.smali   预热 + 回到前台重建

新增（桥接层，编译产物形态）：

  sonylut/bridge/LutBridge.smali      钩子实现：载入 LTC、写伽马表与色彩矩阵、菜单文案、图标
  sonylut/bridge/LutBridge$1.smali    上面那个类里的一处内部类
  sonylut/bridge/LutParams.smali      伽马 + 矩阵的数据结构与读写

由脚本生成、不在补丁里的：

  sonylut/bridge/LutManifest.smali   LUT清单（IDS/STEMS/NAMES/DESC 四个数组）
  assets/MenuData.xml                菜单支项（OFF + N 支）
