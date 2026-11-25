"""Pose an M2 model in the first frame of its Stand animation."""
import struct
import numpy as np
from m2 import chunks
from wago import file


def fetch(fid):
    return open(file(fid), 'rb').read()


def arr(d, off):
    return struct.unpack_from('<II', d, off)


def cq(v):
    return (v + 32768) / 32767.0 if v < 0 else (v - 32767) / 32767.0


def quat_mat(x, y, z, w):
    n = (x * x + y * y + z * z + w * w) ** 0.5 or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]], np.float64)


class Skeleton:
    """bones + sequences from either the M2 itself or its .skel file"""

    def __init__(self, m):
        self.m = m
        raw = m.raw
        if 'SKID' in m.ch:
            o, _ = m.ch['SKID'][0]
            skel = fetch(struct.unpack_from('<I', raw, o)[0])
            ch = chunks(skel)
            o, sz = ch['SKB1'][0]; self.bd = skel[o:o + sz]; self.boff = 0
            n, off = arr(self.bd, 0)
            self.bones = (self.bd, n, off)
            o, sz = ch['SKS1'][0]; sd = skel[o:o + sz]
            # SKS1: global_loops M2Array, sequences M2Array, sequence_lookups M2Array
            n, off = arr(sd, 8)
            self.seqs = [(sd, off + i * 64) for i in range(n)]
            self.afid = self._afid(skel, ch)
            self.seq_data_src = skel  # in-file sequence data lives in SKB1 relative offsets
            self.inline = self.bd
            if 'SKPD' in ch:
                self.parent = True
        else:
            d = m.d
            self.bd = d
            n, off = arr(d, 0x2C)
            self.bones = (d, n, off)
            n, off = arr(d, 0x1C)
            self.seqs = [(d, off + i * 64) for i in range(n)]
            self.afid = self._afid(raw, m.ch)
            self.inline = d

    @staticmethod
    def _afid(raw, ch):
        res = {}
        if 'AFID' in ch:
            o, sz = ch['AFID'][0]
            for i in range(sz // 8):
                aid, sub, fid = struct.unpack_from('<HHI', raw, o + i * 8)
                res[(aid, sub)] = fid
        return res

    def stand_index(self):
        for i, (d, off) in enumerate(self.seqs):
            aid, var = struct.unpack_from('<HH', d, off)
            if aid == 0 and var == 0:
                flags = struct.unpack_from('<I', d, off + 12)[0]
                return i, flags
        return None, None

    def matrices(self):
        si, flags = self.stand_index()
        ext = None
        if si is not None and not (flags & 0x20):
            fid = self.afid.get((0, 0))
            if fid:
                a = fetch(fid)
                if a[:4] == b'AFM2':
                    ch = chunks(a); o, sz = ch['AFM2'][0]; ext = a[o:o + sz]
                else:
                    ext = a
        d, n, off = self.bones
        mats = [None] * n
        info = []
        for b in range(n):
            p = off + b * 88
            key, flg, parent, sub = struct.unpack_from('<iIhH', d, p)
            tr = self._track(d, p + 16, si, ext, 12, lambda bb, o: struct.unpack_from('<3f', bb, o))
            ro = self._track(d, p + 36, si, ext, 8, lambda bb, o: tuple(cq(v) for v in struct.unpack_from('<4h', bb, o)))
            sc = self._track(d, p + 56, si, ext, 12, lambda bb, o: struct.unpack_from('<3f', bb, o))
            pivot = np.array(struct.unpack_from('<3f', d, p + 76))
            info.append((parent, tr, ro, sc, pivot))
        for b in range(n):
            self._resolve(b, info, mats)
        return mats

    def _track(self, d, off, si, ext, size, read):
        interp, gseq = struct.unpack_from('<Hh', d, off)
        tn, toff = arr(d, off + 4)
        vn, voff = arr(d, off + 12)
        if vn == 0:
            return None
        idx = 0 if gseq >= 0 else si
        if idx is None or idx >= vn:
            return None
        cnt, o = arr(d, voff + idx * 8)
        if cnt == 0:
            return None
        src = d if (gseq >= 0 or ext is None) else ext
        try:
            return read(src, o)
        except struct.error:
            return None

    def _resolve(self, b, info, mats):
        if mats[b] is not None:
            return mats[b]
        parent, tr, ro, sc, pv = info[b]
        M = np.eye(4)
        T = np.eye(4); T[:3, 3] = pv
        Ti = np.eye(4); Ti[:3, 3] = -pv
        L = np.eye(4)
        if tr is not None:
            L[:3, 3] = tr
        R = np.eye(4)
        if ro is not None:
            x, y, z, w = ro
            R[:3, :3] = quat_mat(x, y, z, w)
        S = np.eye(4)
        if sc is not None:
            S[0, 0], S[1, 1], S[2, 2] = sc
        M = T @ L @ R @ S @ Ti
        if 0 <= parent < len(info) and parent != b:
            M = self._resolve(parent, info, mats) @ M
        mats[b] = M
        return M


def pose_vertices(m, mats, vids):
    P = np.array([m.verts[v][0] for v in vids], np.float64)
    N = np.array([m.verts[v][1] for v in vids], np.float64)
    W = np.array([m.verts[v][3] for v in vids], np.float64) / 255.0
    B = np.array([m.verts[v][4] for v in vids], np.int64)
    outP = np.zeros_like(P); outN = np.zeros_like(N)
    Ph = np.hstack([P, np.ones((len(P), 1))])
    for k in range(4):
        w = W[:, k]
        mk = w > 0
        if not mk.any():
            continue
        Ms = np.stack([mats[b] if b < len(mats) else np.eye(4) for b in B[mk, k]])
        outP[mk] += (Ms @ Ph[mk][:, :, None])[:, :3, 0] * w[mk, None]
        outN[mk] += (Ms[:, :3, :3] @ N[mk][:, :, None])[:, :, 0] * w[mk, None]
    none = W.sum(1) == 0
    outP[none] = P[none]; outN[none] = N[none]
    outN /= (np.linalg.norm(outN, axis=1, keepdims=True) + 1e-9)
    return outP.astype(np.float32), outN.astype(np.float32)
