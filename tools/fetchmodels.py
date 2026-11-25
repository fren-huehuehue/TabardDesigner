"""Resolve model, skin file and texture FileDataIDs for each race/gender and download them.

Writes tools/cache/models-index.json, which export.py reads. Fixes that the listfile cannot tell us
(a different skin colour, a model file pinned to a build) come from overrides.json.
"""
import json
import os
import re

from wago import CACHE, file, search

HERE = os.path.dirname(os.path.abspath(__file__))
RACES = ['human', 'orc', 'dwarf', 'nightelf', 'scourge', 'tauren', 'gnome', 'troll', 'bloodelf', 'draenei']
OVR = json.load(open(os.path.join(HERE, 'overrides.json')))
INDEX = os.path.join(CACHE, 'models-index.json')


def nums(n):
    return [int(x) for x in re.findall(r'\d+', n)]


def lowest(inv, patterns):
    for pat in patterns:
        c = sorted((n for n in inv if re.fullmatch(pat, n)), key=nums)
        if c:
            return inv[c[0]]
    return None


def resolve(race, sex):
    inv = {v.split('/')[-1]: k for k, v in search(f'character/{race}/{sex}/').items()}
    p, q = f'{race}{sex}', f'{race}_{sex}'  # night elf textures use both spellings
    res = {
        'm2': lowest(inv, [rf'{p}_hd\.m2']),
        'skin': lowest(inv, [rf'{p}_hd00\.skin']),
        'skintex': lowest(inv, [rf'{x}skin00_00_hd\.blp' for x in (p, q)] + [rf'{x}skin\d\d_\d\d_hd\.blp' for x in (p, q)]),
        'pelvis': lowest(inv, [rf'{x}nakedpelvisskin00_00_hd\.blp' for x in (p, q)] + [rf'{x}nakedpelvisskin\d\d_\d\d_hd\.blp' for x in (p, q)]),
        'hair': lowest(inv, [rf'{p}(_hd)?_hair_color_\d+\.blp', rf'{p}_hd_hair_style_\d+\.blp', rf'{p}hair\d+\.blp']),
        'extra': lowest(inv, [rf'{p}skin00_00_extra_hd\.blp', rf'{p}skin\d\d_\d\d_extra_hd\.blp']),
    }
    if sex == 'female':
        res['torso'] = lowest(inv, [rf'{x}nakedtorsoskin00_00_hd\.blp' for x in (p, q)] + [rf'{x}nakedtorsoskin\d\d_\d\d_hd\.blp' for x in (p, q)])
    o = OVR.get(f'{race}_{sex}', {})
    res.update(o.get('tex', {}))
    if o.get('build'):
        res['build'] = o['build']
    return {k: v for k, v in res.items() if v is not None}


if __name__ == '__main__':
    index = {}
    for race in RACES:
        for sex in ('male', 'female'):
            r = resolve(race, sex)
            key = f'{race}_{sex}'
            file(r['m2'], r.get('build'))
            for kind in ('skin', 'skintex', 'pelvis', 'torso', 'hair', 'extra'):
                if r.get(kind):
                    file(r[kind])
            index[key] = r
            print(key, r, flush=True)
    json.dump(index, open(INDEX, 'w'), indent=1)
