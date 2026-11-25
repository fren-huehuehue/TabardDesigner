"""Resolve model, skin file and texture FileDataIDs for each race/gender and download them.

Writes models-index.json in the cache, which export.py reads. Fixes that the listfile cannot tell us
(a different skin colour, a model file pinned to a build) come from overrides.json. A model whose files have no
listfile name (Skyborne) lists all its FileDataIDs there under "files".
"""
import collections
import json
import os
import re

from wago import CACHE, file, search, table

HERE = os.path.dirname(os.path.abspath(__file__))
# the playable races of WoW Forever (build 1.60.1): the eight original races and the Skyborne
RACES = ['human', 'orc', 'dwarf', 'nightelf', 'scourge', 'tauren', 'gnome', 'troll', 'skyborne']
FOREVER = '1.60.1.71091'  # the WoW Forever build the races and their customisation data come from
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


def eye_textures():
    """{race_sex: FileDataID} of the default eye texture (texture type 19): the first choice of the Eye Color option
    (Eye Glow for the Undead), looked up in the ChrCustomization tables."""
    T = lambda n: table(n, FOREVER)
    race_ids = collections.defaultdict(set)
    for r in T('ChrRaces'):
        if r['PlayableRaceBit'] != '-1':
            race_ids[r['ClientFileString'].lower()].add(r['ID'])
    model = {}
    for r in T('ChrRaceXChrModel'):
        for race, ids in race_ids.items():
            if r['ChrRacesID'] in ids:
                model[f"{race}_{'male' if r['Sex'] == '0' else 'female'}"] = r['ChrModelID']
    layout = {r['ID']: r['CharComponentTextureLayoutID'] for r in T('ChrModel')}
    options = collections.defaultdict(list)
    for o in T('ChrCustomizationOption'):
        if o['Name_lang'] in ('Eye Color', 'Eye Glow'):
            options[o['ChrModelID']].append(o['ID'])
    first = {}
    for c in T('ChrCustomizationChoice'):
        k = c['ChrCustomizationOptionID']
        if k not in first or int(c['OrderIndex']) < int(first[k]['OrderIndex']):
            first[k] = c
    elements = collections.defaultdict(list)
    for e in T('ChrCustomizationElement'):
        elements[e['ChrCustomizationChoiceID']].append(e['ChrCustomizationMaterialID'])
    material = {m['ID']: m for m in T('ChrCustomizationMaterial')}
    eye_targets = {(l[t], l['CharComponentTextureLayoutsID']) for l in T('ChrModelTextureLayer') if l['TextureType'] == '19'
                   for t in ('ChrModelTextureTargetID_0', 'ChrModelTextureTargetID_1') if l[t] != '0'}
    files = collections.defaultdict(list)
    for t in T('TextureFileData'):
        files[t['MaterialResourcesID']].append(int(t['FileDataID']))
    out = {}
    for key, mid in model.items():
        for oid in options.get(mid, []):
            for mat_id in elements[first[oid]['ID']] if oid in first else []:
                m = material.get(mat_id)
                if m and (m['ChrModelTextureTargetID'], layout[mid]) in eye_targets and files.get(m['MaterialResourcesID']):
                    out.setdefault(key, files[m['MaterialResourcesID']][0])
    return out


def resolve(race, sex):
    o = OVR.get(f'{race}_{sex}', {})
    if o.get('files'):
        return dict(o['files'])
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
    res.update(o.get('tex', {}))
    if o.get('build'):
        res['build'] = o['build']
    return {k: v for k, v in res.items() if v is not None}


if __name__ == '__main__':
    index = {}
    eyes = eye_textures()
    for race in RACES:
        for sex in ('male', 'female'):
            r = resolve(race, sex)
            key = f'{race}_{sex}'
            if key in eyes:
                r.setdefault('eyes', eyes[key])
            file(r['m2'], r.get('build'))
            for kind in ('skin', 'skintex', 'pelvis', 'torso', 'face', 'hair', 'extra', 'eyes'):
                if r.get(kind):
                    file(r[kind])
            index[key] = r
            print(key, r, flush=True)
    json.dump(index, open(INDEX, 'w'), indent=1)
