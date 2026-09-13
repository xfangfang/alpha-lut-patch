[English](README.md) | [中文](README_ZH.md)

# 镜头补偿 LUT 版

给索尼相机「镜头补偿」应用（`com.sony.imaging.app.manuallenscompensation` v2.40）
装上 LUT 列表的一套 **补丁 + 打包工具**

- 系统：Android 2.3.7（API 10），Sony ScalarA 平台
- 个人自用改造，**请勿公开分发**；原作版权归 Sony，素材来源与许可见文末「致谢」
- 本包**不含**成品 APK，也**不含**应用源码：改动以补丁形式给出

## 相比原版做了什么

1. **内置 LUT**：柯达 / 富士 / 宝丽来... 
   全部打包在 APK 里，不占 SD 卡、不需要联网。

2. **颜色更准**：`.cube` 按机身真实管线顺序拟合。
   相比于同类项目假设引擎是「先逐通道曲线、后矩阵」，而 a5100 实拍反推是「先矩阵、后伽马」；
   按后者拟合，暗部和高光的偏差明显更小。

3. **速度更快**：分解在构建期完成，机内只读 4 KB 参数（1024 点伽马 + 3×3 矩阵）。
   切换 LUT 实测 40-50 ms，且切换时不重新绑定伽马表，取景画面不闪。
   同类项目在机内分解，并重建伽玛表，每次切换要 1~3 秒。

4. **左键直达**：取景时按左键直接进入 LUT 选择页，右侧实时预览当前项效果，边看边换。
   需要在相机的自定义键设置里把左键分配给「创意风格」或「照片效果」。

## 适用设备

在 **a5100** 上调试并验证。同为 16:9 屏幕的索尼 E 卡口机型理论上可用：
a5000、a5100、a6000、a6300、a6500 等。**NEX 系列不支持。**

4:3 屏幕的机型安装后可能图标比例存在问题。

LUT 走机身的伽马表与 3×3 色彩矩阵，补丁与分解器都按 a5100 实拍校准的顺序做的；
换机型后观感可能与预期有出入，请自行测试。

## 准备

| 组件 | 版本 | 用途 |
|---|---|---|
| 原版 APK | v2.40 | 必填。见下方「怎么拿到」，**必须与补丁同一版**，否则补丁套不上 |
| JDK | 8+（实测 21） | apktool、签名、以及分解 `.cube` |
| Python | 3.8+ | 跑 `build.sh`；**画图标**时另需 `numpy` + `Pillow` |
| apktool | 2.10 | **自行下载**到 `tools/apktool.jar`（见下方「怎么拿到外部工具」） |
| uber-apk-signer | 1.3.0 | **自行下载**到 `tools/uber-apk-signer.jar`（同上） |
| adb | 系统自带即可 | 装机 |


**怎么拿到原版 APK**：从相机里拉出厂自带的那份（相机菜单里先打开 adb 服务）。

```bash
adb connect <相机IP>:5555
adb shell pm path com.sony.imaging.app.manuallenscompensation
adb pull <上一步输出的路径> assets/            # 例如 ……/base.apk
```

判别是不是原版看签名：原版由索尼平台密钥签名（包内是 `META-INF/PMCA_KEY.*`），
改装版是本机 debug 签名（`META-INF/ANDROIDD.*`）。
⚠️ 装过改装版之后，相机上那份就被覆盖了 —— 第一次动手前先拉一份留底，它也是你「恢复原状」的底本。

补丁对应的原版 APK 的 sha256 记在 `patch/README.txt` 里，先比对一下再往下走。

**怎么拿到外部工具**：apktool 与 uber-apk-signer 这两个 jar 体积大（24 MB + 3 MB）、
各自有发布页，所以**不随仓库提供**（`tools/` 里只有本工程自己编译的 `lutbuild.jar`）。
clone 下来后自己下载一份放进 `tools/`：

```bash
mkdir -p tools
curl -fL -o tools/apktool.jar \
  https://github.com/iBotPeaches/Apktool/releases/download/v2.10.0/apktool_2.10.0.jar
curl -fL -o tools/uber-apk-signer.jar \
  https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar
```

文件名要正好是 `tools/apktool.jar` 与 `tools/uber-apk-signer.jar`（脚本按名字找），
版本按上表（apktool 2.10 / uber-apk-signer 1.3.0）—— 补丁的 `-r` 展开树与签名都是按这两版做的，
换别的版本可能套不上补丁或签不出相机认的包。缺哪一个，`./build.sh --check` 都会直接点出来。

下完可以核一下（本工程构建用的就是这两份，sha256 逐位相同）：

```bash
shasum -a 256 tools/apktool.jar tools/uber-apk-signer.jar
# c0350abbab5314248dfe2ee0c907def4edd14f6faef1f5d372d3d4abd28f0431  tools/apktool.jar
# e1299fd6fcf4da527dd53735b56127e8ea922a321128123b9c32d619bba1d835  tools/uber-apk-signer.jar
```

## 构建

```bash
./build.sh --check              # 体检：原版 APK / 工具 / 清单与 cube 齐不齐
./build.sh                      # 展开原版 → 套补丁 → 生成支位 → 分解/画图标 → 打包签名 → dist/
./build.sh --apk <原版.apk>      # 不想把原版放进 assets/ 时用这个
./build.sh --force-assets       # .LTC 与图标全部重做（默认只补缺的）
```

五步各是一个独立脚本，想单独跑也行：

```bash
python3 scripts/decompile_apk.py   # apktool d -f -r → work/apktool_out
python3 scripts/apply_patch.py     # 套 patch/01-smali.diff（应用侧 smali 改动 + 桥接层）
python3 scripts/make_assets.py     # assets/cub/*.CUB → assets/luts/*.LTC，并画菜单图标
python3 scripts/make_slots.py      # 按 assets/lutset.csv 生成 LutManifest.smali 与菜单支项
python3 scripts/repack.py          # 装素材 → apktool b -r → 签名 → dist/
```

产物在 `dist/OpticalCompensation_LUT<菜单项数>s-aligned-debugSigned.apk`
（数字 = `OFF + 支位数`，加减 LUT 会跟着变），sha256 写在 `dist/SHA256SUMS.txt`。

打包自检会检查：每个支位都有 `.LTC`（图标缺了会提醒）、dex 里有每个支位的 stem、
zip 无重名条目、没有备份文件混入、菜单里没有多余的「创意风格」入口。
任何一条不过就直接失败，不会产出半成品。

## 用自己的 .cube

```bash
python3 scripts/import_cube.py ~/Downloads/我的片子.cube --name "FILMID" \
        --label 我的滤镜 --desc "一句话说明"
./build.sh
```

它会：把 cube 拷进 `assets/cub/FILMID.CUB`、往 `assets/lutset.csv` 追加一行；
`./build.sh` 再把它分解成 `assets/luts/FILMID.LTC`（机内只认这个格式）、
画一张菜单图标 `assets/icons/lut-filmid.png`，并生成菜单项。

- `--name` 同时决定内部 id 与文件名（取「去掉非字母数字后大写」），所以里面要有一段 ASCII 字母。
- `.cube` 用 3D LUT、`DOMAIN 0..1`；**别用 LOG 套色**（LogC / C-Log / S-Log / V-Log 之类），
  那种是转换用 LUT，作用在显示参考图像上会整片发灰。
- 分解在电脑上做（每支几秒），机内只读 4 KB 结果。

## 换滤镜

- **换某一支的滤镜**：把 `assets/cub/<STEM>.CUB` 换成你的 cube（保持文件名），删掉
  `assets/luts/<STEM>.LTC`，再 `./build.sh`（缺的那支会重新分解）。
- **调顺序**：编辑 `assets/lutset.csv`（**行顺序 = 菜单顺序**）；删支位就连同
  `assets/cub/<STEM>.CUB` 一起删（旧的 `.LTC`/图标会被自动清掉），然后 `./build.sh`。
- 支位与菜单名都由清单现生成，不需要重编什么 Java。

## 安装与还原

```bash
adb connect <相机IP>:5555
adb install -r dist/OpticalCompensation_LUT53s-aligned-debugSigned.apk
# 输出里必须看到 Success（只停在 Performing Push Install 就是没装成，测的还是旧包）

# 不想用了，装回你留底的那份原版：
adb install -r <你留底的原版.apk>
```

相机上的 adb 只能 `logcat -d` 和 `install -r`；不要 `pm disable`、`force-stop`、杀进程。

使用：MENU → 照片效果 → 选 LUT（光标停留时右侧就是该项的实时预览）；选 `OFF` 关闭。
取景时按左键也能直接进这个列表（需先在相机的自定义键设置里把左键分配给「创意风格」或「照片效果」）。

## 已知限制

- 机内引擎只有「一条共用伽马 + 3×3 矩阵」，表达不了 `.cube` 的逐通道非线性：
  高饱和颜色误差偏大，整体比原 LUT 的设计意图略淡。
- 补丁只对应上面那个 sha256 的原版 APK；别的版本（比如另一版固件）套不上，会明确报错。
- 换机型后观感可能不同（管线顺序按 a5100 实拍校准）。

## 目录

```
build.sh                  一条命令入口
patch/01-smali.diff       应用侧 smali 改动 + 桥接层（来历与套用说明见 patch/README.txt）
tools/apktool.jar         apktool 2.10（自行下载，不入库）
tools/uber-apk-signer.jar 签名（自行下载，不入库）
tools/lutbuild.jar        .cube → .LTC 分解器（构建期用，随仓库提供）
assets/lutset.csv         ★ 真源：一行一支 LUT，行顺序 = 菜单顺序
assets/cub/*.CUB          ★ 真源：各支的 .cube（用 import_cube.py 收进来）
assets/icon.jpg           ★ 真源：画图标用的底图
assets/luts/*.LTC         生成物：机内读的滤镜数据（不入库）
assets/icons/*.png        生成物：菜单图标（不入库）
scripts/                  decompile_apk / apply_patch / make_slots / make_assets / import_cube / make_icon / repack / build_app
work/ dist/               中间产物、产物（都不入库）
```

## 致谢

- 先驱：
  [starshine09074-ui/A6000-LUT](https://github.com/starshine09074-ui/A6000-LUT) 与
  [awerdswww/RX100M3-LUT](https://github.com/awerdswww/RX100M3-LUT)。
- LUT 素材：[YahiaAngelo/Film-Luts](https://github.com/YahiaAngelo/Film-Luts)（MIT）。
- 工具：[apktool](https://ibotpeaches.github.io/Apktool/)、
  [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer)。
- 图标底图素材来源：影视飓风，版权归原作者。
