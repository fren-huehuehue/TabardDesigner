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


def build_art():
    out = os.path.join(DOCS, 'img')
    os.makedirs(out, exist_ok=True)
    sheet = Image.new('RGBA', (14 * 125, 14 * 125))
    for i in range(196):
        sheet.alpha_composite(Image.open(armory(f'emblem_{i:02d}')).convert('RGBA'), ((i % 14) * 125, (i // 14) * 125))
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
