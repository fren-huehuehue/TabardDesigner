"""Assets for the Character view: the Guild Tabard's in-game torso textures and colour tables.

- img3d/emblems-ingame.webp + emblem-index.json: each emblem's white (colour 14) TorsoUpper + TorsoLower texture,
  rolled by 256 px so the emblem sits whole in the middle, cropped and kept at half size. Entry: [x, y, w, h, x0, y0]
  = crop in the atlas and its top-left in the rolled 512x384 sheet. The index is also written into EMB in index.html.
- img3d/borders-ingame.webp (3x2 grid of the six white borders) and img3d/bg-ingame.webp, as grey + alpha.
- img3d/luts.b64.txt: 85 colour tables (17 emblem, 17 border, 51 background) x 3 channels x 256 values, mapping the
  grey value of the white texture to the in-game coloured texture. Fitted on emblem 6 (+128), border 0 and the
  background; the error is a few levels out of 255.

Run: python build_ingame.py
"""
import base64
import json
import os
import re

import numpy as np
from PIL import Image

from wago import DOCS, file, table

OUT = os.path.join(DOCS, 'img3d')


def rgba(fid):
    return np.array(Image.open(file(fid)).convert('RGBA')).astype(np.float32)


def lum(a):
    return np.clip(a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114, 0, 255)


def grey_image(a):
    L = lum(a)
    return Image.fromarray(np.dstack([L, L, L, a[..., 3]]).astype(np.uint8), 'RGBA')


def fids(rows, **want):
    out = {}
    for r in rows:
        if all(r[k] == str(v) for k, v in want.items()):
            out[(int(r.get('EmblemID', r.get('BorderID', 0)) or 0), int(r['Color']), int(r['Component']))] = r['FileDataID']
    return out


def build_emblems(emb):
    crops = []
    for e in range(196):
        sheet = np.concatenate([np.roll(rgba(emb[(e, 14, 3)]), 256, 1), np.roll(rgba(emb[(e, 14, 4)]), 256, 1)], 0)
        ys, xs = np.where(sheet[..., 3] > 4)
        x0, x1 = int(xs.min()) & ~1, (int(xs.max()) + 2) & ~1
        y0, y1 = int(ys.min()) & ~1, (int(ys.max()) + 2) & ~1
        im = grey_image(sheet[y0:y1, x0:x1]).resize(((x1 - x0) // 2, (y1 - y0) // 2), Image.LANCZOS)
        crops.append((e, x0, y0, im))
    W, x, y, row, place = 2048, 0, 0, 0, {}
    for e, x0, y0, im in sorted(crops, key=lambda t: -t[3].height):  # shelf packing, tallest first
        if x + im.width > W:
            x, y, row = 0, y + row + 2, 0
        place[e] = [x, y, im.width, im.height, x0, y0]
        x += im.width + 2
        row = max(row, im.height)
    atlas = Image.new('RGBA', (W, y + row))
    for e, x0, y0, im in crops:
        atlas.paste(im, tuple(place[e][:2]))
    atlas.save(os.path.join(OUT, 'emblems-ingame.webp'), 'WEBP', quality=88, method=6)
    index = json.dumps([place[e] for e in range(196)], separators=(',', ':'))
    open(os.path.join(OUT, 'emblem-index.json'), 'w').write(index)
    p = os.path.join(DOCS, 'index.html')
    html = open(p, encoding='utf-8').read()
    html, n = re.subn(r'const EMB = \[.*?\];', lambda m: f'const EMB = {index};', html, count=1)
    assert n == 1, 'EMB not found in index.html'
    open(p, 'w', encoding='utf-8').write(html)


def fit_lut(pairs):
    idx = np.arange(256)
    lut = np.zeros((3, 256), np.float64)
    for ch in range(3):
        xs, ys = [], []
        for white, coloured in pairs:
            m = (white[..., 3] > 200) & (coloured[..., 3] > 200)
            xs.append(np.round(lum(white)[m]).astype(int)); ys.append(coloured[..., ch][m])
        x, y = np.concatenate(xs), np.concatenate(ys)
        sums, cnt = np.bincount(x, weights=y, minlength=256), np.bincount(x, minlength=256)
        good = cnt > 8
        g, v = idx[good], (sums / np.maximum(cnt, 1))[good]
        if len(v) > 5:
            v = np.convolve(np.pad(v, 2, mode='edge'), np.ones(5) / 5, 'valid')
        lut[ch] = np.interp(idx, g, v)
        k = min(20, len(g))
        a, b = np.polyfit(g[-k:], v[-k:], 1); lut[ch][g.max():] = a * idx[g.max():] + b
        a, b = np.polyfit(g[:k], v[:k], 1); lut[ch][:g.min()] = a * idx[:g.min()] + b
    return np.clip(np.round(lut), 0, 255).astype(np.uint8)


def build_luts(emb, bor, bgr):
    luts = []
    for c in range(17):
        pairs = [(rgba(emb[(6, 14, 3)]), rgba(emb[(6, c, 3)])), (rgba(emb[(6, 14, 4)]), rgba(emb[(6, c, 4)]))]
        if c in (0, 9, 16):
            pairs.append((rgba(emb[(128, 14, 3)]), rgba(emb[(128, c, 3)])))
        luts.append(fit_lut(pairs))
    for c in range(17):
        luts.append(fit_lut([(rgba(bor[(0, 14, 3)]), rgba(bor[(0, c, 3)])), (rgba(bor[(0, 14, 4)]), rgba(bor[(0, c, 4)]))]))
    for c in range(51):
        luts.append(fit_lut([(rgba(bgr[(0, 49, 3)]), rgba(bgr[(0, c, 3)]))]))
    blob = np.stack(luts).tobytes()
    open(os.path.join(OUT, 'luts.b64.txt'), 'w').write(base64.b64encode(blob).decode())


def build_bases(bor, bgr):
    grid = Image.new('RGBA', (512 * 3, 384 * 2))
    for b in range(6):
        stack = np.concatenate([rgba(bor[(b, 14, 3)]), rgba(bor[(b, 14, 4)])], 0)
        grid.paste(grey_image(stack), ((b % 3) * 512, (b // 3) * 384))
    grid.save(os.path.join(OUT, 'borders-ingame.webp'), 'WEBP', quality=90, method=6)
    stack = np.concatenate([rgba(bgr[(0, 49, 3)]), rgba(bgr[(0, 49, 4)])], 0)
    grey_image(stack).save(os.path.join(OUT, 'bg-ingame.webp'), 'WEBP', quality=90, method=6)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    emb = fids(table('GuildTabardEmblem'))
    bor = fids(table('GuildTabardBorder'), Tier=0)
    bgr = fids(table('GuildTabardBackground'), Tier=0)
    build_emblems(emb)
    build_bases(bor, bgr)
    build_luts(emb, bor, bgr)
    print('in-game tabard assets written')
