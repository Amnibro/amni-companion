import io,json,os,struct,sys,cv2,xatlas,numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage,sparse
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import dijkstra
H,SIG,CT=0.007,0.025,{5126:np.float32,5123:np.uint16,5121:np.uint8,5125:np.uint32}
OVAL=[10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109];FIT=[33,133,362,263,1,4,5,6,168,195,197,61,291,13,14,152,10,234,454]
UE={'Hips':'pelvis','Spine':'spine_01','Spine1':'spine_02','Spine2':'spine_03','Neck':'neck_01','Head':'Head','LeftShoulder':'clavicle_l','LeftArm':'upperarm_l','LeftForeArm':'lowerarm_l','LeftHand':'hand_l','RightShoulder':'clavicle_r','RightArm':'upperarm_r','RightForeArm':'lowerarm_r','RightHand':'hand_r','LeftUpLeg':'thigh_l','LeftLeg':'calf_l','LeftFoot':'foot_l','LeftToeBase':'ball_l','RightUpLeg':'thigh_r','RightLeg':'calf_r','RightFoot':'foot_r','RightToeBase':'ball_r'}
def rd(path):
    b=open(path,'rb').read();n=struct.unpack('<I',b[12:16])[0];j=json.loads(b[20:20+n]);o=20+n;m=struct.unpack('<I',b[o:o+4])[0];return j,bytearray(b[o+8:o+8+m])
def wr(path,j,bn):
    js=json.dumps(j,separators=(',',':')).encode();js+=b' '*(-len(js)%4);bn=bytes(bn)+b'\0'*(-len(bn)%4);j['buffers'][0]['byteLength']=len(bn);js=json.dumps(j,separators=(',',':')).encode();js+=b' '*(-len(js)%4)
    open(path,'wb').write(struct.pack('<III',0x46546C67,2,28+len(js)+len(bn))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(bn),0x004E4942)+bn)
def loc(j,i):
    a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];t=np.dtype(CT[a['componentType']]);c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];return v.get('byteOffset',0)+a.get('byteOffset',0),v.get('byteStride',0) or t.itemsize*c,t,c,a['count']
def get(j,bn,i):
    o,s,t,c,n=loc(j,i);return np.ndarray((n,c),t,bn,o,(s,t.itemsize)).astype(np.float64)
def put(j,bn,i,x):
    o,s,t,c,n=loc(j,i);np.ndarray((n,c),t,bn,o,(s,t.itemsize))[:]=x.astype(t)
def skel(j):
    sk=j['skins'][0];jn=sk['joints'];names=[j['nodes'][i]['name'] for i in jn];ix={n:k for k,n in enumerate(names)};par=[-1]*len(jn);[par.__setitem__(jn.index(c),k) for k,i in enumerate(jn) for c in j['nodes'][i].get('children',[]) if c in jn]
    if any('rotation' in j['nodes'][i] or 'scale' in j['nodes'][i] for i in jn):sys.exit('joint rotations are not supported')
    wp=np.zeros((len(jn),3))
    for k in range(len(jn)):wp[k]=np.array(j['nodes'][jn[k]].get('translation',[0,0,0]))+(wp[par[k]] if par[k]>=0 else 0)
    return sk,jn,names,ix,par,wp
def setskel(j,bn,sk,jn,par,wp):
    for k in range(len(jn)):j['nodes'][jn[k]]['translation']=list(map(float,wp[k]-(wp[par[k]] if par[k]>=0 else 0)))
    ib=np.zeros((len(jn),16));ib[:,[0,5,10,15]]=1;ib[:,12:15]=-wp;put(j,bn,sk['inverseBindMatrices'],ib)
def snorm(P,F):
    pk=np.unique(np.round(P/1e-5).astype(np.int64),axis=0,return_inverse=True)[1].ravel();fn=np.cross(P[F[:,1]]-P[F[:,0]],P[F[:,2]]-P[F[:,0]]);a=np.zeros((pk.max()+1,3));[np.add.at(a,pk[F[:,c]],fn) for c in range(3)];n=a[pk];return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
def rdg(path):
    if path.endswith('.glb'):return rd(path)
    j=json.load(open(path));return j,bytearray(open(os.path.join(os.path.dirname(path),j['buffers'][0]['uri']),'rb').read())
def tsamp(P,F,step):
    A,B,C=P[F[:,0]],P[F[:,1]],P[F[:,2]];K=np.clip(np.ceil(np.maximum.reduce([np.linalg.norm((B-A)[:,:3],axis=1),np.linalg.norm((C-A)[:,:3],axis=1),np.linalg.norm((C-B)[:,:3],axis=1)])/step),1,40).astype(int)
    for k in np.unique(K):m=K==k;u,v=np.meshgrid(np.arange(k+1),np.arange(k+1));sl=(u+v)<=k;u,v=u[sl]/k,v[sl]/k;yield (A[m][:,None]+(B[m]-A[m])[:,None]*u[None,:,None]+(C[m]-A[m])[:,None]*v[None,:,None]).reshape(-1,P.shape[1])
def depth(P,F,lo,cs,shape):
    Z=np.full(shape,-np.inf)
    for q in tsamp(P,F,.5*cs):g=((q[:,:2]-lo)/cs).astype(int);ok=(g>=0).all(1)&(g[:,0]<shape[0])&(g[:,1]<shape[1]);np.maximum.at(Z,(g[ok,0],g[ok,1]),q[ok,2])
    bad=~np.isfinite(Z);ix=ndimage.distance_transform_edt(bad,return_distances=False,return_indices=True);return Z[ix[0],ix[1]]
def bil(Z,lo,cs,xy):
    f=np.clip((xy-lo)/cs,0,np.array(Z.shape[:2])-1.001);i=f.astype(int);t=f-i;g=lambda a,b:Z[i[:,0]+a,i[:,1]+b].reshape(len(xy),-1);r=(g(0,0)*(1-t[:,:1])+g(1,0)*t[:,:1])*(1-t[:,1:])+(g(0,1)*(1-t[:,:1])+g(1,1)*t[:,:1])*t[:,1:];return r[:,0] if Z.ndim==2 else r
def poly(xy,pg):
    a,b=pg,np.roll(pg,-1,0);ins=np.zeros(len(xy),bool);dmin=np.full(len(xy),np.inf)
    for p0,p1 in zip(a,b):c=((p0[1]>xy[:,1])!=(p1[1]>xy[:,1]))&(xy[:,0]<(p1[0]-p0[0])*(xy[:,1]-p0[1])/(p1[1]-p0[1]+1e-12)+p0[0]);ins^=c;dmin=np.minimum(dmin,seg(np.c_[xy,np.zeros(len(xy))],np.r_[p0,0],np.r_[p1,0]))
    return ins,dmin
def facepack(tpl,marks,out):
    j,bn=rdg(tpl);V=[];Fs=[];o=0;M=np.array([p if p else [np.nan]*3 for p in json.load(open(marks))['pts']]);c=np.nanmean(M[OVAL],0)
    for m in j['meshes']:
        for p in m['primitives']:
            if 'Hair' in j['materials'][p.get('material',0)].get('name',''):continue
            P=get(j,bn,p['attributes']['POSITION']);F=get(j,bn,p['indices']).astype(int).reshape(-1,3);V.append(P);Fs.append(F+o);o+=len(P)
    V=np.concatenate(V);F=np.concatenate(Fs);keep=(np.abs(V[:,:2]-c[:2])<.16).all(1)&(V[:,2]>c[2]-.12);fk=keep[F].all(1);ui,inv=np.unique(F[fk],return_inverse=True);np.savez_compressed(out,V=V[ui].astype(np.float32),F=inv.reshape(-1,3).astype(np.int32),M=M.astype(np.float32));print(out,len(ui),'verts',fk.sum(),'tris')
def face(path,marks,pack,feather=.012):
    j,bn=rd(path);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);F=get(j,bn,pr['indices']).astype(np.int64).reshape(-1,3);Hm=np.array([p if p else [np.nan]*3 for p in json.load(open(marks))['pts']]);z=np.load(pack);TV,TF,Tm=z['V'].astype(float),z['F'],z['M'].astype(float)
    ok=[i for i in FIT if np.isfinite(Tm[i]).all() and np.isfinite(Hm[i]).all()];A=Tm[ok,:2]-Tm[ok,:2].mean(0);B=Hm[ok,:2]-Hm[ok,:2].mean(0);U,S,Vt=np.linalg.svd(B.T@A);D=np.diag([1,np.sign(np.linalg.det(U@Vt))]);R=U@D@Vt;sc=(S*np.diag(D)).sum()/(A**2).sum();t=Hm[ok,:2].mean(0)-sc*R@Tm[ok,:2].mean(0);X=np.c_[(sc*(R@TV[:,:2].T)).T+t,sc*TV[:,2]]
    pg=Hm[OVAL,:2];pg=pg[np.isfinite(pg).all(1)];lo=pg.min(0)-.03;cs=.002;shape=tuple(np.ceil((pg.max(0)+.03-lo)/cs).astype(int)+1);Zt=depth(X,TF,lo,cs,shape);Zh=depth(P,F,lo,cs,shape)
    gx=np.stack(np.meshgrid(np.arange(shape[0]),np.arange(shape[1]),indexing='ij'),-1).reshape(-1,2)*cs+lo;gi,gd=poly(gx,pg);ring=gi&(gd<feather);Zt+=np.median((Zh.ravel()-Zt.ravel())[ring])
    ins,dd=poly(P[:,:2],pg);zh=bil(Zh,lo,cs,P[:,:2]);m=ins&(P[:,2]>=zh-.012);w=np.where(m,np.clip(dd/feather,0,1),0);w=w*w*(3-2*w);dz=np.clip(bil(Zt,lo,cs,P[:,:2])-zh,-.015,.04);P[:,2]+=w*dz
    put(j,bn,at['POSITION'],P);j['accessors'][at['POSITION']].update(min=P.min(0).tolist(),max=P.max(0).tolist());put(j,bn,at['NORMAL'],snorm(P,F));wr(path,j,bn)
    print(path,'face',int(m.sum()),'verts moved, depth change',f'{(w*dz)[m].min()*39.37:+.2f}..{(w*dz)[m].max()*39.37:+.2f}in','scale',round(sc,3));return run(path)
def teximg(j,bn,i):
    v=j['bufferViews'][j['images'][i]['bufferView']];return np.asarray(Image.open(io.BytesIO(bytes(bn[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]))).convert('RGB')).astype(np.float32)/255
def setview(j,bn,vi,data):
    d=[bytes(bn[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]) for v in j['bufferViews']];d[vi]=data;out=bytearray()
    for v,x in zip(j['bufferViews'],d):out+=b'\0'*(-len(out)%4);v['byteOffset']=len(out);v['byteLength']=len(x);out+=x
    return out
def setimg(j,bn,i,im,q=88):
    b=io.BytesIO();Image.fromarray((np.clip(im,0,1)*255+.5).astype(np.uint8)).save(b,'JPEG',quality=q,optimize=True);return setview(j,bn,j['images'][i]['bufferView'],b.getvalue())
def setacc(j,bn,i,x):
    a=j['accessors'][i];x=np.ascontiguousarray(x.astype(CT[a['componentType']]));j['bufferViews'][a['bufferView']].pop('byteStride',None);a.pop('byteOffset',None);a['count']=len(x);x2=x.reshape(len(x),-1);a.update(min=x2.min(0).tolist(),max=x2.max(0).tolist()) if 'min' in a else None;return setview(j,bn,a['bufferView'],x.tobytes())
def basecolor(j,bn,UV):
    im=teximg(j,bn,j['textures'][j['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['index']]['source']);S=np.array(im.shape[1::-1]);px=np.clip((UV*S).astype(int),0,S-1);return im,im[px[:,1],px[:,0]]
def pad(im,m):
    ix=ndimage.distance_transform_edt(~m,return_distances=False,return_indices=True);return im[ix[0],ix[1]]
def texels(UV,F,sz):
    Q=UV*sz;ti=Image.new('I',(sz,sz),-1);dr=ImageDraw.Draw(ti)
    for t,c in enumerate(Q[F]):dr.polygon([tuple(p) for p in c],fill=t,outline=t)
    T=np.asarray(ti);ys,xs=np.nonzero(T>=0);tt=T[ys,xs];A=Q[F[tt,0]];v0,v1,v2=Q[F[tt,1]]-A,Q[F[tt,2]]-A,np.c_[xs+.5,ys+.5]-A;d00,d01,d11,d20,d21=(v0*v0).sum(1),(v0*v1).sum(1),(v1*v1).sum(1),(v2*v0).sum(1),(v2*v1).sum(1);den=d00*d11-d01*d01;den=np.where(np.abs(den)<1e-12,1,den);b1,b2=(d11*d20-d01*d21)/den,(d00*d21-d01*d20)/den;bc=np.clip(np.c_[1-b1-b2,b1,b2],0,1);return T>=0,ys,xs,tt,bc/np.maximum(bc.sum(1,keepdims=True),1e-9)
def rebake(path,bake,high,concept,sz=2048):
    j,bn=rd(path);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);F=get(j,bn,pr['indices']).astype(np.int64).reshape(-1,3);UV=get(j,bn,at['TEXCOORD_0']);mt=j['materials'][0]['pbrMetallicRoughness'];ci,mi=[j['textures'][mt[k]['index']]['source'] for k in('baseColorTexture','metallicRoughnessTexture')];Nm,Jt,Wt=[get(j,bn,at[k]) for k in('NORMAL','JOINTS_0','WEIGHTS_0')]
    bj,bb=rd(bake);bp=bj['meshes'][0]['primitives'][0]['attributes'];Pb=get(bj,bb,bp['POSITION']);du,ix=cKDTree(get(bj,bb,bp['TEXCOORD_0'])).query(UV);O=Pb[ix];_,u0,inv=np.unique(np.round(P/1e-5).astype(np.int64),axis=0,return_index=True,return_inverse=True);xa=xatlas.Atlas();xa.add_mesh(P[u0].astype(np.float32),inv.ravel()[F].astype(np.uint32));po=xatlas.PackOptions();po.resolution=sz;po.padding=4;po.bilinear=True;xa.generate(pack_options=po);vm,F,UV=xa[0];F=F.astype(np.int64);vm=u0[vm];P,O,Nm,Jt,Wt=P[vm],O[vm],Nm[vm],Jt[vm],Wt[vm]
    hj,hb=rd(high);hp=hj['meshes'][0]['primitives'][0];Ph=get(hj,hb,hp['attributes']['POSITION']);Fh=get(hj,hb,hp['indices']).astype(np.int64).reshape(-1,3);UVh=get(hj,hb,hp['attributes']['TEXCOORD_0']);hm=hj['materials'][hp.get('material',0)]['pbrMetallicRoughness'];hc,hr=[teximg(hj,hb,hj['textures'][hm[k]['index']]['source']) for k in('baseColorTexture','metallicRoughnessTexture')]
    hsz=hc.shape[0];hm_=texels(UVh,Fh,hsz)[0];hc,hr=pad(hc,hm_),pad(hr,hm_);cA,cH=(Pb.min(0)+Pb.max(0))/2,(Ph.min(0)+Ph.max(0))/2;s_=np.ptp(Pb[:,1])/np.ptp(Ph[:,1]);sub=Pb[::max(1,len(Pb)//4000)];th=cKDTree(Ph);fl=min((1,-1),key=lambda f:th.query((sub-cA)*[f,1,f]/s_+cH)[0].mean());Oh=(O-cA)*[fl,1,fl]/s_+cH
    S5=np.concatenate(list(tsamp(np.c_[Ph,UVh,snorm(Ph,Fh)],Fh,.0006)));ts=cKDTree(S5[:,:3]);m,ys,xs,tt,bc=texels(UV,F,sz);X=(bc[:,:,None]*Oh[F[tt]]).sum(1);dd,k=ts.query(X,8,workers=-1);fn=np.cross(Oh[F[:,1]]-Oh[F[:,0]],Oh[F[:,2]]-Oh[F[:,0]])[tt];dt=(S5[k,5:]*fn[:,None]).sum(-1);sg=np.sign(np.median(dt[:,0]));dt*=sg;jj=np.argmax(dt>0,1);r_=np.arange(len(k));dd,k=dd[r_,jj],k[r_,jj];uv=S5[k,3:5];lo=.5/hsz;tc=bil(hc,lo,1/hsz,uv[:,::-1]);fo=fn*sg/np.maximum(np.linalg.norm(fn,axis=1,keepdims=True),1e-12)
    C4=np.asarray(Image.open(concept).convert('RGBA')).astype(np.float32)/255;iy,ix=np.nonzero(C4[...,3]>.5);x0,x1,y0,y1=ix.min(),ix.max(),iy.min(),iy.max();mn,mx=Oh.min(0),Oh.max(0);sm=lambda x:np.clip(x,0,1)**2*(3-2*np.clip(x,0,1));cs=.0006*s_;Xf=(bc[:,:,None]*P[F[tt]]).sum(1);g0=P.min(0)[:2]-.01;shape=tuple(np.ceil((P.max(0)[:2]+.01-g0)/cs).astype(int)+1);vis=Xf[:,2]>=bil(depth(P,F,g0,cs,shape),g0,cs,Xf[:,:2])-.005*s_;lum=lambda c:c[:,:3]@[.3,.59,.11];rng=np.random.default_rng(7);best=(-2,)
    for vz in[np.sign(np.corrcoef(Oh[:,0],P[:,0])[0,1])]:
        w=vis*sm((np.abs(fo[:,2])-.1)/.3);u=x0+((X[:,0]-mn[0]) if vz>0 else (mx[0]-X[:,0]))*(x1-x0)/(mx[0]-mn[0]);v=y0+(mx[1]-X[:,1])*(y1-y0)/(mx[1]-mn[1]);sel=rng.choice(np.nonzero(w>.8)[0],min(20000,int((w>.8).sum())),replace=False)
        for kk in(.97,.985,1,1.015,1.03):
            for dx in range(-8,9,2):
                for dy in range(-8,9,2):
                    uu,vv=((u[sel]-(x0+x1)/2)*kk+(x0+x1)/2+dx,(v[sel]-(y0+y1)/2)*kk+(y0+y1)/2+dy);sc=np.corrcoef(lum(bil(C4,0,1,np.c_[vv,uu]-.5)),lum(tc[sel]))[0,1];best=max(best,(sc,vz,kk,dx,dy,w,u,v),key=lambda b:b[0])
    sc,vz,kk,dx,dy,w,u,v=best;u,v=(u-(x0+x1)/2)*kk+(x0+x1)/2+dx,(v-(y0+y1)/2)*kk+(y0+y1)/2+dy;cc=bil(C4,0,1,np.c_[v,u]-.5);fit=(w>.9)&(cc[:,3]>.9);M=np.linalg.lstsq(np.c_[tc,np.ones(len(tc))][fit],cc[fit,:3],rcond=None)[0];tcc=np.clip(np.c_[tc,np.ones(len(tc))]@M,0,1)
    Hc,Wc=C4.shape[:2];vi=(w>.3)&(u>=0)&(v>=0)&(u<Wc-1)&(v<Hc-1);q=(np.round(v[vi]).astype(int),np.round(u[vi]).astype(int));acc=np.zeros((Hc,Wc,3));cnt=np.zeros((Hc,Wc));np.add.at(acc,q,tcc[vi]);np.add.at(cnt,q,1);tm=ndimage.binary_closing(cnt>0,iterations=3);ti=np.where(tm[...,None],pad(acc/np.maximum(cnt,1)[...,None],cnt>0),0)
    gr=lambda a:np.ascontiguousarray((np.clip(a@[.3,.59,.11],0,1)*255).astype(np.uint8));fw=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(gr(ti),gr(C4[...,:3]*C4[...,3:]),None);fw=np.clip(ndimage.gaussian_filter(fw,(14,14,0)),-40,40);fv=bil(fw,0,1,np.c_[v,u]-.5);cc=bil(C4,0,1,np.c_[v+fv[:,1],u+fv[:,0]]-.5);w=w*cc[:,3]
    col=np.zeros((sz,sz,3));col[ys,xs]=w[:,None]*cc[:,:3]+(1-w[:,None])*tcc;orm=np.ones_like(col);[bn:=setacc(j,bn,a_,x_) for a_,x_ in((at['POSITION'],P),(at['NORMAL'],Nm),(at['TEXCOORD_0'],UV),(at['JOINTS_0'],Jt),(at['WEIGHTS_0'],Wt),(pr['indices'],F.ravel()))];orm[ys,xs,1]=bil(hr,lo,1/hsz,uv[:,::-1])[:,1];orm[...,2]=0;bn=setimg(j,bn,ci,pad(col,m));bn=setimg(j,bn,mi,pad(orm,m));wr(path,j,bn)
    print(path,'rebake from',high,f'uv match {du.max():.1e}',f'new atlas {xa.chart_count} charts {xa.utilization*100:.0f}% used {len(P)} verts','flip' if fl<0 else 'no flip',f'fit {th.query((sub-cA)*[fl,1,fl]/s_+cH)[0].mean()*s_*39.37:.3f}in',len(S5),'samples',f'texel gap median {np.median(dd)*s_*39.37:.3f}in','| concept',['mirrored','direct'][int(vz>0)],f'corr {sc:.3f} scale {kk} shift {dx},{dy}px',f'projected {(w>.5).mean()*100:.0f}% of texels, warp median {np.median(np.linalg.norm(fv[w>.5],axis=1)):.1f}px p95 {np.quantile(np.linalg.norm(fv[w>.5],axis=1),.95):.1f}px','color match err',f'{np.abs(tc[fit]-cc[fit,:3]).mean():.3f}->{np.abs(tcc[fit]-cc[fit,:3]).mean():.3f}')
def hairback(path,back=.07):
    j,bn=rd(path);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);F=get(j,bn,pr['indices']).astype(np.int64).reshape(-1,3);sk,jn,names,ix,par,wp=skel(j);_,c=basecolor(j,bn,get(j,bn,at['TEXCOORD_0']))
    hc=np.median(c[(P[:,1]>P[:,1].max()-.04)&(np.abs(P[:,0])<.1)],0);hair=(np.linalg.norm(c-hc,axis=1)<.2)&(P[:,1]>wp[ix['Hips'],1]);sm=lambda x:np.clip(x,0,1)**2*(3-2*np.clip(x,0,1));ey,sy,sz=wp[ix['Head'],1],(wp[ix['LeftArm'],1]+wp[ix['RightArm'],1])/2,(wp[ix['LeftArm'],2]+wp[ix['RightArm'],2])/2
    ae=lambda sd:wp[ix[sd+'Hand']]+.1*(wp[ix[sd+'Hand']]-wp[ix[sd+'ForeArm']])/np.linalg.norm(wp[ix[sd+'Hand']]-wp[ix[sd+'ForeArm']]);da=np.min([seg(P,a_,b_) for sd in('Left','Right') for a_,b_ in((wp[ix[sd+'Arm']],wp[ix[sd+'ForeArm']]),(wp[ix[sd+'ForeArm']],wp[ix[sd+'Hand']]),(wp[ix[sd+'Hand']],ae(sd)))],0);hair=hair*sm((da-.045)/.02);dz=-back*hair*sm((ey-P[:,1])/(ey-sy))*sm((np.abs(P[:,0])-.06)/.05)*sm((P[:,2]-sz+.1)/.1);_,u0,inv=np.unique(np.round(P/1e-5).astype(np.int64),axis=0,return_index=True,return_inverse=True);inv=inv.ravel();Fw=inv[F];e=np.concatenate([Fw[:,[0,1]],Fw[:,[1,2]],Fw[:,[2,0]]]);L=sparse.coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(u0),len(u0))).tocsr();L.data[:]=1;dg=np.maximum(np.asarray(L.sum(1)).ravel(),1);d=dz[u0]
    for _ in range(7):d=.5*d+.5*(L@d)/dg
    P[:,2]+=d[inv];put(j,bn,at['POSITION'],P);j['accessors'][at['POSITION']].update(min=P.min(0).tolist(),max=P.max(0).tolist());put(j,bn,at['NORMAL'],snorm(P,F));wr(path,j,bn);r=run(path);j,bn=rd(path);Jt,Wt=get(j,bn,at['JOINTS_0']).astype(int),get(j,bn,at['WEIGHTS_0']);arm=np.isin(Jt,[ix[sd+b] for sd in('Left','Right') for b in('Arm','ForeArm','Hand')]);sp=ix['Spine2'];mv=(Wt*arm*hair[:,None]).sum(1);Wt=Wt-Wt*arm*hair[:,None];has=Jt==sp;k=np.where(has.any(1),has.argmax(1),Wt.argmin(1));o=np.arange(len(Jt));Jt[o,k]=np.where(mv>1e-4,sp,Jt[o,k]);Wt[o,k]+=mv
    put(j,bn,at['JOINTS_0'],Jt);put(j,bn,at['WEIGHTS_0'],Wt/np.maximum(Wt.sum(1,keepdims=True),1e-9));wr(path,j,bn);print(path,'hair',int(hair.sum()),'verts, moved back up to',f'{-d.min()*39.37:.1f}in,',int((mv>.05).sum()),'freed from arm bones');return r
def bones(path):
    if path.endswith('.json'):return {k:np.array(v) for k,v in json.load(open(path)).items()}
    j,bn=rdg(path);sk=j['skins'][0];jp={j['nodes'][i]['name']:np.linalg.inv(m.reshape(4,4).T)[:3,3] for i,m in zip(sk['joints'],get(j,bn,sk['inverseBindMatrices']))};return {k:jp.get(k,jp.get(v)) for k,v in UE.items()}
def normalize(path,tpl,amt={'Arm':1,'ForeArm':1,'UpLeg':1,'Leg':1,'Shoulder':.5,'spine':1}):
    j,bn=rd(path);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);F=get(j,bn,pr['indices']).astype(np.int64).reshape(-1,3);sk,jn,names,ix,par,wp=skel(j);T=bones(tpl);cur={n:wp[ix[n]] for n in UE};L=lambda D,a,b:np.linalg.norm(D[a]-D[b])
    ch=[('LeftFoot','LeftLeg'),('LeftLeg','LeftUpLeg'),('LeftUpLeg','Hips'),('Hips','Neck'),('Neck','Head')];k=sum(L(cur,a,b) for a,b in ch)/sum(L(T,a,b) for a,b in ch);end={'Arm':'ForeArm','ForeArm':'Hand','UpLeg':'Leg','Leg':'Foot','Shoulder':'Arm'};s=np.ones(len(jn))
    for sd in('Left','Right'):
        for b,e in end.items():s[ix[sd+b]]=1+amt[b]*(k*(L(T,'Left'+b,'Left'+e)+L(T,'Right'+b,'Right'+e))/2/L(cur,sd+b,sd+e)-1)
    sp=1+amt['spine']*(k*L(T,'Hips','Neck')/L(cur,'Hips','Neck')-1);s[[ix[n] for n in('Hips','Spine','Spine1','Spine2')]]=sp
    kids={b:[c for c in range(len(jn)) if par[c]==b] for b in range(len(jn))};main=lambda b:kids[b][0] if len(kids[b])==1 else ix['Spine'] if names[b]=='Hips' else ix['Neck'] if names[b]=='Spine2' else None;S=np.repeat(np.eye(3)[None],len(jn),0)
    for b in range(len(jn)):
        m=main(b)
        if m is not None:d=(wp[m]-wp[b])/np.linalg.norm(wp[m]-wp[b]);S[b]+=(s[b]-1)*np.outer(d,d)
    Jn=wp.copy()
    for c in range(len(jn)):Jn[c]=Jn[par[c]]+S[par[c]]@(wp[c]-wp[par[c]]) if par[c]>=0 else wp[c]
    J=get(j,bn,at['JOINTS_0']).astype(int);Wv=get(j,bn,at['WEIGHTS_0']);Q=sum(Wv[:,i:i+1]*(Jn[J[:,i]]+np.einsum('nij,nj->ni',S[J[:,i]],P-wp[J[:,i]])) for i in range(4));dy=np.array([0,-Q[:,1].min(),0]);Q+=dy;Jn+=dy
    put(j,bn,at['POSITION'],Q);j['accessors'][at['POSITION']].update(min=Q.min(0).tolist(),max=Q.max(0).tolist());put(j,bn,at['NORMAL'],snorm(Q,F));setskel(j,bn,sk,jn,par,Jn);wr(path,j,bn)
    print(path,'normalized',' '.join(f'{names[b]} x{s[b]:.2f}' for b in range(len(jn)) if abs(s[b]-1)>.005 and not names[b].startswith(('Spine','Right'))))
def seg(p,a,b):
    d=b-a;t=np.clip(((p-a)@d)/max(d@d,1e-12),0,1);return np.linalg.norm(p-(a+t[:,None]*d),axis=1)
def run(path):
    j,bn=rd(path);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);F=get(j,bn,pr['indices']).astype(np.int64).reshape(-1,3);sk,jn,names,ix,par,wp=skel(j)
    lo=P.min(0)-3*H;dim=np.ceil((P.max(0)-lo)/H).astype(int)+4;sh=np.zeros(dim,bool)
    for q in tsamp(P,F,.5*H):g=((q-lo)/H).astype(int);sh[g[:,0],g[:,1],g[:,2]]=True
    so=ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_dilation(sh)))|sh;N=int(so.sum());idn=-np.ones(dim,np.int64);idn[so]=np.arange(N);vx=lambda p:np.clip(((np.atleast_2d(p)-lo)/H).astype(int),0,dim-1);ni=ndimage.distance_transform_edt(~so,return_distances=False,return_indices=True);sv=lambda g:idn[ni[0][g[:,0],g[:,1],g[:,2]],ni[1][g[:,0],g[:,1],g[:,2]],ni[2][g[:,0],g[:,1],g[:,2]]];w0=wp.copy()
    def cen(p,axis,r):
        g=vx(p)[0];sl=[slice(None)]*3;sl[axis]=g[axis];m=so[tuple(sl)];o=[a for a in range(3) if a!=axis];yy,xx=np.nonzero(m);pts=(np.stack([yy,xx],1)+.5)*H+lo[o];near=np.linalg.norm(pts-p[o],axis=1)<r
        if near.sum()<4:return p
        lab,_=ndimage.label(m);c=np.clip(((p[o]-lo[o])/H).astype(int),0,np.array(m.shape)-1);l0=lab[c[0],c[1]] or np.bincount(lab[yy[near],xx[near]]).argmax();keep=(lab[yy,xx]==l0)&near;q=p.copy();q[o]=pts[keep].mean(0) if keep.sum()>3 else q[o];return q
    for s in 'Left','Right':
        u,k,f=ix[s+'UpLeg'],ix[s+'Leg'],ix[s+'Foot'];wp[k]=cen(wp[k],1,.1);wp[u,0]=wp[k,0];wp[f,[0,2]]=cen(wp[f]+np.array([0,.03,0]),1,.09)[[0,2]]
        e,w=ix[s+'ForeArm'],ix[s+'Hand'];ax=0;wp[e]=cen(wp[e],ax,.09);wp[w]=cen(wp[w],ax,.08)
    nk,hd=ix['Neck'],ix['Head'];wp[hd,0]=wp[nk,0];wp[hd,2]=wp[nk,2]+.2*(wp[hd,1]-wp[nk,1])
    G=[];W=[]
    for d in [(a,b,c) for a in(-1,0,1) for b in(-1,0,1) for c in(-1,0,1) if (a,b,c)>(0,0,0)]:
        s1=tuple(slice(max(0,-x),dim[i]-max(0,x)) for i,x in enumerate(d));s2=tuple(slice(max(0,x),dim[i]-max(0,-x)) for i,x in enumerate(d));m=so[s1]&so[s2];G+=[np.stack([idn[s1][m],idn[s2][m]],1)];W+=[np.full(m.sum(),H*np.sqrt(sum(abs(x) for x in d)))]
    G=np.concatenate(G);W=np.concatenate(W);gr=sparse.coo_matrix((W,(G[:,0],G[:,1])),shape=(N,N)).tocsr()
    ch={k:[c for c in range(len(jn)) if par[c]==k] for k in range(len(jn))};top=P[:,1].max();segs=[]
    for k,n in enumerate(names):
        kids=ch[k];c=kids[0] if len(kids)==1 else ix.get('Spine') if n=='Hips' else ix.get('Neck') if n=='Spine2' else None
        if n=='Head':b=np.array([wp[k,0],wp[k,1]+.8*(top-wp[k,1]),wp[k,2]])
        elif n.endswith('Hand'):d=wp[k]-wp[par[k]];d/=np.linalg.norm(d);vv=P[np.linalg.norm(P-wp[k],axis=1)<.2];b=wp[k]+d*max(.03,((vv-wp[k])@d).max()*.8)
        elif n.endswith('ToeBase'):b=wp[k]+np.array([0,0,max(.02,P[np.linalg.norm(P[:,[0,1]]-wp[k,[0,1]],axis=1)<.07][:,2].max()-wp[k,2])*.8])
        else:b=wp[c]
        segs.append([(wp[k],b)]+([(wp[k],(wp[ix['LeftUpLeg']]+wp[ix['RightUpLeg']])/2-np.array([0,.04,0]))] if n=='Hips' else []))
    cv=np.argwhere(so)*H+lo;D=np.zeros((len(jn),N))
    for k in range(len(jn)):
        sd=np.unique(np.concatenate([sv(vx(a+(b-a)*np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/(.5*H))+1))[:,None])) for a,b in segs[k]]))
        D[k]=dijkstra(gr,directed=False,indices=sd,min_only=True)
    vi=sv(vx(P))
    g=D[:,vi].T;g[~np.isfinite(g)]=9
    lim=[k for k,n in enumerate(names) if n.endswith(('Shoulder','Arm','UpLeg')) and 'Fore' not in n]
    def rad(k):
        a,b=segs[k][0];m=(a+b)/2;d=b-a;d/=np.linalg.norm(d);rel=cv-m;near=(np.abs(rel@d)<H)&(np.linalg.norm(rel-np.outer(rel@d,d),axis=1)<.12);return max(.03,np.sqrt(near.sum()*H*H/(2*np.pi)))
    R={k:rad(k) for k in lim};[R.__setitem__(ix[s+'Shoulder'],R[ix[s+'Arm']]*1.3) for s in('Left','Right')]
    cap=np.ones_like(g)
    def rloc(k):
        a,b=segs[k][0];ax=int(np.argmax(np.abs(b-a)));lo_i,hi_i=sorted([vx(a)[0,ax],vx(b)[0,ax]]);out=np.full(dim[ax],R[k]);o=[i for i in range(3) if i!=ax]
        for i in range(max(0,lo_i-7),min(dim[ax],hi_i+8)):
            t=np.clip((lo[ax]+(i+.5)*H-a[ax])/((b-a)[ax] or 1e-9),0,1);c=vx(a+(b-a)*t)[0][o];sl=[slice(None)]*3;sl[ax]=i;m=so[tuple(sl)]
            if m[c[0],c[1]]:lab,_=ndimage.label(m);out[i]=np.sqrt((lab==lab[c[0],c[1]]).sum()*H*H/np.pi)
        return np.clip(out,R[k],2*R[k])[vx(P)[:,ax]]
    for k in lim:dd=np.min([seg(P,a,b) for a,b in segs[k]],0);rl=rloc(k) if not names[k].endswith('Shoulder') else R[k];f1,f2=(1.6,.4) if names[k].endswith('Arm') else (2.2,.85);cap[:,k]=np.clip((f1*rl-dd)/(f2*rl),0,1)
    for s,sg in(('Left',1),('Right',-1)):
        k=ix[s+'Arm'];a,b=segs[k][0];t=np.clip(((P-a)@((b-a)/np.linalg.norm(b-a))+.01)/.05,0,1);cap[:,k]*=t*t*(3-2*t);c=vx(np.array([wp[ix['Spine2'],0],a[1]-.12,wp[ix['Spine2'],2]]))[0];lab,_=ndimage.label(so[:,c[1],:]);xs,zs=(np.nonzero(lab==lab[c[0],c[2]])+np.array([[.5],[.5]]))*H+lo[[0,2]][:,None];xs=xs[np.abs(zs-wp[ix['Spine2'],2])<.12];xt=sg*(xs.max() if sg>0 else xs.min());d=(b-a)/np.linalg.norm(b-a);dn=d[1]*d-np.array([0,1,0]);dn/=np.linalg.norm(dn)
        bl=np.clip(((P-a)@dn-R[k])/.03,0,1);la=np.clip((sg*P[:,0]-xt+.01)/.04,0,1);cap[:,k]*=1-bl*(1-la*la*(3-2*la))
    cy=(wp[ix['LeftUpLeg'],1]+wp[ix['RightUpLeg'],1])/2-.04;g[:,ix['Hips']]+=.3*np.clip((cy-P[:,1])/.06,0,1)*np.clip(2*np.maximum(cap[:,ix['LeftUpLeg']],cap[:,ix['RightUpLeg']])-1,0,1)
    adj=[{k,par[k],*ch[k]}-{-1} for k in range(len(jn))]
    def wts(gg,ok):
        gg=np.where(ok,gg,1e9);dm=gg.argmin(1);al=np.zeros_like(gg,bool)
        for k in range(len(jn)):al[np.ix_(dm==k,list(adj[k]))]=True
        x=np.where(al,np.exp(-(gg-gg.min(1,keepdims=True))/SIG),0);return x/x.sum(1,keepdims=True)
    wf=wts(g,cap>0);rig=np.ones_like(cap,bool);rig[:,lim]=cap[:,lim]>=1;wr_=wts(g,rig);c=(wf*cap).sum(1,keepdims=True);w=c*wf+(1-c)*wr_
    hd,nk,s2=ix['Head'],ix['Neck'],ix['Spine2'];t=np.clip((wp[nk,1]-P[:,1])/.25,0,1);t=t*t*(3-2*t)*.8;mv=w[:,hd]*t;w[:,hd]-=mv;w[:,s2]+=mv
    _,u0,inv=np.unique(np.round(P/1e-5).astype(np.int64),axis=0,return_index=True,return_inverse=True);inv=inv.ravel();Fw=inv[F];w=w[u0];e=np.concatenate([Fw[:,[0,1]],Fw[:,[1,2]],Fw[:,[2,0]]]);L=sparse.coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(u0),len(u0))).tocsr();L.data[:]=1;dg=np.asarray(L.sum(1)).ravel()
    for _ in range(2):w=.5*w+.5*(L@w)/np.maximum(dg,1)[:,None]
    w=w[inv]
    o=np.argsort(-w,1)[:,:4];v=np.take_along_axis(w,o,1);v[v<.01]=0;v/=v.sum(1,keepdims=True);o=np.where(v>0,o,0)
    put(j,bn,at['JOINTS_0'],o);put(j,bn,at['WEIGHTS_0'],v)
    e0=np.abs(get(j,bn,sk['inverseBindMatrices'])[:,12:15]+w0).max();e0>1e-4 and sys.exit(f'unexpected bind matrices ({e0:.4f})');setskel(j,bn,sk,jn,par,wp);wr(path,j,bn)
    print(path,'solid',N,'moved',', '.join(f'{names[k]} {np.linalg.norm(wp[k]-w0[k])*39.37:.1f}in' for k in range(len(jn)) if np.linalg.norm(wp[k]-w0[k])>.005),'| max-weight median',f'{np.median(v[:,0]):.2f}',f'q25 {np.quantile(v[:,0],.25):.2f}')
    return names,wp
def graft(src,rig,out,tpl=None,q=86,px=2048):
    j,bn=rd(src);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);Nm=get(j,bn,at['NORMAL']);UV=get(j,bn,at['TEXCOORD_0']);F=get(j,bn,pr['indices']).astype(np.uint32).ravel()
    rj,rb=rd(rig);RP=get(rj,rb,rj['meshes'][0]['primitives'][0]['attributes']['POSITION']);mn,mx=RP.min(0),RP.max(0);s=(mx[1]-mn[1])/np.ptp(P[:,1]);ref=RP[::max(1,len(RP)//3000)];fit=[]
    for fl in(1,-1):
        Q=P*np.array([fl,1,fl])*s;Q+=(mn+mx)/2-(Q.min(0)+Q.max(0))/2;Q[:,1]+=mn[1]-Q[:,1].min();sub=Q[::max(1,len(Q)//3000)];fit.append((np.sqrt(((sub[:,None]-ref[None])**2).sum(2)).min(1).mean(),fl,Q))
    err,fl,P=min(fit,key=lambda x:x[0]);_,u0,inv=np.unique(np.c_[np.round(P/1e-5),np.round(UV/1e-6)].astype(np.int64),axis=0,return_index=True,return_inverse=True);F=inv.ravel()[F].reshape(-1,3);P,UV=P[u0],UV[u0];F=F[(F[:,0]!=F[:,1])&(F[:,1]!=F[:,2])&(F[:,0]!=F[:,2])];Nm=snorm(P,F);F=F.astype(np.uint32).ravel();rk=rj['skins'][0]['joints'];nm={o:i+1 for i,o in enumerate(rk)};wp={}
    def wpos(o,base):wp[o]=base+np.array(rj['nodes'][o].get('translation',[0,0,0]));[wpos(c,wp[o]) for c in rj['nodes'][o].get('children',[]) if c in nm]
    roots=[o for o in rk if not any(o in rj['nodes'][x].get('children',[]) for x in rk)];[wpos(o,np.zeros(3)) for o in roots]
    mt=j['materials'][pr.get('material',0)]['pbrMetallicRoughness'];tx=lambda k:j['textures'][mt[k]['index']]['source']
    def img(i):
        v=j['bufferViews'][j['images'][i]['bufferView']];im=Image.open(io.BytesIO(bytes(bn[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]))).convert('RGB');im=im.resize((px,px),Image.LANCZOS) if im.width>px else im;b=io.BytesIO();im.save(b,'JPEG',quality=q,optimize=True);return b.getvalue()
    n=len(P);ib=np.zeros((len(rk),16));ib[:,[0,5,10,15]]=1;ib[:,12:15]=-np.array([wp[o] for o in rk])
    parts=[P.astype(np.float32),Nm.astype(np.float32),UV.astype(np.float32),np.zeros((n,4),np.uint16),np.zeros((n,4),np.float32),F,ib.astype(np.float32),img(tx('baseColorTexture')),img(tx('metallicRoughnessTexture'))];out_b=bytearray();views=[]
    for x in parts:out_b+=b'\0'*(-len(out_b)%4);views.append({'buffer':0,'byteOffset':len(out_b),'byteLength':len(x if isinstance(x,bytes) else x.tobytes())});out_b+=x if isinstance(x,bytes) else x.tobytes()
    acc=[{'bufferView':0,'componentType':5126,'count':n,'type':'VEC3','min':P.min(0).tolist(),'max':P.max(0).tolist()},{'bufferView':1,'componentType':5126,'count':n,'type':'VEC3'},{'bufferView':2,'componentType':5126,'count':n,'type':'VEC2'},{'bufferView':3,'componentType':5123,'count':n,'type':'VEC4'},{'bufferView':4,'componentType':5126,'count':n,'type':'VEC4'},{'bufferView':5,'componentType':5125,'count':len(F),'type':'SCALAR'},{'bufferView':6,'componentType':5126,'count':len(rk),'type':'MAT4'}]
    name=next(x['name'] for x in rj['nodes'] if 'mesh' in x);sk=[{'name':rj['nodes'][o]['name'],'translation':rj['nodes'][o].get('translation',[0,0,0])}|({'children':[nm[c] for c in rj['nodes'][o]['children'] if c in nm]} if rj['nodes'][o].get('children') else {}) for o in rk]
    nj={'asset':{'version':'2.0','generator':'Amni-Companion reskin'},'scene':0,'scenes':[{'nodes':[0]+[nm[o] for o in roots]}],'nodes':[{'name':name,'mesh':0,'skin':0}]+sk,'skins':[{'joints':list(range(1,len(rk)+1)),'inverseBindMatrices':6,'skeleton':nm[roots[0]]}],'meshes':[{'name':name,'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2,'JOINTS_0':3,'WEIGHTS_0':4},'indices':5,'material':0}]}],'materials':[{'name':name,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicRoughnessTexture':{'index':1},'metallicFactor':1,'roughnessFactor':1},'occlusionTexture':{'index':1},'doubleSided':True}],'textures':[{'sampler':0,'source':0},{'sampler':0,'source':1}],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}],'images':[{'bufferView':7,'mimeType':'image/jpeg'},{'bufferView':8,'mimeType':'image/jpeg'}],'accessors':acc,'bufferViews':views,'buffers':[{'byteLength':len(out_b)}]}
    wr(out,nj,out_b);print(out,'grafted',len(F)//3,'tris',n,'verts','fit',f'{err*39.37:.2f}in','flipped' if fl<0 else '');r0=run(out);return (normalize(out,tpl),run(out))[1] if tpl else r0
if __name__=='__main__':{'--graft':graft,'--face':face,'--facepack':facepack,'--hairback':hairback,'--rebake':rebake}.get(sys.argv[1],lambda *a:[run(p) for p in sys.argv[1:]])(*sys.argv[2:])
