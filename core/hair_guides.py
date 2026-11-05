import json,struct,sys,numpy as np
src,dst_glb,dst_g=sys.argv[1:4]
b=open(src,'rb').read();l=struct.unpack('<I',b[12:16])[0];j=json.loads(b[20:20+l]);bin_=b[20+l+8:]
def acc(i):
    a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];dt={5126:np.float32,5123:np.uint16,5125:np.uint32,5121:np.uint8}[a['componentType']];x=np.frombuffer(bin_,dt,a['count']*n,v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],n).astype(float);return x/255 if dt==np.uint8 and a.get('normalized') else x
mi=[k for k,m in enumerate(j['meshes']) if m['name']=='hair'][0];pr=j['meshes'][mi]['primitives'][0];P=acc(pr['attributes']['POSITION']);U=acc(pr['attributes']['TEXCOORD_0']);C=acc(pr['attributes']['COLOR_0'])
L,R,UL,CL=P[0::2],P[1::2],U[0::2],(C[0::2,0]+C[1::2,0])/2;v=UL[:,1];st=np.r_[0,np.flatnonzero(v[1:]<v[:-1])+1,len(v)]
print('COLOR_0 r min/mean/max',C[:,0].min().round(3),C[:,0].mean().round(3),C[:,0].max().round(3),'a',C[:,3].min().round(3))
pts=[];segs=[];g=0
for a,e in zip(st[:-1],st[1:]):
    if e-a<2:continue
    c=(L[a:e]+R[a:e])/2;sd=(R[a:e]-L[a:e])/2;tg=np.gradient(c,axis=0);n=np.cross(tg,sd);n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12;tt=(v[a:e]-v[a])/max(v[e-1]-v[a],1e-6);o=len(pts)
    pts+=[np.r_[c[k],CL[a+k],sd[k],tt[k],n[k],0] for k in range(e-a)];segs+=[(o+k,g,0,0) for k in range(e-a-1)];g+=1
pts=np.array(pts,np.float32);segs=np.array(segs,np.uint32);print('guides',g,'points',len(pts),'segs',len(segs),'mean card width mm',round(float(np.linalg.norm(pts[:,4:7],axis=1).mean()*2000),2))
open(dst_g,'wb').write(b'HMG2'+struct.pack('<iii',g,len(pts),len(segs))+pts.tobytes()+segs.tobytes())
for nd in j['nodes']:
    if nd.get('mesh')==mi:nd.pop('mesh');nd.pop('skin',None)
s=json.dumps(j).encode();s+=b' '*(-len(s)%4);rest=b[20+l:];open(dst_glb,'wb').write(b[:8]+struct.pack('<I',12+8+len(s)+len(rest))+struct.pack('<I',len(s))+b'JSON'+s+rest)
