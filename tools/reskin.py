import io,json,struct,sys,numpy as np
from PIL import Image
from scipy import ndimage,sparse
from scipy.sparse.csgraph import dijkstra
H,SIG,CT=0.007,0.025,{5126:np.float32,5123:np.uint16,5121:np.uint8,5125:np.uint32}
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
def seg(p,a,b):
    d=b-a;t=np.clip(((p-a)@d)/max(d@d,1e-12),0,1);return np.linalg.norm(p-(a+t[:,None]*d),axis=1)
def run(path):
    j,bn=rd(path);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);F=get(j,bn,pr['indices']).astype(np.int64).reshape(-1,3);sk=j['skins'][0];jn=sk['joints'];names=[j['nodes'][i]['name'] for i in jn];ix={n:k for k,n in enumerate(names)}
    par=[-1]*len(jn);[par.__setitem__(jn.index(c),k) for k,i in enumerate(jn) for c in j['nodes'][i].get('children',[]) if c in jn]
    if any('rotation' in j['nodes'][i] or 'scale' in j['nodes'][i] for i in jn):sys.exit('joint rotations are not supported')
    wp=np.zeros((len(jn),3))
    for k in range(len(jn)):wp[k]=np.array(j['nodes'][jn[k]].get('translation',[0,0,0]))+(wp[par[k]] if par[k]>=0 else 0)
    lo=P.min(0)-3*H;dim=np.ceil((P.max(0)-lo)/H).astype(int)+4;sh=np.zeros(dim,bool);A,B,C=P[F[:,0]],P[F[:,1]],P[F[:,2]];K=np.clip(np.ceil(np.maximum.reduce([np.linalg.norm(B-A,axis=1),np.linalg.norm(C-A,axis=1),np.linalg.norm(C-B,axis=1)])/(.5*H)),1,40).astype(int)
    for k in np.unique(K):
        m=K==k;u,v=np.meshgrid(np.arange(k+1),np.arange(k+1));s=(u+v)<=k;u,v=u[s]/k,v[s]/k;q=(A[m][:,None]+(B[m]-A[m])[:,None]*u[None,:,None]+(C[m]-A[m])[:,None]*v[None,:,None]).reshape(-1,3);g=((q-lo)/H).astype(int);sh[g[:,0],g[:,1],g[:,2]]=True
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
    for k in lim:dd=np.min([seg(P,a,b) for a,b in segs[k]],0);rl=rloc(k) if not names[k].endswith('Shoulder') else R[k];cap[:,k]=np.clip((2.2*rl-dd)/(.85*rl),0,1)
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
    for k in range(len(jn)):j['nodes'][jn[k]]['translation']=list(map(float,wp[k]-(wp[par[k]] if par[k]>=0 else 0)))
    ib=np.zeros((len(jn),16));ib[:,[0,5,10,15]]=1;ib[:,12:15]=-wp;e0=np.abs(get(j,bn,sk['inverseBindMatrices'])[:,12:15]+w0).max();e0>1e-4 and sys.exit(f'unexpected bind matrices ({e0:.4f})');put(j,bn,sk['inverseBindMatrices'],ib);wr(path,j,bn)
    print(path,'solid',N,'moved',', '.join(f'{names[k]} {np.linalg.norm(wp[k]-w0[k])*39.37:.1f}in' for k in range(len(jn)) if np.linalg.norm(wp[k]-w0[k])>.005),'| max-weight median',f'{np.median(v[:,0]):.2f}',f'q25 {np.quantile(v[:,0],.25):.2f}')
    return names,wp
def graft(src,rig,out,q=86,px=2048):
    j,bn=rd(src);pr=j['meshes'][0]['primitives'][0];at=pr['attributes'];P=get(j,bn,at['POSITION']);Nm=get(j,bn,at['NORMAL']);UV=get(j,bn,at['TEXCOORD_0']);F=get(j,bn,pr['indices']).astype(np.uint32).ravel()
    rj,rb=rd(rig);RP=get(rj,rb,rj['meshes'][0]['primitives'][0]['attributes']['POSITION']);mn,mx=RP.min(0),RP.max(0);s=(mx[1]-mn[1])/np.ptp(P[:,1]);ref=RP[::max(1,len(RP)//3000)];fit=[]
    for fl in(1,-1):
        Q=P*np.array([fl,1,fl])*s;Q+=(mn+mx)/2-(Q.min(0)+Q.max(0))/2;Q[:,1]+=mn[1]-Q[:,1].min();sub=Q[::max(1,len(Q)//3000)];fit.append((np.sqrt(((sub[:,None]-ref[None])**2).sum(2)).min(1).mean(),fl,Q))
    err,fl,P=min(fit,key=lambda x:x[0]);_,u0,inv=np.unique(np.c_[np.round(P/1e-5),np.round(UV/1e-6)].astype(np.int64),axis=0,return_index=True,return_inverse=True);F=inv.ravel()[F].reshape(-1,3);P,UV=P[u0],UV[u0];F=F[(F[:,0]!=F[:,1])&(F[:,1]!=F[:,2])&(F[:,0]!=F[:,2])];pk=np.unique(np.round(P/1e-5).astype(np.int64),axis=0,return_inverse=True)[1].ravel();fn=np.cross(P[F[:,1]]-P[F[:,0]],P[F[:,2]]-P[F[:,0]]);acc_n=np.zeros((pk.max()+1,3));[np.add.at(acc_n,pk[F[:,c]],fn) for c in range(3)];Nm=acc_n[pk]/np.maximum(np.linalg.norm(acc_n[pk],axis=1,keepdims=True),1e-12);F=F.astype(np.uint32).ravel();rk=rj['skins'][0]['joints'];nm={o:i+1 for i,o in enumerate(rk)};wp={}
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
    wr(out,nj,out_b);print(out,'grafted',len(F)//3,'tris',n,'verts','fit',f'{err*39.37:.2f}in','flipped' if fl<0 else '');return run(out)
if __name__=='__main__':graft(*sys.argv[2:5]) if sys.argv[1:2]==['--graft'] else [run(p) for p in sys.argv[1:]]
