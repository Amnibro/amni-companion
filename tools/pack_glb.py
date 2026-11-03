import io,json,struct,sys
from PIL import Image
def pack(src,dst,q=86,maxsz=2048):
    b=open(src,'rb').read();n=struct.unpack('<I',b[12:16])[0];j=json.loads(b[20:20+n]);o=20+n;bl=struct.unpack('<I',b[o:o+4])[0];bin_=b[o+8:o+8+bl]
    imv={im['bufferView']:k for k,im in enumerate(j.get('images',[])) if 'bufferView' in im};out=bytearray();views=[]
    for k,v in enumerate(j['bufferViews']):
        d=bin_[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
        if k in imv:
            im=Image.open(io.BytesIO(d));im.thumbnail((maxsz,maxsz),Image.LANCZOS);a='A' in im.getbands() and im.getchannel('A').getextrema()[0]<250
            s=io.BytesIO();(im.save(s,'PNG',optimize=True) if a else im.convert('RGB').save(s,'JPEG',quality=q,optimize=True,progressive=True));d=s.getvalue();j['images'][imv[k]]['mimeType']='image/png' if a else 'image/jpeg'
        while len(out)%4:out.append(0)
        v=dict(v);v['byteOffset']=len(out);v['byteLength']=len(d);out+=d;views.append(v)
    while len(out)%4:out.append(0)
    j['bufferViews']=views;j['buffers'][0]['byteLength']=len(out);js=json.dumps(j,separators=(',',':')).encode()
    js+=b' '*((4-len(js)%4)%4);t=12+8+len(js)+8+len(out)
    open(dst,'wb').write(struct.pack('<III',0x46546C67,2,t)+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(out),0x004E4942)+out)
    print(dst,len(b),'->',t)
if __name__=='__main__':pack(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 86)
