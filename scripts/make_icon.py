"""给一支 LUT 画菜单图标（胶片条：齿孔 + 底图套该 LUT + 中文短名）。

    python3 scripts/make_icon.py --stem MYFILM --label 我的片子 [--cube x.CUB | --ltc x.LTC]

图标按 **上屏尺寸 138×58** 设计，写盘时横向压 3/4 存成 104×58
（a5100 屏幕 16:9 而帧缓冲 640×480，上屏会横向放大 4/3）。
没给 --cube/--ltc 时按 assets/cub/<STEM>.CUB、assets/luts/<STEM>.LTC 顺序找。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import lutlib
from paths import CUBDIR, ICONS, ROOT

SRC = os.path.join(ROOT, 'assets', 'icon.jpg')

FONT_CANDIDATES = (
    ('/System/Library/Fonts/PingFang.ttc', 4),
    ('/System/Library/Fonts/Hiragino Sans GB.ttc', 0),
    ('/System/Library/Fonts/STHeiti Medium.ttc', 0),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 0),
    ('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 0),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 0),
)

PW, PH = 138, 58
BAR = 14
CW = PW - 2 * BAR
RADIUS = 7
SS = 4
HOLES = 5
HOLE_W, HOLE_H = 8, 6
FILM_BG = (26, 26, 31)
HOLE_FG = (178, 178, 188)
TEXT_FG = (238, 238, 244, 255)
MAX_FONT = 10
PANEL_STRETCH = 4.0 / 3.0
FB_W = int(round(PW * (1.0 / PANEL_STRETCH)))


def _font_path(size):
    for path, idx in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except OSError:
                continue
    raise SystemExit('找不到中文字体（可在 make_icon.py 的 FONT_CANDIDATES 里补一个）')


def _fit(draw, text, max_w):
    size = MAX_FONT
    while size > 6:
        f = _font_path(size)
        b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] <= max_w:
            return f, b
        size -= 1
    f = _font_path(6)
    return f, draw.textbbox((0, 0), text, font=f)


def _mask(w, h, radius):
    m = Image.new('L', (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1],
                                        radius=radius * SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def _photo():
    im = Image.open(SRC).convert('RGB')
    return np.asarray(im.resize((CW * SS, PH * SS), Image.LANCZOS),
                      dtype=np.float64) / 255.0


def _blue_rows(arr, lo=0.55):
    h = arr.shape[0]
    blue = arr[:, :, 2] - (arr[:, :, 0] + arr[:, :, 1]) / 2.0
    row = blue.mean(axis=1)
    start = int(h * lo)
    thr = max(6.0, row[start:].max() * 0.45)
    ys = [y for y in range(start, h) if row[y] >= thr]
    if len(ys) < 4:
        return max(0, h - 10), h - 1
    return ys[0], ys[-1]


def find_source(stem, cube=None, ltc=None):
    if cube:
        return cube
    if ltc:
        return ltc
    for p in (os.path.join(CUBDIR, stem + '.CUB'), os.path.join(ROOT, 'assets', 'luts', stem + '.LTC')):
        if os.path.isfile(p):
            return p
    raise SystemExit('找不到 %s 的 cube 或 LTC（用 --cube/--ltc 指定）' % stem)


def apply_lut(path, photo):
    if path is None:
        return photo
    if path.upper().endswith('.CUB'):
        return lutlib.apply_cube(path, photo)
    lut = lutlib.Lut.from_ltc(path)
    h, w, _ = photo.shape
    flat = photo.reshape(-1, 3)
    return lut.apply_u8((flat * 255.0).round().astype(np.uint8), matrix_first=True).reshape(h, w, 3) / 255.0


def make(stem, label, path, out=None):
    photo = _photo()
    ref = np.asarray(Image.fromarray((photo * 255).round().astype(np.uint8))
                     .resize((CW, PH), Image.LANCZOS)).astype(np.float64) / 255.0
    lab_top, lab_bot = _blue_rows(ref)

    o = apply_lut(path, photo)
    band = Image.fromarray((o * 255).round().astype(np.uint8)).resize((CW, PH), Image.LANCZOS)

    ic = Image.new('RGB', (PW, PH), FILM_BG)
    d = ImageDraw.Draw(ic)
    gap = (PH - HOLES * HOLE_H) / float(HOLES + 1)
    for k in range(HOLES):
        y = gap + k * (HOLE_H + gap)
        for x0 in (2, PW - 2 - HOLE_W):
            d.rounded_rectangle([x0, y, x0 + HOLE_W - 1, y + HOLE_H - 1],
                                radius=2, fill=HOLE_FG)
    ic.paste(band, (BAR, 0))

    font, bbox = _fit(d, label, CW - 4)
    tw = bbox[2] - bbox[0]
    d.text((BAR + (CW - tw) / 2.0 - bbox[0], max(0.0, (lab_bot + 1) - bbox[3])),
           label, font=font, fill=TEXT_FG)

    ic = ic.convert('RGBA')
    ic.putalpha(_mask(PW, PH, RADIUS))
    os.makedirs(ICONS, exist_ok=True)
    out = out or os.path.join(ICONS, 'lut-%s.png' % stem.lower())
    ic.resize((FB_W, PH), Image.LANCZOS).save(out)
    print('图标 -> %s（上屏 %dx%d / 写盘 %dx%d）'
          % (os.path.relpath(out, ROOT), PW, PH, FB_W, PH))
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split('\n')[0])
    ap.add_argument('--stem', required=True, help='支位 id = 大写词干（图标名 = lut-<小写>.png）')
    ap.add_argument('--label', help='图标上那行中文短名（默认用 stem）')
    ap.add_argument('--cube')
    ap.add_argument('--ltc')
    a = ap.parse_args()
    make(a.stem.upper(), a.label or a.stem.upper(), find_source(a.stem.upper(), a.cube, a.ltc))
    return 0


if __name__ == '__main__':
    sys.exit(main())
