"""Pick geosets, render a check sheet, and export web-ready model files."""
import sys, os, json, base64, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
from m2 import M2, Skin
from raster import render
from wago import CACHE, DOCS, file

OUT = os.path.join(DOCS, 'models')
INDEX = json.load(open(os.path.join(CACHE, 'models-index.json')))

# per-model overrides: hair style id, extra geosets, removed geosets
OVR = json.load(open(os.path.join(HERE, 'overrides.json'))) if os.path.exists(os.path.join(HERE, 'overrides.json')) else {}


def load(key):
    r = INDEX[key]
    m = M2(file(r['m2'], r.get('build'))); s = Skin(file(r['skin']))
    return m, s


def subinfo(m, s):
    info = {}
    for i, sub in enumerate(s.subs):
        bs = [b for b in s.batches if b['sub'] == i]
        tt = [m.textures[m.texCombos[b['texCombo']]][0] if b['texCombo'] < len(m.texCombos) and m.texCombos[b['texCombo']] < len(m.textures) else -1 for b in bs]
        info.setdefault(sub['id'], []).append((i, sub, tt))
    return info


def choose(key, info):
    o = OVR.get(key, {})
    ids = set(info)
    groups = {}
    for g in ids:
        groups.setdefault(g // 100, []).append(g)
    sel = [0]
    hairs = sorted(i for i in groups.get(0, []) if i > 0)
    hair = o.get('hair', hairs[0] if hairs else None)
    if hair is not None and hair in ids:
        sel.append(hair)
    for g in (4, 5, 13, 18, 20, 22, 23):  # 23: elf hands (the elves' 401 is only the wrist)
        if g * 100 + 1 in ids:
            sel.append(g * 100 + 1)
        elif g in groups:
            sel.append(min(groups[g]))
    if 702 in ids:
        sel.append(702)
    elif 701 in ids:
        sel.append(701)
    faces = sorted(i for i in groups.get(32, []) if sum(x[1]['vcount'] for x in info[i]) > 200)
    if faces:
        sel.append(faces[0])
    if 3301 in ids:
        sel.append(3301)
    if 1202 in ids:
        sel.append(1202)
    sel += [g for g in o.get('add', []) if g in ids]
    sel = [g for g in sel if g not in o.get('remove', [])]
    return sorted(set(sel))


def body_texture(key, with_tabard=None):
    r = INDEX[key]
    T = lambda k: Image.open(file(r[k])).convert('RGBA')
    base = T('skintex').resize((1024, 512), Image.BICUBIC)
    if r.get('pelvis'):
        base.alpha_composite(T('pelvis').resize((256, 128)), (256, 192))
    if r.get('torso'):
        base.alpha_composite(T('torso').resize((256, 128)), (256, 0))
    if r.get('face'):  # a separate face layer (Skyborne): section 10, the right half
        base.alpha_composite(T('face').resize((512, 512)), (512, 0))
    if with_tabard is not None:
        base.alpha_composite(with_tabard.resize((256, 192)), (256, 0))
    return base


def hair_texture(key, kind='hair'):
    fid = INDEX[key].get(kind)
    if fid:
        return Image.open(file(fid)).convert('RGBA')
    return None


def geometry(m, s, info, sel, hairtex_ok):
    """returns list of (P,N,UV,I,kind) per selected submesh, posed in frame 0 of Stand"""
    from pose import Skeleton, pose_vertices
    if not hasattr(m, '_mats'):
        try:
            m._mats = Skeleton(m).matrices()
        except Exception as e:
            print('pose failed', e); m._mats = None
    mats = m._mats
    parts = []
    for g in sel:
        for i, sub, tt in info[g]:
            vids = [s.vidx[k] for k in range(sub['vstart'], sub['vstart'] + sub['vcount'])]
            if mats is not None:
                P, N = pose_vertices(m, mats, vids)
            else:
                P = np.array([m.verts[v][0] for v in vids], np.float32)
                N = np.array([m.verts[v][1] for v in vids], np.float32)
            UV = np.array([m.verts[v][2][:2] for v in vids], np.float32)
            I = np.array(s.idx[sub['istart']:sub['istart'] + sub['icount']]).reshape(-1, 3) - sub['vstart']
            t0 = tt[0] if tt else 1
            if t0 in (0, 2, -1):
                continue  # hardcoded textures (eye glow etc.) and capes
            kind = 'hair' if t0 == 6 else 'extra' if t0 == 8 else 'body'
            parts.append((P, N, UV, I, kind, g))
    return parts


def tabard_demo():
    # background 5, border 0 in colour 15, emblem 6 in colour 16 (tier 0 textures, for the check sheet only)
    L = lambda f: Image.open(file(f)).convert('RGBA')
    tu = L('180071'); tu.alpha_composite(L('180193')); tu.alpha_composite(L('180635'))
    tl = L('180070'); tl.alpha_composite(L('180192')); tl.alpha_composite(L('180634'))
    st = Image.new('RGBA', (512, 384)); st.paste(tu, (0, 0)); st.paste(tl, (0, 256))
    return st


def check_sheet(keys, path):
    demo = tabard_demo()
    tiles = []
    for key in keys:
        m, s = load(key); info = subinfo(m, s); sel = choose(key, info)
        bt = np.array(body_texture(key, demo))
        ht = hair_texture(key); ht = np.array(ht) if ht is not None else (70, 50, 40)
        et = hair_texture(key, 'extra'); et = np.array(et) if et is not None else ht
        parts = [(P, N, UV, I, {'body': bt, 'hair': ht, 'extra': et}[k]) for P, N, UV, I, k, g in geometry(m, s, info, sel, True)]
        img = render(parts, size=(300, 380), view='front')
        im = Image.fromarray(img)
        from PIL import ImageDraw
        ImageDraw.Draw(im).text((4, 4), key, fill=(255, 209, 0))
        ImageDraw.Draw(im).text((4, 366), ' '.join(map(str, sel)), fill=(200, 200, 200))
        tiles.append(im)
        print(key, 'sel', sel, 'all groups', sorted(info), flush=True)
    cols = 5
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 300, rows * 380))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 300, (i // cols) * 380))
    sheet.save(path)


def export(key):
    m, s = load(key); info = subinfo(m, s); sel = choose(key, info)
    parts = geometry(m, s, info, sel, True)
    # WoW (x fwd, y left, z up) -> three (X=y, Y=z, Z=x)
    pos = []; nrm = []; uv = []; tri = {'body': [], 'hair': [], 'extra': []}; base = 0
    for P, N, UV, I, k, g in parts:
        pos.append(P[:, [1, 2, 0]]); nrm.append(N[:, [1, 2, 0]]); uv.append(UV)
        tri[k].append(I + base); base += len(P)
    assert base < 65536, base
    pos = np.concatenate(pos).astype(np.float32); nrm = np.concatenate(nrm).astype(np.float32); uv = np.concatenate(uv).astype(np.float32)
    pos[:, 1] -= pos[:, 1].min()
    pos[:, 0] -= (pos[:, 0].min() + pos[:, 0].max()) / 2
    pos[:, 2] -= (pos[:, 2].min() + pos[:, 2].max()) / 2
    nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
    n8 = np.clip(np.round(nrm * 127), -127, 127).astype(np.int8).tobytes()
    n8 += b'\0' * ((-len(n8)) % 4)
    idx = {k: (np.concatenate(v).astype(np.uint16).ravel() if v else np.zeros(0, np.uint16)) for k, v in tri.items()}
    os.makedirs(OUT, exist_ok=True)
    # layout: pos f32 (12v) | uv f32 (8v) | normals i8 (3v, padded to 4) | body u16 | hair u16 | extra u16
    blob = pos.tobytes() + uv.tobytes() + n8 + idx['body'].tobytes() + idx['hair'].tobytes() + idx['extra'].tobytes()
    # artifacts only serve text and media types, so the page reads base64 text (GitHub Pages compresses it)
    open(os.path.join(OUT, f'{key}.b64.txt'), 'w').write(base64.b64encode(blob).decode())
    meta = dict(v=int(len(pos)), body=int(len(idx['body'])), hair=int(len(idx['hair'])), extra=int(len(idx['extra'])),
                height=round(float(pos[:, 1].max()), 3))
    body_texture(key).convert('RGB').save(os.path.join(OUT, f'{key}-skin.jpg'), quality=85)
    for kind in ('hair', 'extra'):
        t = hair_texture(key, kind)
        if t is not None and meta[kind]:
            if max(t.size) > 512:
                t = t.resize((t.width // 2, t.height // 2), Image.LANCZOS)
            t.save(os.path.join(OUT, f'{key}-{kind}.webp'), 'WEBP', quality=85)
            meta[kind + 'Tex'] = True
    return meta


if __name__ == '__main__':
    mode = sys.argv[1]
    keys = [k for k in INDEX if INDEX[k].get('m2') and INDEX[k].get('skin')]
    if len(sys.argv) > 2:
        keys = [k for k in keys if k in sys.argv[2].split(',')]
    if mode == 'check':
        check_sheet(keys, os.path.join(CACHE, 'models_check.png'))
    else:
        metas = {k: export(k) for k in keys}
        path = os.path.join(OUT, 'models.json')
        if len(sys.argv) > 2 and os.path.exists(path):  # a subset updates its own entries only
            old = json.load(open(path))
            metas = {k: metas.get(k, old.get(k)) for k in INDEX if k in metas or k in old}
        json.dump(metas, open(path, 'w'), indent=1)
        print(json.dumps(metas, indent=1))
