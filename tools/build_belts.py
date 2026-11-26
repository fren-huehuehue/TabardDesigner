"""Belt textures for the Character view: the nine Tier 1 belts from Molten Core.

Classic belts are a single LegUpper texture (no buckle model, no extra geoset). The page draws it over the waist
band (geoset 1801) of the character texture. Item -> appearance -> display info -> material for section 5 (LegUpper)
-> texture file.

Run: python build_belts.py
"""
import collections
import os

from PIL import Image

from wago import DOCS, file, table

BELTS = [('might', 'Belt of Might'), ('lawbringer', 'Lawbringer Belt'), ('giantstalker', "Giantstalker's Belt"),
         ('nightslayer', 'Nightslayer Belt'), ('prophecy', 'Girdle of Prophecy'), ('earthfury', 'Earthfury Belt'),
         ('arcanist', 'Arcanist Belt'), ('felheart', 'Felheart Belt'), ('cenarion', 'Cenarion Belt')]
LEG_UPPER = 5


def main():
    out = os.path.join(DOCS, 'models', 'belts')
    os.makedirs(out, exist_ok=True)
    names = {r['Display_lang']: r['ID'] for r in table('ItemSearchName') if r['ExpansionID'] == '0'}
    appearance = {}
    for r in table('ItemModifiedAppearance'):
        if r['ItemAppearanceModifierID'] == '0':
            appearance.setdefault(r['ItemID'], r['ItemAppearanceID'])
    display = {r['ID']: r['ItemDisplayInfoID'] for r in table('ItemAppearance')}
    material = collections.defaultdict(dict)
    for r in table('ItemDisplayInfoMaterialRes'):
        material[r['ItemDisplayInfoID']][int(r['ComponentSection'])] = r['MaterialResourcesID']
    texture = {}
    for r in table('TextureFileData'):
        texture.setdefault(r['MaterialResourcesID'], r['FileDataID'])
    for key, name in BELTS:
        item = names[name]
        d = display[appearance[item]]
        fid = texture[material[d][LEG_UPPER]]
        im = Image.open(file(fid)).convert('RGBA')
        if im.size != (512, 256):
            im = im.resize((512, 256), Image.BICUBIC)
        im.save(os.path.join(out, f'{key}.webp'), 'WEBP', quality=88)
        print(f'{name:22} item {item:>6} display {d:>6} texture {fid}')


if __name__ == '__main__':
    main()
