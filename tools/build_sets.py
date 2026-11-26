"""Tier 0.5 sets (Dungeon Set 2) for the Character view: body textures, geosets, helmets and shoulders.

For each of the nine class sets (ItemSet 511-519 in WoW Forever 1.60.1):
- models/sets/<set>-<sex>.webp: the armour's character textures in the 1024x512 body layout, drawn under the tabard:
  legs, boots, chest, bracers, gloves, in that order (a later piece covers an earlier one, as in game).
- models/sets/<set>-belt-<sex>.webp: the belt (LegUpper), drawn over the tabard like the Tier 1 belts.
- models/items/<FileDataID>.b64.txt + t<FileDataID>.webp: helmet (one per race and body type) and shoulder models,
  posed in the first frame of Stand. The page places them on the character's attachment points (export.py).
- models/sets/sets.json: names, the geosets each set switches, the geoset groups a helmet hides, the item models.

Item -> appearance -> ItemDisplayInfo -> material per body section (ItemDisplayInfoMaterialRes) or model and texture
(ModelResourcesID / ModelMaterialResourcesID) -> file, picked per race and body type with ComponentTextureFileData
and ComponentModelFileData. Skyborne wear Blood Elf helmets (ChrRaces model fallback).

Run after export.py: python build_sets.py
"""
import base64
import collections
import json
import os

import numpy as np
from PIL import Image

from fetchmodels import FOREVER
from m2 import M2, Skin
from pose import Skeleton, pose_vertices
from wago import DOCS, file as wago_file, table

SETS = [(511, 'heroism', 'Warrior'), (516, 'soulforge', 'Paladin'), (515, 'beastmaster', 'Hunter'),
        (512, 'darkmantle', 'Rogue'), (514, 'virtuous', 'Priest'), (519, 'fivethunders', 'Shaman'),
        (517, 'sorcerer', 'Mage'), (518, 'deathmist', 'Warlock'), (513, 'feralheart', 'Druid')]
RACE_ID = {'human': 1, 'orc': 2, 'dwarf': 3, 'nightelf': 4, 'scourge': 5, 'tauren': 6, 'gnome': 7, 'troll': 8,
           'skyborne': 95}
SEX = {'male': 0, 'female': 1}
# body sections in the 1024x512 layout: ArmUpper, ArmLower, Hand, TorsoUpper, TorsoLower, LegUpper, LegLower, Foot
SECTION = {0: (0, 0, 256, 128), 1: (0, 128, 256, 128), 2: (0, 256, 256, 64), 3: (256, 0, 256, 128),
           4: (256, 128, 256, 64), 5: (256, 192, 256, 128), 6: (256, 320, 256, 128), 7: (256, 448, 256, 64)}
HEAD, SHOULDER, CHEST, WAIST, LEGS, FEET, WRIST, HANDS, ROBE = 1, 3, 5, 6, 7, 8, 9, 10, 20
UNDER = [LEGS, FEET, CHEST, ROBE, WRIST, HANDS]  # drawing order under the tabard
# ItemDisplayInfo.GeosetGroup_k -> character geoset group, per inventory type; geoset = group * 100 + 1 + value.
# Legs come before the chest, so a robe's 13xx wins over the trousers'.
GEOSETS = [(LEGS, (11, 9, 13)), (FEET, (5, 20)), (WAIST, (18,)), (CHEST, (8, 10, 13, 22)), (ROBE, (8, 10, 13, 22)),
           (HANDS, (4, 23))]
OUT = os.path.join(DOCS, 'models')


def T(name):
    return table(name, FOREVER)


def file(fid):
    """game files from the WoW Forever build: a newer retail copy of a model may not match its skin file"""
    return wago_file(fid, FOREVER)


class Data:
    def __init__(self):
        self.sets = {r['ID']: r for r in T('ItemSet')}
        self.inv = {r['ID']: int(r['InventoryType']) for r in T('Item')}
        self.appearance = {}
        for r in T('ItemModifiedAppearance'):
            if r['ItemAppearanceModifierID'] == '0':
                self.appearance.setdefault(r['ItemID'], r['ItemAppearanceID'])
        self.display = {r['ID']: r['ItemDisplayInfoID'] for r in T('ItemAppearance')}
        self.idi = {r['ID']: r for r in T('ItemDisplayInfo')}
        self.material = collections.defaultdict(dict)
        for r in T('ItemDisplayInfoMaterialRes'):
            self.material[r['ItemDisplayInfoID']][int(r['ComponentSection'])] = r['MaterialResourcesID']
        self.textures = collections.defaultdict(list)
        for r in T('TextureFileData'):
            self.textures[r['MaterialResourcesID']].append(int(r['FileDataID']))
        self.ctfd = {int(r['ID']): r for r in T('ComponentTextureFileData')}
        self.models = collections.defaultdict(list)
        for r in T('ModelFileData'):
            self.models[r['ModelResourcesID']].append(int(r['FileDataID']))
        self.cmfd = {int(r['ID']): r for r in T('ComponentModelFileData')}
        self.helmet_hide = collections.defaultdict(set)
        for r in T('HelmetGeosetData'):
            self.helmet_hide[(r['HelmetGeosetVisDataID'], int(r['RaceID']))].add(int(r['HideGeosetGroup']))
        self.fallback = {int(r['ID']): (int(r['MaleModelFallbackRaceID']), int(r['FemaleModelFallbackRaceID']))
                         for r in T('ChrRaces')}

    def items(self, set_id):
        s = self.sets[str(set_id)]
        out = {}
        for i in range(17):
            item = s[f'ItemID_{i}']
            if item != '0':
                out[self.inv[item]] = self.idi[self.display[self.appearance[item]]]
        return out

    def texture(self, material_res, sex):
        """the file of a material for this body type: its own, else one for both"""
        best = None
        for fid in self.textures.get(material_res, []):
            c = self.ctfd.get(fid)
            g = int(c['GenderIndex']) if c else 3
            if g == SEX[sex]:
                return fid
            if g in (2, 3) or best is None:
                best = best or fid
        return best

    def model(self, res, race=None, sex=None, position=None):
        fids = self.models.get(res, [])
        for fid in fids:
            c = self.cmfd.get(fid)
            if c is None:
                continue
            if race is not None and (int(c['RaceID']) != race or int(c['GenderIndex']) != SEX[sex]):
                continue
            if position is not None and int(c['PositionIndex']) != position:
                continue
            return fid
        return None

    def helmet_race(self, race, sex):
        """the race whose helmet models a race wears: its own, else the ChrRaces model fallback"""
        fb = self.fallback.get(race, (0, 0))[SEX[sex]]
        return fb or race


def body_layers(d, items, key):
    out = os.path.join(OUT, 'sets')
    for sex in SEX:
        layer = Image.new('RGBA', (1024, 512))
        for inv in UNDER:
            row = items.get(inv)
            if not row:
                continue
            for sec, mr in sorted(d.material[row['ID']].items()):
                fid = d.texture(mr, sex)
                if fid is None or sec not in SECTION:
                    continue
                x, y, w, h = SECTION[sec]
                layer.alpha_composite(Image.open(file(fid)).convert('RGBA').resize((w, h), Image.BICUBIC), (x, y))
        layer.save(os.path.join(out, f'{key}-{sex}.webp'), 'WEBP', quality=88, method=6)
        belt = items.get(WAIST)
        mr = d.material[belt['ID']].get(5) if belt else None
        if mr:
            fid = d.texture(mr, sex)
            Image.open(file(fid)).convert('RGBA').resize((512, 256), Image.BICUBIC).save(
                os.path.join(out, f'{key}-belt-{sex}.webp'), 'WEBP', quality=88)


def save_texture(fid, done):
    name = f't{fid}.webp'
    if fid not in done:
        im = Image.open(file(fid)).convert('RGBA')
        if max(im.size) > 512:
            im = im.resize((max(1, im.width * 512 // max(im.size)), max(1, im.height * 512 // max(im.size))), Image.LANCZOS)
        im.save(os.path.join(OUT, 'items', name), 'WEBP', quality=88, method=6)
        done.add(fid)
    return fid


def item_model(fid, item_tex, metas, done_tex):
    """export one armour model, posed in frame 0 of Stand, in its own space (WoW axes); returns its meta"""
    if fid in metas:
        return metas[fid]
    m = M2(file(fid)); s = Skin(file(m.sfid[0]))
    try:
        mats = Skeleton(m).matrices()
    except Exception:
        mats = None
    pos, nrm, uv, idx, batches = [], [], [], [], []
    base = start = 0
    for b in s.batches:
        sub = s.subs[b['sub']]
        tex_i = m.texCombos[b['texCombo']] if b['texCombo'] < len(m.texCombos) else -1
        if tex_i < 0 or tex_i >= len(m.textures):
            continue
        kind = m.textures[tex_i][0]
        if kind == 2:
            tex = item_tex  # the item's own texture (ModelMaterialResourcesID)
        elif kind == 0 and tex_i < len(m.txid) and m.txid[tex_i]:
            tex = save_texture(m.txid[tex_i], done_tex)
        else:
            continue  # skin, hair and other character textures under a helmet: not drawn
        blend = m.materials[b['mat']][1] if b['mat'] < len(m.materials) else 0
        env = b['coord'] < len(m.texCoordCombos) and m.texCoordCombos[b['coord']] == -1
        vids = [s.vidx[k] for k in range(sub['vstart'], sub['vstart'] + sub['vcount'])]
        if mats is not None:
            P, N = pose_vertices(m, mats, vids)
        else:
            P = np.array([m.verts[v][0] for v in vids], np.float32); N = np.array([m.verts[v][1] for v in vids], np.float32)
        I = np.array(s.idx[sub['istart']:sub['istart'] + sub['icount']]) - sub['vstart'] + base
        pos.append(P); nrm.append(N); uv.append(np.array([m.verts[v][2][:2] for v in vids], np.float32)); idx.append(I)
        batches.append([start, int(len(I)), int(tex), int(blend), 1 if env else 0])
        start += len(I); base += len(P)
    if not batches:
        metas[fid] = None
        return None
    pos = np.concatenate(pos).astype(np.float32); uv = np.concatenate(uv).astype(np.float32)
    nrm = np.concatenate(nrm).astype(np.float32); nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
    n8 = np.clip(np.round(nrm * 127), -127, 127).astype(np.int8).tobytes()
    n8 += bytes((-len(n8)) % 4)
    blob = pos.tobytes() + uv.tobytes() + n8 + np.concatenate(idx).astype(np.uint16).tobytes()
    open(os.path.join(OUT, 'items', f'{fid}.b64.txt'), 'w').write(base64.b64encode(blob).decode())
    metas[fid] = dict(v=int(len(pos)), n=int(start), b=batches)
    return metas[fid]


def main():
    os.makedirs(os.path.join(OUT, 'sets'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'items'), exist_ok=True)
    d = Data()
    metas, done_tex, out = {}, set(), {}
    for set_id, key, cls in SETS:
        items = d.items(set_id)
        body_layers(d, items, key)
        geo = {}
        for inv, groups in GEOSETS:
            row = items.get(inv)
            for k, g in enumerate(groups):
                v = int(row[f'GeosetGroup_{k}']) if row else 0
                if v:
                    geo[g] = g * 100 + 1 + v
        entry = dict(name=d.sets[str(set_id)]['Name_lang'], cls=cls, geo=geo, belt=WAIST in items)
        head = items.get(HEAD)
        if head:
            tex = save_texture(d.texture(head['ModelMaterialResourcesID_0'], 'male'), done_tex)
            helm = {}
            for race, rid in RACE_ID.items():
                for sex, si in SEX.items():
                    hr = d.helmet_race(rid, sex)
                    fid = d.model(head['ModelResourcesID_0'], hr, sex)
                    if fid is None or item_model(fid, tex, metas, done_tex) is None:
                        continue
                    vis = head[f'HelmetGeosetVis_{si}']
                    hide = d.helmet_hide.get((vis, rid)) or d.helmet_hide.get((vis, hr)) or set()
                    helm[f'{race}_{sex}'] = dict(m=fid, hide=sorted(hide))
            entry['helm'] = helm
        sh = items.get(SHOULDER)
        if sh:
            for side, (k, pos) in (('L', (0, 0)), ('R', (1, 1))):
                res = sh[f'ModelResourcesID_{k}']
                fid = d.model(res, position=pos)
                mat = sh[f'ModelMaterialResourcesID_{k}']
                if fid and mat != '0':
                    tex = save_texture(d.texture(mat, 'male'), done_tex)
                    if item_model(fid, tex, metas, done_tex):
                        entry[f'shoulder{side}'] = fid
        out[key] = entry
        print(key, entry['name'], 'geosets', geo, 'helmets', len(entry.get('helm', {})),
              'shoulders', entry.get('shoulderL'), entry.get('shoulderR'), flush=True)
    data = dict(sets=out, items={str(k): v for k, v in metas.items() if v})
    json.dump(data, open(os.path.join(OUT, 'sets', 'sets.json'), 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
