const te=new TextEncoder(),td=new TextDecoder()
export const SLOTS=['hips','spine','chest','upper_chest','neck','head','l_shoulder','l_upper_arm','l_lower_arm','l_hand','r_shoulder','r_upper_arm','r_lower_arm','r_hand','l_upper_leg','l_lower_leg','l_foot','l_toes','r_upper_leg','r_lower_leg','r_foot','r_toes']
export async function loadCore(src){
  const bytes=src instanceof ArrayBuffer||ArrayBuffer.isView(src)?src:await (await fetch(src)).arrayBuffer(),mod=await WebAssembly.compile(bytes),m=new Uint8Array(WebAssembly.Module.customSections(mod,'he.mem')[0]||new ArrayBuffer(5)),mem=new WebAssembly.Memory({initial:m[0]|m[1]<<8|m[2]<<16|m[3]<<24,maximum:65536}),holes=[],u8=()=>new Uint8Array(mem.buffer),N=Number,V={}
  const mmap=l=>{l=Math.ceil(l/65536)*65536;const k=holes.findIndex(h=>h[1]>=l);if(k>=0){const[a,n]=holes[k];n===l?holes.splice(k,1):holes[k]=[a+l,n-l];u8().fill(0,a,a+l);return a}try{return mem.grow(l/65536)*65536}catch{return-12}}
  const sys=(n,a,b,c)=>{switch(N(n)){case 1:{const s=td.decode(u8().subarray(N(b),N(b)+N(c)));(N(a)===2?console.warn:console.log)('[core]',s.replace(/\n$/,''));return c}case 9:return BigInt(mmap(N(b)));case 11:{const p=N(a),l=Math.ceil(N(b)/65536)*65536;p%65536===0&&l>0&&holes.push([p,l]);return 0n}case 28:N(c)===4&&u8().fill(0,N(a),N(a)+N(b));return 0n;case 228:{const t=performance.now()*1e6,w=new DataView(mem.buffer),p=N(b);w.setBigInt64(p,BigInt(Math.floor(t/1e9)),true);w.setBigInt64(p+8,BigInt(Math.floor(t%1e9)),true);return 0n}case 60:case 231:throw new Error('core exit '+N(a));case 2:case 4:return-2n;default:return 0n}}
  const keep=(id,p,n)=>{V[id]=[N(p),N(n)]},ex=(await WebAssembly.instantiate(mod,{env:{sys,memory:mem,cv_view:keep,cv_view_i:keep,cv_bytes:keep}})).exports
  ex.he_start(0n);ex.cv_init()
  const F=()=>new Float64Array(mem.buffer,V[0][0],V[0][1]),I=()=>new Int32Array(mem.buffer,V[1][0],V[1][1]),T=()=>new Uint8Array(mem.buffer,V[2][0],V[2][1]),O=()=>new Uint8Array(mem.buffer,V[3][0],V[3][1])
  const put=s=>{const b=te.encode(s).subarray(0,69999);T().set(b);return b.length},out=(n,at=0)=>td.decode(O().subarray(at,at+n))
  const L={par:0,slot:4096,slot2:4128,ev:4160,pos:0,rest:200000,rest2:200300,want:200600,res:200800,lm:201000,pose:201200,hands:201400,face:201420,objs:201500,frames:0}
  return{
    F,I,mem,
    rig(names,parents,pos){const n=Math.min(names.length,1024),i=I(),f=F();for(let k=0;k<n;k++){i[L.par+k]=parents[k];f[L.pos+3*k]=pos[3*k];f[L.pos+3*k+1]=pos[3*k+1];f[L.pos+3*k+2]=pos[3*k+2]}const len=put(names.slice(0,n).join('\n')),count=ex.cv_rig(n,len,L.par,L.pos,L.slot),slot=Array.from(I().subarray(L.slot,L.slot+22));return{slot,count,humanoid:!!ex.cv_humanoid(L.slot)}},
    retarget(sslot,srest,tslot,trest,frames,nf){const f=F(),i=I(),fr=Math.min(nf,Math.floor((L.rest-1000)/182));i.set(sslot,L.slot);i.set(tslot,L.slot2);f.set(srest,L.rest);f.set(trest,L.rest2);f.set(frames.subarray(0,91*fr),0);const o=91*fr;ex.cv_retarget(L.slot,L.rest,L.slot2,L.rest2,fr,0,o);return F().slice(o,o+91*fr)},
    solve(slot,rest,want){const f=F();I().set(slot,L.slot);f.set(rest,L.rest);f.set(want,L.want);ex.cv_solve(L.slot,L.rest,L.want,L.res);return F().slice(L.res,L.res+110)},
    pose(lm,mirror,t,slot,rest,filter=1){const f=F();I().set(slot,L.slot);f.set(rest,L.rest);f.set(lm,L.lm);const n=ex.cv_pose(L.lm,mirror?1:0,t,filter,L.slot,L.rest,L.res);return{n,out:F().slice(L.res,L.res+110)}},
    poseReset(){ex.cv_pose_reset()},
    sense(t,pose,hands,face,objs){const f=F();f.set(pose,L.pose);f.set(hands,L.hands);f.set(face,L.face);f.set(objs,L.objs);const n=ex.cv_sense(t,L.pose,L.hands,L.face,L.objs,L.ev),i=I(),r=[];for(let k=0;k<n;k++)r.push({code:i[L.ev+2*k],arg:i[L.ev+2*k+1],name:out(ex.cv_sense_name(i[L.ev+2*k]))});return r},
    senseReset(){ex.cv_sense_reset()},
    tags(text){const n=ex.cv_tags(put(text)),i=I(),clean=out(i[8190]),tags=out(i[8191],35000).split('\n').filter(Boolean).map(l=>{const k=l.indexOf(':');return k<0?{kind:l,arg:''}:{kind:l.slice(0,k),arg:l.slice(k+1)}});return{clean,tags,n}},
    reply(ctx,utter){const h=Object.entries(ctx).map(([k,v])=>`${k}=${String(v??'').replace(/\n/g,' ')}`).join('\n');return out(ex.cv_reply(put(h+'\n\n'+utter)))}
  }
}
