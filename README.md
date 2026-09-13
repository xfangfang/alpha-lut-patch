[English](README.md) | [中文](README_ZH.md)

# Lens Compensation LUT Edition

A **patch + repack toolkit** that adds a LUT list to Sony's built-in "Lens Compensation"
app (`com.sony.imaging.app.manuallenscompensation` v2.40).

- System: Android 2.3.7 (API 10), Sony ScalarA platform
- Personal mod, **do not redistribute**; the original app is © Sony — sources and licences are in the Credits section
- This package contains **no ready-made APK** and **no application source code**: the changes are delivered as a patch

## What's different from the stock app

1. **Built-in LUTs**: Kodak / Fujifilm / Polaroid and more —
   all packed inside the APK, no SD card and no network needed.

2. **More accurate colour**: `.cube` files are fitted to the camera's real pipeline order.
   Comparable projects assume the engine is "per-channel curve first, then matrix", while an
   a5100 measures out as "matrix first, then gamma"; fitting to the latter makes the error
   in shadows and highlights noticeably smaller.

3. **Faster switching**: decomposition happens at build time, so the camera only reads
   4 KB of parameters (1024-point gamma + 3×3 matrix). Switching a LUT measures 40–50 ms,
   and the gamma table is not re-bound on switch, so the live view does not flicker.
   Comparable projects decompose on-camera and rebuild the gamma table: 1–3 s per switch.

4. **Left-key shortcut**: while shooting, the left key jumps straight to the LUT list with a
   live preview of the item on the right, so you can compare while you switch.
   Assign the left key to "Creative Style" or "Picture Effect" in the camera's custom-key settings.

## Supported cameras

Developed and verified on the **a5100**. Other Sony E-mount models with a 16:9 screen
should work in theory: a5000, a5100, a6000, a6300, a6500, etc. **NEX series is not supported.**

Models with a 4:3 screen may show icons with the wrong proportions after install.

LUTs are applied through the camera's gamma table and 3×3 colour matrix; both the patch
and the decomposer follow the pipeline order measured on an a5100, so results may differ
on other bodies — please test.

## Requirements

| Component | Version | Purpose |
|---|---|---|
| Stock APK | v2.40 | Required. See "Getting the stock APK" below — it **must be the same version** as the patch, or the patch will not apply |
| JDK | 8+ (21 tested) | apktool, signing, and decomposing `.cube` |
| Python | 3.8+ | Runs `build.sh`; drawing icons additionally needs `numpy` + `Pillow` |
| apktool | 2.10 | **download it yourself** to `tools/apktool.jar` (see "Getting the external tools") |
| uber-apk-signer | 1.3.0 | **download it yourself** to `tools/uber-apk-signer.jar` (same) |
| adb | system one is fine | Installing |

**Getting the stock APK**: pull the factory copy from your camera (enable the adb
service in the camera menu first).

```bash
adb connect <camera-ip>:5555
adb shell pm path com.sony.imaging.app.manuallenscompensation
adb pull <path printed above> assets/            # e.g. ……/base.apk
```

To tell whether it is really the stock build, look at the signature: the stock APK is
signed with Sony's platform key (`META-INF/PMCA_KEY.*` inside), while the modded build is
signed with a local debug key (`META-INF/ANDROIDD.*`).
⚠️ Installing a modded build overwrites the copy on the camera — pull one and keep it
before your first attempt; that backup is also how you restore the original later.

The sha256 of the stock APK the patch expects is recorded in `patch/README.txt` —
check it first.

**Getting the external tools**: the apktool and uber-apk-signer jars are large (24 MB + 3 MB)
and each has its own release page, so they are **not shipped with the repo** (`tools/` only
contains `lutbuild.jar`, which this project compiles itself). After cloning, download them
into `tools/`:

```bash
mkdir -p tools
curl -fL -o tools/apktool.jar \
  https://github.com/iBotPeaches/Apktool/releases/download/v2.10.0/apktool_2.10.0.jar
curl -fL -o tools/uber-apk-signer.jar \
  https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar
```

The file names must be exactly `tools/apktool.jar` and `tools/uber-apk-signer.jar` (the scripts
look them up by name), in the versions from the table above (apktool 2.10 / uber-apk-signer
1.3.0) — the patch's `-r` unpack tree and the signing were both produced with those, so a
different version may fail to apply the patch or produce an APK the camera rejects.
`./build.sh --check` names whichever one is missing.

After downloading you can verify them (these are the exact files this project was built with):

```bash
shasum -a 256 tools/apktool.jar tools/uber-apk-signer.jar
# c0350abbab5314248dfe2ee0c907def4edd14f6faef1f5d372d3d4abd28f0431  tools/apktool.jar
# e1299fd6fcf4da527dd53735b56127e8ea922a321128123b9c32d619bba1d835  tools/uber-apk-signer.jar
```

## Build

```bash
./build.sh --check              # sanity check: stock APK / tools / list & cubes
./build.sh                      # unpack → patch → generate slots → decompose & draw icons → repack & sign → dist/
./build.sh --apk <stock.apk>    # if you don't want to put the stock APK into assets/
./build.sh --force-assets       # redo all .LTC and icons (by default only missing ones are built)
```

The five stages are separate scripts; you can run them one by one:

```bash
python3 scripts/decompile_apk.py   # apktool d -f -r → work/apktool_out
python3 scripts/apply_patch.py     # apply patch/01-smali.diff (app-side smali changes + bridge)
python3 scripts/make_assets.py     # assets/cub/*.CUB → assets/luts/*.LTC, plus menu icons
python3 scripts/make_slots.py      # build LutManifest.smali and menu entries from assets/lutset.csv
python3 scripts/repack.py          # install assets → apktool b -r → sign → dist/
```

The result is `dist/OpticalCompensation_LUT<menu-item-count>s-aligned-debugSigned.apk`
(the number is `OFF + number of LUTs` and changes when you add or remove LUTs), with its
sha256 in `dist/SHA256SUMS.txt`.

The packaging self-check verifies that every slot has a `.LTC` (missing icons only warn),
that every slot's stem is present in the dex, that the zip has no duplicate entries and no
backup files, and that the redundant "Creative Style" menu entry is gone. If any check
fails the build stops — you never get a half-finished APK.

## Using your own .cube

```bash
python3 scripts/import_cube.py ~/Downloads/myfilm.cube --name "FILMID" \
        --label "My Film" --desc "one-line description"
./build.sh
```

It copies the cube to `assets/cub/FILMID.CUB` and appends a row to `assets/lutset.csv`;
`./build.sh` then decomposes it to `assets/luts/FILMID.LTC` (the only format the camera
reads), draws a menu icon `assets/icons/lut-filmid.png`, and generates the menu entry.

- `--name` determines both the internal id and the file names (non-alphanumeric characters
  are stripped and the rest is uppercased), so it must contain some ASCII letters.
- `.cube` must be a 3D LUT with `DOMAIN 0..1`; **do not use log conversion LUTs**
  (LogC / C-Log / S-Log / V-Log and friends) — they are meant to convert log footage and
  will wash the picture out when applied to a display-referred image.
- Decomposition runs on your computer (a few seconds per LUT); the camera only reads the 4 KB result.

## Swapping filters

- **Replace one filter**: drop your cube in as `assets/cub/<STEM>.CUB` (keep the file name),
  delete `assets/luts/<STEM>.LTC`, then run `./build.sh` — the missing one is rebuilt.
- **Change the order**: edit `assets/lutset.csv` (**row order = menu order**); to remove a
  slot, delete `assets/cub/<STEM>.CUB` as well (stale `.LTC`/icons are pruned automatically),
  then run `./build.sh`.
- Slots and menu names are generated from the list on every build; no Java compilation involved.

## Install and restore

```bash
adb connect <camera-ip>:5555
adb install -r dist/OpticalCompensation_LUT53s-aligned-debugSigned.apk
# You must see "Success" (stopping at "Performing Push Install" means it did not install,
# so you would be testing the previous build)

# To go back, install the stock APK you kept:
adb install -r <your-stock-backup.apk>
```

The camera's adb only supports `logcat -d` and `install -r`; do not use `pm disable`,
`force-stop`, or kill processes.

Usage: MENU → Picture Effect → pick a LUT (the item under the cursor is previewed live on
the right); pick `OFF` to turn it off. Pressing the left key while shooting also jumps
straight to this list (assign the left key to "Creative Style" or "Picture Effect" in the
camera's custom-key settings first).

## Known limitations

- The in-camera engine only has "one shared gamma curve + a 3×3 matrix", so it cannot
  express the per-channel non-linearity of a `.cube`: highly saturated colours deviate more,
  and the overall look is flatter than the LUT was designed to be.
- The patch only matches the stock APK with the sha256 above; other versions (e.g. another
  firmware build) will fail to apply, with an explicit error.
- Look may differ on other camera bodies (the pipeline order was calibrated on an a5100).

## Layout

```
build.sh                  single entry point
patch/01-smali.diff       app-side smali changes + bridge layer (provenance and usage: patch/README.txt)
tools/apktool.jar         apktool 2.10 (download it yourself, not tracked)
tools/uber-apk-signer.jar signing (download it yourself, not tracked)
tools/lutbuild.jar        .cube → .LTC decomposer (build-time, built by this project)
assets/lutset.csv         ★ source of truth: one LUT per row, row order = menu order
assets/cub/*.CUB          ★ source of truth: the .cube files (imported with import_cube.py)
assets/icon.jpg           ★ source of truth: base photo for the icons
assets/luts/*.LTC         generated: the filter data the camera reads (not tracked)
assets/icons/*.png        generated: menu icons (not tracked)
scripts/                  decompile_apk / apply_patch / make_slots / make_assets / import_cube / make_icon / repack / build_app
work/ dist/               build tree and output (not tracked)
```

## Credits

- Pioneers:
  [starshine09074-ui/A6000-LUT](https://github.com/starshine09074-ui/A6000-LUT) and
  [awerdswww/RX100M3-LUT](https://github.com/awerdswww/RX100M3-LUT).
- LUT material: [YahiaAngelo/Film-Luts](https://github.com/YahiaAngelo/Film-Luts) (MIT).
- Tools: [apktool](https://ibotpeaches.github.io/Apktool/),
  [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer).
- Icon base photo: provided by the author, sourced from 影视飓风 (Ying Shi Ju Feng); copyright belongs to the original creator.
