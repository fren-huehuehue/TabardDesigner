import numpy as np
def render(tris_list, size=(560,700), view='front', bounds=None, light=(0.6,0.3,0.75)):
    """tris_list: list of (P[n,3], N[n,3], UV[n,2], I[m,3], tex(HxWx4 uint8) or color)"""
    W,H=size
    allp=np.concatenate([t[0] for t in tris_list])
    if bounds is None:
        ymin,ymax=allp[:,1].min(),allp[:,1].max(); zmin,zmax=allp[:,2].min(),allp[:,2].max()
    else: ymin,ymax,zmin,zmax=bounds
    sc=min(W/(ymax-ymin),H/(zmax-zmin))*0.92
    cy=(ymin+ymax)/2; cz=(zmin+zmax)/2
    img=np.zeros((H,W,3),np.float32); img[:]= (0.16,0.17,0.21)
    zb=np.full((H,W),-1e9,np.float32)
    L=np.array(light,np.float32); L/=np.linalg.norm(L)
    sgn=1 if view=='front' else -1
    for P,N,UV,I,tex in tris_list:
        # screen: x = -y*sgn (character faces +x; its left (+y) appears on screen right when viewed from front)
        sx=W/2+(-P[:,1]*sgn+cy*sgn)*sc*(-1)  # mirror so that +y is screen right
        sx=W/2+(P[:,1]-cy)*sc*sgn*-1
        sy=H/2-(P[:,2]-cz)*sc
        depth=P[:,0]*sgn
        Lv=L.copy(); Lv[0]*=sgn
        for a,b,c in I:
            xs=np.array([sx[a],sx[b],sx[c]]); ys=np.array([sy[a],sy[b],sy[c]])
            x0=max(int(np.floor(xs.min())),0); x1=min(int(np.ceil(xs.max())),W-1)
            y0=max(int(np.floor(ys.min())),0); y1=min(int(np.ceil(ys.max())),H-1)
            if x0>x1 or y0>y1: continue
            gx,gy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
            d=(ys[1]-ys[2])*(xs[0]-xs[2])+(xs[2]-xs[1])*(ys[0]-ys[2])
            if abs(d)<1e-9: continue
            w0=((ys[1]-ys[2])*(gx-xs[2])+(xs[2]-xs[1])*(gy-ys[2]))/d
            w1=((ys[2]-ys[0])*(gx-xs[2])+(xs[0]-xs[2])*(gy-ys[2]))/d
            w2=1-w0-w1
            m=(w0>=-1e-4)&(w1>=-1e-4)&(w2>=-1e-4)
            if not m.any(): continue
            z=w0*depth[a]+w1*depth[b]+w2*depth[c]
            sub=zb[y0:y1+1,x0:x1+1]
            m&=z>sub
            if not m.any(): continue
            n=(w0[...,None]*N[a]+w1[...,None]*N[b]+w2[...,None]*N[c])
            n/=np.linalg.norm(n,axis=-1,keepdims=True)+1e-9
            shade=np.clip(np.abs(n@Lv)*0.75+0.3,0,1.2)
            if isinstance(tex,np.ndarray):
                u=w0*UV[a,0]+w1*UV[b,0]+w2*UV[c,0]; v=w0*UV[a,1]+w1*UV[b,1]+w2*UV[c,1]
                th,tw=tex.shape[:2]
                tx=np.clip((u%1.0)*tw,0,tw-1).astype(int); ty=np.clip((v%1.0)*th,0,th-1).astype(int)
                col=tex[ty,tx,:3].astype(np.float32)/255
            else:
                col=np.broadcast_to(np.array(tex,np.float32)/255,(m.shape[0],m.shape[1],3))
            region=img[y0:y1+1,x0:x1+1]
            region[m]=(col*shade[...,None])[m]
            sub[m]=z[m]
    return (np.clip(img,0,1)*255).astype(np.uint8)
