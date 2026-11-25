import struct
def chunks(b):
    o=0; out={}
    while o+8<=len(b):
        tag=b[o:o+4].decode('latin1'); sz=struct.unpack_from('<I',b,o+4)[0]
        out.setdefault(tag,[]).append((o+8,sz)); o+=8+sz
    return out
class M2:
    def __init__(s,path):
        b=open(path,'rb').read(); s.ch=chunks(b)
        o,sz=s.ch['MD21'][0]; s.d=b[o:o+sz]; s.raw=b
        d=s.d
        arr=lambda off: struct.unpack_from('<II',d,off)
        s.version=struct.unpack_from('<I',d,4)[0]
        n,off=arr(0x3C); s.verts=[]
        for i in range(n):
            p=off+i*48
            pos=struct.unpack_from('<3f',d,p); bw=struct.unpack_from('<4B',d,p+12); bi=struct.unpack_from('<4B',d,p+16)
            nrm=struct.unpack_from('<3f',d,p+20); uv=struct.unpack_from('<4f',d,p+32)
            s.verts.append((pos,nrm,uv,bw,bi))
        n,off=arr(0x50); s.textures=[struct.unpack_from('<II',d,off+i*16) for i in range(n)]
        n,off=arr(0x80); s.texCombos=list(struct.unpack_from(f'<{n}H',d,off))
        n,off=arr(0x68); s.texLookupById=list(struct.unpack_from(f'<{n}h',d,off))
        n,off=arr(0x2C); s.nbones=n; s.bonesoff=off
        s.sfid=[]; 
        if 'SFID' in s.ch:
            o,sz=s.ch['SFID'][0]; s.sfid=list(struct.unpack_from(f'<{sz//4}I',b,o))
        s.txid=[]
        if 'TXID' in s.ch:
            o,sz=s.ch['TXID'][0]; s.txid=list(struct.unpack_from(f'<{sz//4}I',b,o))
class Skin:
    def __init__(s,path):
        d=open(path,'rb').read(); s.d=d
        arr=lambda off: struct.unpack_from('<II',d,off)
        n,off=arr(4); s.vidx=list(struct.unpack_from(f'<{n}H',d,off))
        n,off=arr(12); s.idx=list(struct.unpack_from(f'<{n}H',d,off))
        n,off=arr(28); s.subs=[]
        for i in range(n):
            p=off+i*48; v=struct.unpack_from('<10H',d,p)
            s.subs.append(dict(id=v[0],level=v[1],vstart=v[2],vcount=v[3],istart=v[4]+(v[1]<<16),icount=v[5]))
        n,off=arr(36); s.batches=[]
        for i in range(n):
            v=struct.unpack_from('<BbHHHHHHHHHHH',d,off+i*24)
            s.batches.append(dict(flags=v[0],shader=v[2],sub=v[3],geoset=v[4],mat=v[6],texCount=v[8],texCombo=v[9]))
