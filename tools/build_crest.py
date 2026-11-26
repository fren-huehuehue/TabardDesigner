"""Assets for the 2D Crest view, and the colour palette.

1. Blizzard's Armory tabard art (render.worldofwarcraft.com) -> docs/img/: emblem and border sprite sheets stored as
   grey + alpha (the page tints them) and the frame parts (background, shadow, overlay, hooks, faction rings).
2. The palette. For every colour: the in-game cloth colour, measured from the tier-0 Guild Tabard textures; the
   GuildColor value that Blizzard's crest API and Armory use; and the tint factors that turn the grey Armory art into
   the cloth colour. Written into the PAL block of docs/index.html.

Run: python build_crest.py
"""
import os
import re
import shutil

import numpy as np
from PIL import Image

from wago import CACHE, DOCS, download, file, table

ARMORY = 'https://render.worldofwarcraft.com/us/guild/tabards'
PARTS = ['bg_00', 'shadow_00', 'overlay_00', 'hooks', 'ring-alliance', 'ring-horde']


def armory(name):
    return download(f'{ARMORY}/{name}.png', os.path.join(CACHE, 'armory', f'{name}.png'))


def grey_alpha(im):
    return Image.merge('LA', (im.convert('L'), im.split()[3]))


# The Armory serves the wrong picture for two emblems: emblem_117 repeats the crossed hammers of 116 and emblem_144
# the scroll of 143, where the game has crossed spears (vendor #118) and crossed pickaxes (#145). Those two are drawn
# from the game's own white emblem texture, at the size, place and brightness the neighbour has against its texture.
ARMORY_WRONG = {117: 116, 144: 143}


def game_emblem(fid, e):
    """the emblem as the game stores it: TorsoUpper + TorsoLower, rolled so it sits whole, cropped to its pixels"""
    a = np.concatenate([np.roll(np.array(Image.open(file(fid[(e, 14, c)])).convert('RGBA')), 256, 1) for c in (3, 4)], 0)
    ys, xs = np.where(a[..., 3] > 4)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float64)


def from_game(sheet, e, ref):
    fid = {(int(r['EmblemID']), int(r['Color']), int(r['Component'])): r['FileDataID'] for r in table('GuildTabardEmblem')}
    tile = lambda i: np.array(sheet.crop(((i % 14) * 125, (i // 14) * 125, (i % 14) * 125 + 125, (i // 14) * 125 + 125)))
    t = tile(ref).astype(np.float64)
    ys, xs = np.where(t[..., 3] > 4)
    g_ref, g = game_emblem(fid, ref), game_emblem(fid, e)
    scale = ((np.ptp(xs) + 1) / g_ref.shape[1] + (np.ptp(ys) + 1) / g_ref.shape[0]) / 2
    w, h = max(1, round(g.shape[1] * scale)), max(1, round(g.shape[0] * scale))
    im = np.array(Image.fromarray(g.astype(np.uint8), 'RGBA').resize((w, h), Image.LANCZOS)).astype(np.float64)
    lum = im[..., :3] @ np.array([0.299, 0.587, 0.114])
    gain = highlight(t[t[..., 3] > 200][:, :3])[0] / highlight(np.repeat(lum[im[..., 3] > 200][:, None], 3, 1))[0]
    grey = np.clip(lum * gain, 0, 255)
    im = np.dstack([grey, grey, grey, im[..., 3]]).astype(np.uint8)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    cell, art = Image.new('RGBA', (125, 125)), Image.fromarray(im, 'RGBA')
    cell.paste(art, (round(cx - w / 2), round(cy - h / 2)), art)
    sheet.paste(cell, ((e % 14) * 125, (e // 14) * 125))


def build_art():
    out = os.path.join(DOCS, 'img')
    os.makedirs(out, exist_ok=True)
    sheet = Image.new('RGBA', (14 * 125, 14 * 125))
    for i in range(196):
        sheet.alpha_composite(Image.open(armory(f'emblem_{i:02d}')).convert('RGBA'), ((i % 14) * 125, (i // 14) * 125))
    for e, ref in ARMORY_WRONG.items():
        from_game(sheet, e, ref)
    grey_alpha(sheet).save(os.path.join(out, 'emblems.png'), optimize=True)
    strip = Image.new('RGBA', (6 * 147, 159))
    for i in range(6):
        strip.alpha_composite(Image.open(armory(f'border_{i:02d}')).convert('RGBA'), (i * 147, 0))
    grey_alpha(strip).save(os.path.join(out, 'borders.png'), optimize=True)
    for n in PARTS:
        shutil.copy(armory(n), os.path.join(out, f'{n}.png'))


def opaque(path):
    a = np.array(Image.open(path).convert('RGBA')).reshape(-1, 4)
    return a[a[:, 3] > 200][:, :3].astype(np.float64)


def highlight(px):
    """mean colour of the 60-90th luminance percentile: the lit cloth, without folds and highlights"""
    order = np.argsort(px @ np.array([0.3, 0.59, 0.11]))
    n = len(order)
    return px[order[int(n * 0.6):int(n * 0.9)]].mean(0)


def build_palette():
    emb = table('GuildTabardEmblem'); bor = table('GuildTabardBorder'); bg = table('GuildTabardBackground')
    sets = {
        'EMBLEM': ([r for r in emb if r['EmblemID'] == '6'], armory('emblem_06'), 'GuildColorEmblem'),
        'BORDER': ([r for r in bor if r['BorderID'] == '0' and r['Tier'] == '0'], armory('border_00'), 'GuildColorBorder'),
        'BACKGROUND': ([r for r in bg if r['Tier'] == '0' and r['Component'] == '3'], armory('bg_00'), 'GuildColorBackground'),
    }
    lines = []
    for name, (rows, base, api_table) in sets.items():
        base_hi = highlight(opaque(base))[0]  # the Armory art is grey: one channel is enough
        api = {int(r['ID']): '%02x%02x%02x' % (int(r['Red']), int(r['Green']), int(r['Blue'])) for r in table(api_table)}
        by_colour = {}
        for r in rows:
            by_colour.setdefault(int(r['Color']), []).append(opaque(file(r['FileDataID'])))
        entries = []
        for c in sorted(by_colour):
            hi = highlight(np.concatenate(by_colour[c]))
            swatch = '%02x%02x%02x' % tuple(min(255, int(round(x))) for x in hi)
            factors = ','.join(str(int(round(x / base_hi * 1000))) for x in hi)
            entries.append(f'{swatch}:{api[c]}:{factors}')
        lines.append(f"  {name}: '{' '.join(entries)}'")
    block = 'const PAL = {\n' + ',\n'.join(lines) + '\n};'
    p = os.path.join(DOCS, 'index.html')
    html = open(p, encoding='utf-8').read()
    html, n = re.subn(r'const PAL = \{\n.*?\n\};', lambda m: block, html, count=1, flags=re.S)
    assert n == 1, 'PAL block not found in index.html'
    open(p, 'w', encoding='utf-8').write(html)


if __name__ == '__main__':
    build_art()
    build_palette()
    print('crest art and palette written')
