import io,json,os,struct,subprocess,sys,xatlas,numpy as np
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw
from scipy import ndimage
from skimage.measure import marching_cubes
import fast_simplification
from scipy.spatial.transform import Rotation as Rr
CT={5126:np.float32,5123:np.uint16,5121:np.uint8,5125:np.uint32}
def rd(path):
    b=open(path,'rb').read();n=struct.unpack('<I',b[12:16])[0];j=json.loads(b[20:20+n]);o=20+n;m=struct.unpack('<I',b[o:o+4])[0];return j,bytearray(b[o+8:o+8+m])
def loc(j,i):
    a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];t=np.dtype(CT[a['componentType']]);c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];return v.get('byteOffset',0)+a.get('byteOffset',0),v.get('byteStride',0) or t.itemsize*c,t,c,a['count']
def get(j,bn,i):
    o,s,t,c,n=loc(j,i);return np.ndarray((n,c),t,bn,o,(s,t.itemsize)).astype(np.float64)
def snorm(P,F):
    pk=np.unique(np.round(P/1e-5).astype(np.int64),axis=0,return_inverse=True)[1].ravel();fn=np.cross(P[F[:,1]]-P[F[:,0]],P[F[:,2]]-P[F[:,0]]);a=np.zeros((pk.max()+1,3));[np.add.at(a,pk[F[:,c]],fn) for c in range(3)];n=a[pk];return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
def rdg(path):
    if path.endswith('.glb'):return rd(path)
    j=json.load(open(path));return j,bytearray(open(os.path.join(os.path.dirname(path),j['buffers'][0]['uri']),'rb').read())
def tsamp(P,F,step):
    A,B,C=P[F[:,0]],P[F[:,1]],P[F[:,2]];K=np.clip(np.ceil(np.maximum.reduce([np.linalg.norm((B-A)[:,:3],axis=1),np.linalg.norm((C-A)[:,:3],axis=1),np.linalg.norm((C-B)[:,:3],axis=1)])/step),1,40).astype(int)
    for k in np.unique(K):m=K==k;u,v=np.meshgrid(np.arange(k+1),np.arange(k+1));sl=(u+v)<=k;u,v=u[sl]/k,v[sl]/k;yield (A[m][:,None]+(B[m]-A[m])[:,None]*u[None,:,None]+(C[m]-A[m])[:,None]*v[None,:,None]).reshape(-1,P.shape[1])
def pad(im,m):
    ix=ndimage.distance_transform_edt(~m,return_distances=False,return_indices=True);return im[ix[0],ix[1]]
def texels(UV,F,sz):
    Q=UV*sz;ti=Image.new('I',(sz,sz),-1);dr=ImageDraw.Draw(ti)
    for t,c in enumerate(Q[F]):dr.polygon([tuple(p) for p in c],fill=t,outline=t)
    T=np.asarray(ti);ys,xs=np.nonzero(T>=0);tt=T[ys,xs];A=Q[F[tt,0]];v0,v1,v2=Q[F[tt,1]]-A,Q[F[tt,2]]-A,np.c_[xs+.5,ys+.5]-A;d00,d01,d11,d20,d21=(v0*v0).sum(1),(v0*v1).sum(1),(v1*v1).sum(1),(v2*v0).sum(1),(v2*v1).sum(1);den=d00*d11-d01*d01;den=np.where(np.abs(den)<1e-12,1,den);b1,b2=(d11*d20-d01*d21)/den,(d00*d21-d01*d20)/den;bc=np.clip(np.c_[1-b1-b2,b1,b2],0,1);return T>=0,ys,xs,tt,bc/np.maximum(bc.sum(1,keepdims=True),1e-9)
def mat(n):
    T=np.eye(4);T[:3,:3]=Rr.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()*np.array(n.get('scale',[1,1,1]));T[:3,3]=n.get('translation',[0,0,0]);return T
def tpl(path):
    j,bn=rdg(path);N=j['nodes'];par={c:i for i,n in enumerate(N) for c in n.get('children',[])};wm=lambda i:wm(par[i])@mat(N[i]) if i in par else mat(N[i]);sk=j['skins'][0];jn=sk['joints'];names=[N[i]['name'] for i in jn]
    texs={}
    for m in j['materials']:
        t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture');u=j['images'][j['textures'][t['index']]['source']]['uri'] if t else None;texs[m['name']]=np.asarray(Image.open(os.path.join(os.path.dirname(path),u)).convert('RGB'),np.float32)/255 if u else np.full((4,4,3),[.78,.6,.5],np.float32)
    parts=[]
    for i,n in enumerate(N):
        if 'mesh' not in n:continue
        for p in j['meshes'][n['mesh']]['primitives']:
            a=p['attributes'];parts.append(dict(name=n['name'],mat=j['materials'][p['material']]['name'],P=get(j,bn,a['POSITION']),N=get(j,bn,a['NORMAL']),UV=get(j,bn,a['TEXCOORD_0']),F=get(j,bn,p['indices']).astype(np.int64).reshape(-1,3),J=get(j,bn,a['JOINTS_0']).astype(int),W=get(j,bn,a['WEIGHTS_0'])))
    sole=min(p['P'][:,1].min() for p in parts)
    return dict(sole=sole,names=names,par=[names.index(N[par[i]]['name']) if i in par and N[par[i]]['name'] in names else -1 for i in jn],W=np.array([wm(i) for i in jn]),parts=parts,tex=texs)
def render(P,F,UV,tex,x0,y0,mpp,shape):
    h,w=shape;Z=np.full((h,w),-np.inf);C=np.zeros((h,w,3),np.float32)
    for q in tsamp(np.c_[P,UV],F,.5*mpp):
        c=((q[:,0]-x0)/mpp).astype(int);r=((y0-q[:,1])/mpp).astype(int);ok=(c>=0)&(c<w)&(r>=0)&(r<h)
        if not ok.any():continue
        c,r,q=c[ok],r[ok],q[ok];o=np.lexsort((q[:,2],r*w+c));c,r,q=c[o],r[o],q[o];k=np.r_[(r*w+c)[1:]!=(r*w+c)[:-1],True];c,r,q=c[k],r[k],q[k];nb=q[:,2]>Z[r,c];c,r,q=c[nb],r[nb],q[nb];Z[r,c]=q[:,2]
        if tex is not None:th,tw=tex.shape[:2];C[r,c]=tex[np.clip((q[:,4]%1*th).astype(int),0,th-1),np.clip((q[:,3]%1*tw).astype(int),0,tw-1)]*(q[:,5:6] if q.shape[1]>5 else 1)
    return C,np.isfinite(Z),Z
def frame(t,size=1200,fill=.82):
    P=np.concatenate([p['P'] for p in t['parts']]);lo,hi=P.min(0),P.max(0);mpp=(hi[1]-lo[1])/(fill*size);return (lo[0]+hi[0])/2-size/2*mpp,hi[1]+(1-fill)/2*size*mpp,mpp
def look(t,png,size=1200):
    x0,y0,mpp=frame(t,size);img=np.full((size,size,3),.5,np.float32);Zb=np.full((size,size),-np.inf);al=np.zeros((size,size),bool)
    for p in t['parts']:
        C,A,Z=render(p['P'],p['F'],p['UV'],t['tex'][p['mat']],x0,y0,mpp,(size,size));m=A&(Z>Zb);img[m]=C[m];Zb[m]=Z[m];al|=A
    Image.fromarray(np.dstack([(img*255).astype(np.uint8),(al*255).astype(np.uint8)])).save(png);return x0,y0,mpp
def analyze(png,out):
    subprocess.run(['node',os.path.join(os.path.dirname(os.path.abspath(__file__)),'analyze.mjs'),png,out],check=True);return json.load(open(out))
def marks(d,tf=None):
    W,H=d['w'],d['h'];P=np.array([[q['x']*W,q['y']*H] for q in d['pose']]);F=np.array([[q['x']*W,q['y']*H] for q in d['face']]) if d.get('face') else None
    if tf is None:return P,F
    x0,y0,mpp=tf;f=lambda a:np.c_[x0+a[:,0]*mpp,y0-a[:,1]*mpp];return f(P),f(F) if F is not None else None
def tomet(d,alpha,hgt,top):
    P,F=marks(d);sole=np.nonzero(alpha.any(1))[0].max()+1;r10,r152=F[10,1],F[152,1];rt=r10-top*(r152-r10);m=hgt/(sole-rt);cx=(P[23,0]+P[24,0])/2;f=lambda a:np.c_[(a[:,0]-cx)*m,(sole-a[:,1])*m];return f(P),f(F),(cx,sole,m)
def measure(P,F):
    L=lambda a,b:np.linalg.norm(P[a]-P[b]);ang=lambda a,b:np.arctan2(*(P[b]-P[a])[::-1])
    return dict(ua=(L(11,13)+L(12,14))/2,fa=(L(13,15)+L(14,16))/2,hand=(L(15,19)+L(16,20)+L(15,17)+L(16,18))/4,th=(L(23,25)+L(24,26))/2,sh=(L(25,27)+L(26,28))/2,shw=L(11,12),hipw=L(23,24),torso=np.linalg.norm((P[11]+P[12])/2-(P[23]+P[24])/2),neck=((P[11]+P[12])/2)[1]-(F[1,1]),ankle=(P[27,1]+P[28,1])/2,facew=np.linalg.norm(F[234]-F[454]),faceh=np.linalg.norm(F[10]-F[152]),a_ua=(ang(11,13),ang(12,14)),a_fa=(ang(13,15),ang(14,16)),a_th=(ang(23,25),ang(24,26)),a_sh=(ang(25,27),ang(26,28)))
def rz(a):
    c,s=np.cos(a),np.sin(a);return np.array([[c,-s,0],[s,c,0],[0,0,1.]])
def wrap(a):return (a+np.pi)%(2*np.pi)-np.pi
def deform(T,mc,mt,glob,blend=1.,girth=None):
    nm,par,Wm=T['names'],T['par'],T['W'];h=Wm[:,:3,3];ix={n:k for k,n in enumerate(nm)};r=lambda k,cl=(.7,1.45):glob*np.clip(mc[k]/mt[k]/glob,*cl)**(blend if k in('ua','fa','hand') else 1);dz=lambda w:glob*(w/glob)**.6
    rh,rs,rt,rn=r('hipw'),r('shw'),r('torso'),r('neck',(.8,1.25));rhd=glob*np.clip(np.sqrt(mc['facew']*mc['faceh']/mt['facew']/mt['faceh'])/glob,.8,1.3);gw=girth or {}
    L=np.repeat(np.eye(3)[None],len(nm),0);R=np.repeat(np.eye(3)[None],len(nm),0);H=h.copy();A=np.zeros((len(nm),3,4))
    for k,n in enumerate(nm):
        p=par[k];H[k]=A[p][:,:3]@h[k]+A[p][:,3] if p>=0 else h[k];side=0 if n.endswith('_l') else 1;base=n[:-2] if n[-2:] in('_l','_r') else n;fing=any(n.startswith(f) for f in('index','middle','ring','pinky','thumb'))
        if n=='root':pass
        elif n in('pelvis','spine_01','spine_02','spine_03'):t={'pelvis':0,'spine_01':.33,'spine_02':.67,'spine_03':1}[n];w=gw.get(n,(1-t)*rh+t*rs);L[k]=np.diag([w,rt,dz(w)])
        elif n=='neck_01':L[k]=np.diag([rhd,rn,rhd])
        elif n=='Head':L[k]=rhd*np.eye(3)
        elif base=='clavicle':u=ix['upperarm'+n[-2:]];tx=rs*h[u,0];sx=(tx-H[k,0])/(h[u,0]-h[k,0]);L[k]=np.diag([sx,rt,dz(rs)])
        elif base in('upperarm','lowerarm','thigh','calf'):
            c={'upperarm':'lowerarm','lowerarm':'hand','thigh':'calf','calf':'foot'}[base]+n[-2:];d=h[ix[c]]-h[k];d/=np.linalg.norm(d);key={'upperarm':'ua','lowerarm':'fa','thigh':'th','calf':'sh'}[base];s=r(key);g=gw.get(n,glob if base in('upperarm','lowerarm') else glob*(rh/glob)**.5)
            R[k]=rz(wrap(mc['a_'+key][side]-mt['a_'+key][side]));L[k]=R[k]@(g*np.eye(3)+(s-g)*np.outer(d,d))
        elif base=='hand' or fing:R[k]=R[ix['lowerarm'+n[-2:]]];L[k]=R[k]*r('hand',(.75,1.3))
        elif base in('foot','ball','ball_leaf'):d0=h[ix['foot'+n[-2:]],1]-T['sole'];fy=np.clip((glob*d0+mc['ankle']-glob*mt['ankle'])/d0,.8,2.5);fx=gw.get('foot',glob);L[k]=np.diag([fx,fy,glob*(fx/glob)**.7])
        A[k][:,:3]=L[k];A[k][:,3]=H[k]-L[k]@h[k]
    out=[]
    for p in T['parts']:
        X=np.einsum('vkij,vj->vki',A[p['J']][...,:3],p['P'])+A[p['J']][...,3];X=(X*p['W'][...,None]).sum(1)/np.maximum(p['W'].sum(1,keepdims=True),1e-9);out.append(X)
    sole=min(X[:,1].min() for X in out);[X.__setitem__((slice(None),1),X[:,1]-sole) for X in out];H[:,1]-=sole;A[:,1,3]-=sole;T['A']=A
    return out,H,R
def sil(Xs,T,cm,shape,skip=('Eyebrows',)):
    cx,sole,m=cm;al=np.zeros(shape,bool);Zb=np.full(shape,-np.inf)
    for X,p in zip(Xs,T['parts']):
        if p['name'] in skip:continue
        _,A,Z=render(X,p['F'],np.zeros((len(X),2)),None,-cx*m,sole*m,m,shape);al|=A;Zb=np.maximum(Zb,Z)
    return al,Zb
LIMB={'upperarm':'lowerarm','lowerarm':'hand','thigh':'calf','calf':'foot'}
def march(ok,c,n,dmax):
    d=np.arange(int(dmax));q=np.rint(c[:,None,:]+d[None,:,None]*n[:,None,:]).astype(int);h,w=ok.shape;inb=(q[...,0]>=0)&(q[...,0]<w)&(q[...,1]>=0)&(q[...,1]<h);v=np.zeros(q.shape[:2],bool);v[inb]=ok[q[...,1][inb],q[...,0][inb]];out=~v;i=np.where(out.any(1),out.argmax(1),len(d)-1);e=q[np.arange(len(c)),i];return i.astype(float),e,inb[np.arange(len(c)),i]
def profiles(T,H,fit,body,bg,cm,step=3.):
    cx,sole,m=cm;tp=lambda X:np.stack([X[...,0]/m+cx,sole-X[...,1]/m],-1);nm=T['names'];ix={n:k for k,n in enumerate(nm)};G={}
    def ratio(c,nv,dmax):
        r=[]
        for sg in(1,-1):
            df,_,_=march(fit,c,sg*nv,dmax);dc,e,inb=march(body,c,sg*nv,dmax);ok=inb&bg[np.clip(e[:,1],0,bg.shape[0]-1),np.clip(e[:,0],0,bg.shape[1]-1)]&(df>2)&(dc>2)&(df<dmax-1);r.append(np.where(ok,dc/np.maximum(df,1),np.nan))
        return np.array(r)
    def smooth(g,hi=1.5):
        g=g.copy();i=np.arange(len(g));v=np.isfinite(g);g=np.interp(i,i[v],g[v]) if v.any() else np.ones(len(g));return np.clip(ndimage.gaussian_filter1d(g,2,mode='nearest'),.72,hi)
    for n in nm:
        b=n[:-2]
        if b not in LIMB or n[-2:] not in('_l','_r'):continue
        a,e=tp(H[ix[n]]),tp(H[ix[LIMB[b]+n[-2:]]]);L=np.linalg.norm(e-a);t=np.linspace(0,1,max(4,int(L/step)));c=a+t[:,None]*(e-a);d=(e-a)/L;nv=np.repeat(np.array([[-d[1],d[0]]]),len(t),0);r=ratio(c,nv,.9*L if b in('upperarm','lowerarm') else .6*L);G[n]=(t,smooth(np.nanmean(r,0),1.9 if b in('calf','lowerarm') else 1.5) if np.isfinite(r).any() else np.ones(len(t)),None)
    a,e=tp(H[ix['pelvis']]),tp(H[ix['spine_03']]);crotch=int(a[1]);col=int(round(cx))
    while crotch<fit.shape[0]-1 and fit[crotch,col]:crotch+=1
    rows=np.arange(int(e[1]),crotch);c=np.c_[np.interp(rows,[e[1],a[1]],[e[0],a[0]]),rows];r=ratio(c,np.repeat(np.array([[1.,0]]),len(rows),0),.45*fit.shape[1]/2)
    G['torso']=(rows,smooth(r[0]),smooth(r[1]))
    return G
def swell(Xs,T,H,G,cm,dy=0.):
    cx,sole,m=cm;nm=T['names'];ix={n:k for k,n in enumerate(nm)};lk={k:n for k,n in enumerate(nm) if n in G};tor=[ix[n] for n in('pelvis','spine_01','spine_02','spine_03')];out=[]
    rows,gl,gr=G['torso']
    for X,p in zip(Xs,T['parts']):
        D=np.zeros_like(X)
        for s in range(p['J'].shape[1]):
            k,w=p['J'][:,s],p['W'][:,s]
            for kk,n in lk.items():
                sel=(k==kk)&(w>0)
                if not sel.any():continue
                t,g,_=G[n];a,b=H[kk],H[ix[LIMB[n[:-2]]+n[-2:]]];ab=b-a;u=np.clip(((X[sel]-a)@ab)/(ab@ab),0,1);rho=X[sel]-a-u[:,None]*ab;gg=np.interp(u,t,g)-1;D[sel]+=w[sel,None]*gg[:,None]*rho*np.array([1,1,.8])
            sel=np.isin(k,tor)&(w>0)
            if sel.any():
                Y=X[sel];rr=sole-(Y[:,1]-dy)/m;g=np.where(Y[:,0]>=0,np.interp(rr,rows,gr),np.interp(rr,rows,gl))-1;gm=(np.interp(rr,rows,gl)+np.interp(rr,rows,gr))/2-1;z=np.interp(Y[:,1],H[tor,1],H[tor,2]);D[sel,0]+=w[sel]*g*Y[:,0];D[sel,2]+=w[sel]*.8*gm*(Y[:,2]-z)
        out.append(X+D)
    return out
def skirt(T,H,fit,body,cm):
    cx,sole,m=cm;ix={n:k for k,n in enumerate(T['names'])};row=lambda k:int(sole-H[ix[k],1]/m);col=int(round(cx));cr=row('pelvis')
    while cr<fit.shape[0]-1 and fit[cr,col]:cr+=1
    if not body[cr+2,col-2:col+3].any():return None
    hem=cr
    while hem<body.shape[0]-1 and body[hem+1,col]:hem+=1
    if hem-cr<.015/m or np.count_nonzero(body[cr-int(.016/m)])<1.2*np.count_nonzero(fit[cr-int(.016/m)]):return None
    a,b=row('spine_02'),row('pelvis');wd=np.array([np.count_nonzero(body[r]) for r in range(a,b)]);return int(a+wd.argmin()),hem
def centers(ok,c,nv,dmax,bg):
    d1,e1,i1=march(ok,c,nv,dmax);d2,e2,i2=march(ok,c,-nv,dmax);v=(d1>1)&(d2>1)&i1&i2;v&=bg[e1[:,1].clip(0,bg.shape[0]-1),e1[:,0].clip(0,bg.shape[1]-1)]&bg[e2[:,1].clip(0,bg.shape[0]-1),e2[:,0].clip(0,bg.shape[1]-1)] if bg is not None else True;return np.where(v,(d1-d2)/2,np.nan)
def refine(T,mc,mt,glob,cm,body,bg,shape,it=3):
    mc=dict(mc);cx,sole,m=cm;ix={n:k for k,n in enumerate(T['names'])}
    for i in range(it):
        Xs,H,_=deform(T,mc,mt,glob,1);fit,_=sil(Xs,T,(cx,sole,m),shape);tp=lambda X:np.stack([X[...,0]/m+cx,sole-X[...,1]/m],-1);lo=int(sole-H[ix['spine_02'],1]/m)
        sh=np.arange(-20,21);sc=[(np.roll(fit[lo:],s,1)&body[lo:]).sum()-(np.roll(fit[lo:],s,1)&~body[lo:]&~bg[lo:]).sum()*0 for s in sh];cx+=sh[int(np.argmax(sc))]
        Xs,H,_=deform(T,mc,mt,glob,1);fit,_=sil(Xs,T,(cx,sole,m),shape)
        for key,b in(('a_ua','upperarm'),('a_fa','lowerarm'),('a_th','thigh'),('a_sh','calf')):
            ang=list(mc[key])
            for si,sd in enumerate(('_l','_r')):
                a,e=tp(H[ix[b+sd]]),tp(H[ix[LIMB[b]+sd]]);L=np.linalg.norm(e-a);t=np.linspace(.15,.95,24);c=a+t[:,None]*(e-a);d=(e-a)/L;nv=np.repeat(np.array([[-d[1],d[0]]]),len(t),0);dm=.6*L
                off=centers(body,c,nv,dm,bg)-centers(fit,c,nv,dm,None);v=np.isfinite(off)
                if v.sum()<5:continue
                tl=t[v]*L;dl=np.clip((off[v]*tl).sum()/(tl*tl).sum(),-.15,.15);ang[si]-=dl
            mc[key]=tuple(ang)
    return mc,(cx,sole,m)
def feet(T,H,fit,body,cm):
    cx,sole,m=cm;ix={n:k for k,n in enumerate(T['names'])};r=[]
    for sd in('_l','_r'):
        c0=int(H[ix['foot'+sd],0]/m+cx)
        for row in range(int(sole-H[ix['foot'+sd],1]/m),int(sole)-2):
            run=lambda ok:(lambda a,b:b-a)(*(lambda L:(c0-np.argmin(ok[row,c0::-1]) if not ok[row,c0::-1].all() else 0,c0+np.argmin(ok[row,c0:])))(0)) if ok[row,c0] else 0
            a,b=run(body),run(fit)
            if a>3 and b>3:r.append(a/b)
    return float(np.clip(np.median(r),.8,1.7)) if r else 1.
def lm3d(T,TF):
    x0,y0,mpp=frame(T);b=max(T['parts'],key=lambda p:len(p['P']));_,A,Z=render(b['P'],b['F'],np.zeros((len(b['P']),2)),None,x0,y0,mpp,(1200,1200));c=np.clip(((TF[:,0]-x0)/mpp).astype(int),0,1199);r=np.clip(((y0-TF[:,1])/mpp).astype(int),0,1199);z=Z[r,c];z=np.where(np.isfinite(z),z,np.median(z[np.isfinite(z)]));return np.c_[TF,z]
def facewarp(Xs,T,src,dst):
    hd=T['names'].index('Head');nk=T['names'].index('neck_01');key=[i for i in range(0,468,3) if np.isfinite(src[i]).all() and np.isfinite(dst[i]).all()];s,d=src[key],dst[key];A=np.c_[s,np.ones(len(s))];sol=np.linalg.lstsq(A,d,rcond=None)[0];res=d-A@sol
    K=lambda a,b:(lambda q:q*q*np.log(q+1e-9))(np.linalg.norm(a[:,None]-b[None],axis=2));n=len(s);M=np.zeros((n+3,n+3));M[:n,:n]=K(s,s)+2e-4*np.eye(n);M[:n,n:]=A;M[n:,:n]=A.T;cf=np.linalg.solve(M,np.r_[res,np.zeros((3,2))]);aff=lambda q:np.c_[q,np.ones(len(q))]@sol;warp=lambda q:aff(q)+K(q,s)@cf[:n]+np.c_[q,np.ones(len(q))]@cf[n:]
    ov=src[[10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109],:2];c=ov.mean(0);rad=np.linalg.norm(ov-c,axis=1).max();D=[]
    for X,p in zip(Xs,T['parts']):
        q=X[:,:2];wh=(p['W']*(p['J']==hd)).sum(1)+.5*(p['W']*(p['J']==nk)).sum(1);dd=np.linalg.norm(q-c,axis=1)/rad;f=np.clip((1.3-dd)/.4,0,1);f=f*f*(3-2*f);zc=np.median(X[wh>.9,2]) if (wh>.9).any() else 0;fr=np.clip((X[:,2]-zc)/.04+.3,0,1);Dp=np.zeros_like(X)
        if p['name']=='Eyes':
            for sg in(1,-1):sel=sg*X[:,0]>0;cc=X[sel].mean(0)[None,:2];Dp[sel,:2]=warp(cc)-cc
        else:Dp[:,:2]=wh[:,None]*((aff(q)-q)+(warp(q)-aff(q))*(f*fr)[:,None])
        D.append(Dp)
    return D,sol,res
def grid(mask,cm,x0,y0,v,shape):
    cx,sole,m=cm;iy,ix=np.mgrid[0:shape[0],0:shape[1]];c=np.clip(((x0+ix*v)/m+cx).astype(int),0,mask.shape[1]-1);r=np.clip((sole-(y0-iy*v)/m).astype(int),0,mask.shape[0]-1);return mask[r,c]
def surf(V,x0,y0,z0,v,tris):
    P,F,_,_=marching_cubes(np.pad(ndimage.gaussian_filter(V.astype(np.float32),1.),1),.5);P-=1;X=np.c_[x0+P[:,1]*v,y0-P[:,0]*v,z0+P[:,2]*v];F=F[:,::-1]
    if len(F)>tris:X,F=fast_simplification.simplify(X.astype(np.float32),F.astype(np.int32),1-tris/len(F));X=X.astype(float)
    fn=np.cross(X[F[:,1]]-X[F[:,0]],X[F[:,2]]-X[F[:,0]]);F=F if (fn*(X[F].mean(1)-X.mean(0))).sum()>0 else F[:,::-1];return X,F.astype(np.int64)
def hairvol(Xb,Fb,H,T,hair,face,al,cm,fy,v=.004,tris=16000):
    cx,sole,m=cm;ix={n:k for k,n in enumerate(T['names'])};hp=np.argwhere(hair)
    if len(hp)<50:return None
    ycut=H[ix['neck_01'],1];hx=np.r_[(hp[:,1]-cx)*m];hy=(sole-hp[:,0])*m;top=Xb[Xb[:,1]>ycut];x0=min(hx.min(),top[:,0].min())-.03;x1=max(hx.max(),top[:,0].max())+.03;y1=max(hy.max(),top[:,1].max())+.03;y0=min(hy.min(),ycut)-.03;z0=top[:,2].min()-.09;z1=top[:,2].max()+.06
    sh=(int((y1-y0)/v)+1,int((x1-x0)/v)+1);nz=int((z1-z0)/v)+1;zs=z0+np.arange(nz)*v
    up=Xb[:,1]>ycut-.01;fk=up[Fb].all(1);_,Sf,Zf=render(Xb,Fb[fk],np.zeros((len(Xb),2)),None,x0,y1,v,sh);_,_,Zb=render(Xb*np.array([1,1,-1]),Fb[fk],np.zeros((len(Xb),2)),None,x0,y1,v,sh);Zb=-Zb
    ys=y1-np.arange(sh[0])*v;S2=Sf&(ys[:,None]>=fy[0]);hr=grid(hair,cm,x0,y1,v,sh);fc=grid(face,cm,x0,y1,v,sh);ag=ndimage.binary_dilation(grid(al,cm,x0,y1,v,sh),iterations=2)
    Z3=zs[None,None,:];HI=(S2&(ys[:,None]>=fy[1]-.01))[...,None]&(Z3>=Zb[...,None])&(Z3<=Zf[...,None]);zm=np.where(S2,(Zf+Zb)/2,0);ff=fc[...,None]&(Z3>zm[...,None]-.004)
    cy,cxx=np.argwhere(S2).mean(0);ang=np.linspace(0,2*np.pi,360,endpoint=False);dl=np.zeros(360);ok=hr|S2
    for i,a in enumerate(ang):
        st=np.arange(0,max(sh));py=np.rint(cy-np.sin(a)*st).astype(int);px=np.rint(cxx+np.cos(a)*st).astype(int);inb=(py>=0)&(py<sh[0])&(px>=0)&(px<sh[1]);py,px=py[inb],px[inb];a1=S2[py,px];rs=np.argmin(a1) if not a1.all() else len(a1)-1
        if rs<len(a1) and hr[py[rs],px[rs]]:a2=ok[py,px];rh=rs+np.argmin(a2[rs:]) if not a2[rs:].all() else len(a2)-1;dl[i]=min((rh-rs)*v,.05)
    dl=ndimage.gaussian_filter1d(dl,4,mode='wrap');hd=dl[dl>0];dmin=.6*np.median(hd) if len(hd) else .008;ear=fy[1]
    iy,ixx=np.mgrid[0:sh[0],0:sh[1]];phi=np.arctan2(cy-iy,ixx-cxx)%(2*np.pi);dphi=dl[(phi/(2*np.pi)*360).astype(int)%360];D=ndimage.distance_transform_edt(~HI)*v;dd=np.maximum(dphi[...,None],np.where((ys[:,None,None]>ear)&(Z3<zm[...,None]),dmin,0))
    e=ndimage.distance_transform_edt(hr);R=np.minimum(ndimage.maximum_filter(e,size=31),.07/v);tau=np.sqrt(np.clip(2*R*e-e*e,0,None))*v;zh=np.median(top[:,2]);dn=np.clip((ycut+.03-ys[:,None])/.12,0,1);zc=zh-.065*dn;tau=tau*(1-.35*dn)
    INF=(hr&~ndimage.binary_erosion(Sf,iterations=2))[...,None]&(np.abs(Z3-zc[...,None])<=tau[...,None]);sok=(hr[...,None]&((ys>ear)[:,None,None]|(Z3>zm[...,None])))|((ys>ear-.015)[:,None,None]&(Z3<zm[...,None]+.01));V=((HI|((D>0)&(D<=dd)&sok))&~ff|INF)&ag[...,None];V&=~ff|INF&~(fc[...,None])
    return surf(V,x0,y1,z0,v,tris)
def skirtmesh(Xb,sk,al,cm,n=64,th=.004,pleats=18):
    cx,sole,m=cm;rows=np.unique(np.r_[np.arange(sk[0],sk[1],5),sk[1],sk[1]+int(.008/m)]);ang=np.linspace(0,2*np.pi,n,endpoint=False);rings=[];cen=[];col=int(round(cx))
    for i,r in enumerate(rows):
        y=(sole-r)*m;ln=al[min(r,sk[1])];c0=col-np.argmin(ln[col::-1]);c1=col+np.argmin(ln[col:]);x0,x1=(c0-cx)*m,(c1-cx)*m;B=Xb[np.abs(Xb[:,1]-y)<.012];B=B[(B[:,0]>x0-.02)&(B[:,0]<x1+.02)]
        xc=(x0+x1)/2;zc=(B[:,2].min()+B[:,2].max())/2 if len(B) else 0;a=(x1-x0)/2;bd=(B[:,2].max()-B[:,2].min())/2 if len(B) else a*.7;t=i/max(1,len(rows)-1);b=max(bd+.004+.012*t,a*.6*t+bd*(1-t))
        rad=1/np.sqrt((np.cos(ang)/a)**2+(np.sin(ang)/b)**2)
        if len(B):pa=np.arctan2(B[:,2]-zc,B[:,0]-xc)%(2*np.pi);pr=np.hypot(B[:,0]-xc,B[:,2]-zc);bi=(pa/(2*np.pi)*n).astype(int)%n;br=np.zeros(n);np.maximum.at(br,bi,pr);br=np.maximum(br,ndimage.maximum_filter1d(br,5,mode='wrap'));rad=np.maximum(rad,br+.004+.002*t)
        cen.append((y,xc,zc,a));rad=rad*(1+.035*t*np.sin(pleats*ang));rings.append(np.c_[xc+rad*np.cos(ang),np.full(n,y),zc+rad*np.sin(ang)])
    O=np.array(rings);c=O.mean(1,keepdims=True);I=c+(O-c)*(1-th/np.maximum(np.linalg.norm((O-c)*np.array([1,0,1]),axis=2,keepdims=True),1e-6));k=len(rows);X=np.r_[O.reshape(-1,3),I.reshape(-1,3)];F=[]
    q=lambda a,b,c_,d:F.extend([(a,b,c_),(a,c_,d)])
    for i in range(k-1):
        for j in range(n):j2=(j+1)%n;q(i*n+j,(i+1)*n+j,(i+1)*n+j2,i*n+j2);o=k*n;q(o+i*n+j,o+i*n+j2,o+(i+1)*n+j2,o+(i+1)*n+j)
    for j in range(n):j2=(j+1)%n;o=k*n;l=(k-1)*n;q(l+j,o+l+j,o+l+j2,l+j2);q(j,j2,o+j2,o+j)
    F=np.array(F,np.int64);fn=np.cross(X[F[:,1]]-X[F[:,0]],X[F[:,2]]-X[F[:,0]]);cc=X[F].mean(1);out=((cc-np.r_[c.reshape(-1,3).mean(0)])*np.array([1,0,1])*fn).sum(1)
    return X,(F if (out[:len(F)//2]>0).mean()>.5 else F[:,::-1]),np.array(cen)
GRP={'Head':0,'neck_01':6,'pelvis':1,'spine_01':1,'spine_02':1,'spine_03':1,'clavicle':1,'upperarm':2,'lowerarm':2,'hand':3,'thigh':4,'calf':4,'foot':5,'ball':5,'ball_leaf':5}
def grpof(n):
    b=n[:-2] if n[-2:] in('_l','_r') else n;g=GRP.get(b,3 if any(b.startswith(f) for f in('index','middle','ring','pinky','thumb')) else 1);return g+(10 if n.endswith('_r') and g>=2 else 0)
def xweights(name,X,H,T):
    ix={n:k for k,n in enumerate(T['names'])};J=np.zeros((len(X),4),int);W=np.zeros((len(X),4));sm=lambda t:(lambda u:u*u*(3-2*u))(np.clip(t,0,1))
    if name=='Hair':t=.8*sm((H[ix['neck_01'],1]+.04-X[:,1])/.25);J[:,0],J[:,1]=ix['Head'],ix['spine_03'];W[:,0],W[:,1]=1-t,t
    else:
        yw,yh=X[:,1].max(),X[:,1].min();t=np.clip((yw-X[:,1])/(yw-yh),0,1);xc=(X[:,0].max()+X[:,0].min())/2;c=np.clip((X[:,0]-xc)/np.maximum(np.abs(X[:,0]-xc).max(),1e-6),-1,1);wl=.6*t*(.5+.5*c);wr=.6*t*(.5-.5*c);J[:,0],J[:,1],J[:,2]=ix['pelvis'],ix['thigh_l'],ix['thigh_r'];W[:,0],W[:,1],W[:,2]=1-wl-wr,wl,wr
    return J,W
def bakeall(Pe,Pf,F,pid,grp,owner_parts,cm,img,al,cls,kinds,sk=None,unroll={},sz=2048):
    cx,sole,m=cm;_,u0,inv=np.unique(np.c_[np.round(Pf/1e-5).astype(np.int64),pid],axis=0,return_index=True,return_inverse=True);xa=xatlas.Atlas();xa.add_mesh(Pf[u0].astype(np.float32),inv.ravel()[F].astype(np.uint32));po=xatlas.PackOptions();po.resolution=sz;po.padding=4;po.bilinear=True;xa.generate(pack_options=po);vm,F2,UV=xa[0];F2=F2.astype(np.int64);vm=u0[vm]
    h,w=al.shape;Zb=np.full((h,w),-np.inf);own=np.full((h,w),-1)
    for k,(X,Fk) in enumerate(owner_parts):_,A,Z=render(X,Fk,np.zeros((len(X),2)),None,-cx*m,sole*m,m,(h,w));nb=A&(Z>Zb);Zb[nb]=Z[nb];own[nb]=k
    ok=al.copy();ok=ndimage.binary_erosion(ok,iterations=2);Cc=pad(img[...,:3].astype(np.float32)/255,ok)
    _,ys,xs,tt,bc=texels(UV,F2,sz);V=vm[F2[tt]];X=(Pe[V]*bc[...,None]).sum(1);Nv=snorm(Pe,F);n=(Nv[V]*bc[...,None]).sum(1);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-9);pt=pid[V[:,0]];gt=grp[V[:,0]]
    c=np.clip((X[:,0]/m+cx).astype(int),0,w-1);r=np.clip((sole-X[:,1]/m).astype(int),0,h-1);inside=(X[:,0]/m+cx>=0)&(X[:,0]/m+cx<w)&(sole-X[:,1]/m>=0)&(sole-X[:,1]/m<h);vis=inside&(Zb[r,c]-X[:,2]<.006)&(n[:,2]>.08)
    ko=np.array(kinds)[pt];cl=cls[r,c];hc=ndimage.binary_erosion(al&(cls==1),iterations=max(2,int(.005/m)))[r,c];hd_=ndimage.binary_dilation(al&(cls==1),iterations=max(2,int(.006/m)))[r,c];band=(r>=sk[0])&(r<=sk[1]+int(.008/m)) if sk else np.zeros(len(r),bool);bad=((ko=='body')&(hd_|band))|((ko=='hair')&~hc);vis&=~bad;mir=inside&(own[r,c]==pt)&al[r,c]&~((ko=='body')&(cl==3)&(n[:,2]<0))&~bad
    src=vis|mir;col=Cc[r,c].copy();fc_=ndimage.binary_erosion(al&(cls==3),iterations=max(2,int(.01/m)));lum=Cc[r,c].mean(1);sk_l=np.median(Cc[fc_].mean(1)) if fc_.any() else 0
    for k,cen in unroll.items():
        sel=pt==k;y=X[sel,1];o=np.argsort(cen[:,0]);xc,zc,a=[np.interp(y,cen[o,0],cen[o,i]) for i in(1,2,3)];u=np.abs(np.arctan2(X[sel,2]-zc,X[sel,0]-xc))/np.pi;cs=np.clip(((xc+a*(1-2*u)*.97)/m+cx).astype(int),0,w-1);rs=np.clip((sole-np.maximum(y,cen[:,0].min()+.022)/m).astype(int),0,h-1);col[sel]=Cc[rs,cs];src[sel]=True
    for g in np.unique(gt):
        sel=gt==g;a=sel&src&~((cl==3)&(g!=0));a=sel&src&(lum>=.75*sk_l) if g==6 else a;a=a if a.any() else sel&src;b=sel&~(a|vis) if g==6 else sel&~src
        if b.any() and a.any():kd=cKDTree(X[a]);d,i=kd.query(X[b],k=min(24,int(a.sum())));col[np.nonzero(b)[0]]=np.median(Cc[r[a],c[a]][i],axis=1)
    tex=np.zeros((sz,sz,3),np.float32);msk=np.zeros((sz,sz),bool);tex[ys,xs]=col;msk[ys,xs]=True;tex=pad(tex,msk)
    print('  texels',len(tt),'front',int(vis.sum()),'mirror',int((mir&~vis).sum()),'filled',int((~src).sum()))
    return vm,F2,UV,tex
def mat4(t,q):
    M=np.eye(4);M[:3,:3]=Rr.from_quat(q).as_matrix();M[:3,3]=t;return M
def glb(path,names,par,Wr,P,N,UV,J,W,F,tex,q=90):
    bufs=bytearray();views=[];acc=[]
    def add(a,ctype,typ,target=None,mm=False):
        b=a.tobytes();bufs.extend(b'\0'*(-len(bufs)%4));views.append(dict(buffer=0,byteOffset=len(bufs),byteLength=len(b),**({'target':target} if target else {})));bufs.extend(b);x=dict(bufferView=len(views)-1,componentType=ctype,count=len(a),type=typ)
        if mm:x.update(min=a.min(0).tolist(),max=a.max(0).tolist())
        acc.append(x);return len(acc)-1
    nodes=[]
    for k,n in enumerate(names):
        L=np.linalg.inv(Wr[par[k]])@Wr[k] if par[k]>=0 else Wr[k];U,_,Vt=np.linalg.svd(L[:3,:3]);nodes.append(dict(name=n,translation=L[:3,3].tolist(),rotation=Rr.from_matrix(U@Vt).as_quat().tolist(),children=[c for c in range(len(names)) if par[c]==k]))
    for nd in nodes:nd['children'] or nd.pop('children')
    W=W/np.maximum(W.sum(1,keepdims=True),1e-9);a=dict(POSITION=add(P.astype(np.float32),5126,'VEC3',34962,True),NORMAL=add(N.astype(np.float32),5126,'VEC3',34962),TEXCOORD_0=add(UV.astype(np.float32),5126,'VEC2',34962),JOINTS_0=add(J.astype(np.uint16),5123,'VEC4',34962),WEIGHTS_0=add(W.astype(np.float32),5126,'VEC4',34962));ii=add(F.astype(np.uint32).ravel(),5125,'SCALAR',34963)
    ib=add(np.array([np.linalg.inv(M).T.ravel() for M in Wr],np.float32),5126,'MAT4');jb=io.BytesIO();Image.fromarray((np.clip(tex,0,1)*255+.5).astype(np.uint8)).save(jb,'JPEG',quality=q,optimize=True);b=jb.getvalue();bufs.extend(b'\0'*(-len(bufs)%4));views.append(dict(buffer=0,byteOffset=len(bufs),byteLength=len(b)));bufs.extend(b)
    nodes.append(dict(name='Body',mesh=0,skin=0));j=dict(asset=dict(version='2.0',generator='amni-companion image3d'),scene=0,scenes=[dict(nodes=[k for k in range(len(names)) if par[k]<0]+[len(names)])],nodes=nodes,meshes=[dict(name='Body',primitives=[dict(attributes=a,indices=ii,material=0)])],skins=[dict(joints=list(range(len(names))),inverseBindMatrices=ib)],materials=[dict(name='Body',pbrMetallicRoughness=dict(baseColorTexture=dict(index=0),metallicFactor=0,roughnessFactor=.85))],textures=[dict(source=0,sampler=0)],samplers=[dict(magFilter=9729,minFilter=9987,wrapS=33071,wrapT=33071)],images=[dict(bufferView=len(views)-1,mimeType='image/jpeg')],accessors=acc,bufferViews=views,buffers=[dict(byteLength=len(bufs))])
    js=json.dumps(j,separators=(',',':')).encode();js+=b' '*(-len(js)%4);bufs.extend(b'\0'*(-len(bufs)%4));j['buffers'][0]['byteLength']=len(bufs);js=json.dumps(j,separators=(',',':')).encode();js+=b' '*(-len(js)%4)
    open(path,'wb').write(struct.pack('<III',0x46546C67,2,28+len(js)+len(bufs))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(bufs),0x004E4942)+bytes(bufs))
def cutout(im,cls,d):
    a=im[...,:3].astype(np.float32);h,w=a.shape[:2];S=max(h,w);per=cls!=0;bgm=~ndimage.binary_dilation(per,iterations=int(.04*S));g=lambda x:ndimage.gaussian_filter(x,.05*S);B=np.stack([g(a[...,k]*bgm) for k in range(3)],-1)/np.maximum(g(bgm.astype(np.float32)),1e-4)[...,None]
    P,_=marks(d);ank=int(min(P[27,1],P[28,1]));fg=(np.abs(a-B).max(-1)>16)&ndimage.binary_dilation(per,iterations=max(3,int(.02*S)));low=np.arange(h)[:,None]>ank;fg&=~low|ndimage.binary_dilation(per,iterations=3);fg|=ndimage.binary_erosion(per,iterations=max(2,int(.006*S)))
    fg=ndimage.binary_opening(fg,iterations=2);lab,n=ndimage.label(fg);fg=lab==(np.bincount(lab.ravel())[1:].argmax()+1) if n else fg;return ndimage.binary_fill_holes(fg)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));UBC=os.path.join(ROOT,'art','ubc')
def make(concept,body,hgt,out,blend=.5,work=None):
    work=work or os.path.join(ROOT,'.stock','img3d');os.makedirs(work,exist_ok=True);B={'female':'Female','male':'Male'}[body];T=tpl(os.path.join(UBC,f'Superhero_{B}_FullBody.gltf'));T['parts']=[p for p in T['parts'] if p['name']!='Eyebrows'];tj=os.path.join(UBC,f'tpl_{body}.json')
    if not os.path.exists(tj):png=os.path.join(work,'tpl.png');look(T,png);analyze(png,tj);os.path.exists(tj.replace('.json','_cls.png')) and os.remove(tj.replace('.json','_cls.png'))
    tm=json.load(open(tj));aj=os.path.join(work,'concept.json');d=analyze(concept,aj);im=np.asarray(Image.open(concept).convert('RGBA')).copy();al=im[...,3]>127;cls=np.asarray(Image.open(aj.replace('.json','_cls.png')).resize(al.shape[::-1],Image.NEAREST))[...,0]
    if al.all():al=cutout(im,cls,d);im[...,3]=al*255;Image.fromarray(im).save(os.path.join(work,'cutout.png'))
    TP,TF=marks(tm,frame(T));bi=max(range(len(T['parts'])),key=lambda i:len(T['parts'][i]['P']));bp=T['parts'][bi];top=(bp['P'][:,1].max()-TF[10,1])/(TF[10,1]-TF[152,1]);CP,CF,cm=tomet(d,al,hgt,top);mt,mc=measure(TP,TF),measure(CP,CF);glob=hgt/bp['P'][:,1].max()
    hair=al&(cls==1);bodym=al&~hair;bg=~al;Xs,H,R=deform(T,mc,mt,glob,1);fit,_=sil(Xs,T,cm,al.shape);sk=skirt(T,H,fit,bodym,cm)
    if sk:bodym[sk[0]:sk[1]+1]=False
    mc,cm=refine(T,mc,mt,glob,cm,bodym,bg,al.shape);Xs,H,R=deform(T,mc,mt,glob,1);fit,_=sil(Xs,T,cm,al.shape);gw={'foot':glob*feet(T,H,fit,bodym,cm)};Xs,H,R=deform(T,mc,mt,glob,1,gw);fit,_=sil(Xs,T,cm,al.shape);G=profiles(T,H,fit,bodym,bg,cm)
    cx,sole,m=cm;Fp=marks(d)[1];CFm=np.c_[(Fp[:,0]-cx)*m,(sole-Fp[:,1])*m];TL=lm3d(T,TF);hd=T['names'].index('Head');pv=T['names'].index('pelvis');He=None
    def fitted(bl):
        Xs,H,R=deform(T,mc,mt,glob,bl,gw);A=T['A'].copy();src=(TL@A[hd][:,:3].T+A[hd][:,3])[:,:2];o=np.zeros(2) if He is None else (H[hd]-He[hd])[:2];Xs=swell(Xs,T,H,G,cm,0 if He is None else H[pv,1]-He[pv,1]);D,_,_=facewarp(Xs,T,src,CFm+o);return [X+Dp for X,Dp in zip(Xs,D)],H,R
    Xe,He,Re=fitted(1);Xf,Hf,Rf=fitted(blend);ex=[]
    hv=hairvol(Xe[bi],bp['F'],He,T,hair,al&(cls==3),al,cm,(CFm[152,1]+(He[hd,1]-He[hd,1]),CFm[13,1]));ex+=[('Hair',)+hv] if hv else [];sm_=skirtmesh(Xe[bi],sk,al,cm) if sk else None;ex+=[('Skirt',)+sm_[:2]] if sk else []
    parts=[dict(kind='body',Pe=X,Pf=Y,F=p['F'],J=p['J'],W=p['W'],g=(lambda g_:np.where((g_==0)&(X[:,1]<CFm[152,1]),6,g_))(np.array([20 if p['name']=='Eyes' else grpof(T['names'][j]) for j in p['J'][np.arange(len(X)),p['W'].argmax(1)]]))) for X,Y,p in zip(Xe,Xf,T['parts'])]
    for n,X,F in ex:J,W=xweights(n,X,He,T);parts.append(dict(kind=n.lower(),Pe=X,Pf=X+(W[...,None]*(Hf[J]-He[J])).sum(1),F=F,J=J,W=W,g=np.full(len(X),30 if n=='Hair' else 31)))
    o=np.cumsum([0]+[len(p['Pe']) for p in parts]);Pe,Pf,J,W,g=[np.concatenate([p[k] for p in parts]) for k in('Pe','Pf','J','W','g')];F=np.concatenate([p['F']+o[i] for i,p in enumerate(parts)]);pid=np.concatenate([np.full(len(p['Pe']),i) for i,p in enumerate(parts)])
    vm,F2,UV,tex=bakeall(Pe,Pf,F,pid,g,[(p['Pe'],p['F']) for p in parts],cm,im,al,cls,[p['kind'] for p in parts],sk,{len(parts)-1:sm_[2]} if sk else {});N=snorm(Pf[vm],F2)
    Wr=np.array([np.r_[np.c_[Rf[k]@T['W'][k][:3,:3],Hf[k]],[[0,0,0,1]]] for k in range(len(T['names']))]);glb(out,T['names'],T['par'],Wr,Pf[vm],N,UV,J[vm],W[vm],F2,tex)
    print(out,f'{len(vm)} verts {len(F2)} tris','skirt' if sk else 'no skirt','hair' if hv else 'no hair',f'height {Pf[:,1].max()*39.37:.1f}in ({Pf[:,1].max():.2f}m)',f'{os.path.getsize(out)/1048576:.1f} MB')
    return out
if __name__=='__main__':make(sys.argv[1],sys.argv[2],float(sys.argv[3]),sys.argv[4],*map(float,sys.argv[5:6]))
