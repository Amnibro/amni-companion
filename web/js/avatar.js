import * as THREE from 'three'
import {GLTFLoader} from '../vendor/three/loaders/GLTFLoader.js'
const loader=new GLTFLoader(),HEIGHT=1.7,FPS=30
const ANIM={idle:'Relax_Loop',talk:'Relax_Talk_Loop',walk:'Walk_Loop',run:'Jog_Fwd_Loop',dance:'Dance_Loop',sit:['Sitting_Enter','Sitting_Idle_Loop'],stand:['Sitting_Exit'],jump:['Jump_Start','Jump_Land'],punch:['Punch_Jab','Punch_Cross'],tpose:'A_TPose',fix:'Fixing_Kneeling',interact:'Interact',pickup:'PickUp_Table',roll:'Roll',spell:['Spell_Simple_Enter','Spell_Simple_Shoot','Spell_Simple_Exit'],crouch:'Crouch_Idle_Loop',hit:'Hit_Chest',swim:'Swim_Idle_Loop',drive:'Driving_Loop',push:'Push_Loop',sword:'Sword_Attack',death:'Death01'}
const MORPH={open:/^(jawopen|mouthopen|aa|a|vrc\.v_aa|fcl_mth_a|mth_a|viseme_aa|mouth_a|v_aa)$/i,blink:/^(eyeblink|blink|eyesclosed|eyes_closed|fcl_eye_close|eye_close|blink_both|eyeblinkleft|eyeblinkright|blinkleft|blinkright)$/i,smile:/^(mouthsmile|smile|happy|joy|fcl_all_joy|fun|mouthsmileleft|mouthsmileright|fcl_mth_smile)$/i,surprised:/(surprise|fcl_all_surprised|eyewide)/i,sad:/(^sad$|sorrow|fcl_all_sorrow|mouthfrown)/i,wink:/^(wink|winkleft|eyeblinkleft|blink_l|blinkleft|fcl_eye_close_l)$/i}
const v3=(x,y,z)=>new THREE.Vector3(x,y,z),sm=u=>u<=0?0:u>=1?1:u*u*(3-2*u),osc=(t,f)=>Math.sin(t*f*Math.PI*2)
const EMOTE={
  wave:{d:2.4,w:t=>[[11,v3(-.8,-.42,.42)],[12,v3(.2*osc(t,2.2)-.22,1,.15)]]},
  heart:{d:2.2,w:()=>[[7,v3(.45,.85,.2)],[8,v3(-.7,.7,.2)],[11,v3(-.45,.85,.2)],[12,v3(.7,.7,.2)]]},
  clap:{d:2,w:t=>{const s=.07+.22*Math.abs(osc(t,2.5));return[[7,v3(.25,-.35,.9)],[8,v3(-s-.15,.35,.9)],[11,v3(-.25,-.35,.9)],[12,v3(s+.15,.35,.9)]]}},
  thumbs_up:{d:1.8,w:()=>[[11,v3(-.3,-.25,.9)],[12,v3(-.05,.75,.75)]]},
  peace:{d:1.8,w:()=>[[11,v3(-.55,.05,.75)],[12,v3(.2,.9,.35)]]},
  fist_bump:{d:1.7,w:()=>[[11,v3(-.15,.05,1)],[12,v3(0,0,1)]]},
  think:{d:2.7,w:()=>[[11,v3(-.15,-.7,.7)],[12,v3(.35,.8,.45)],[5,['z',-.18]]]},
  shrug:{d:1.7,w:()=>[[7,v3(.35,-.8,.25)],[8,v3(.45,.15,.9)],[11,v3(-.35,-.8,.25)],[12,v3(-.45,.15,.9)],[5,['z',.15]]]},
  nod:{d:1.3,w:t=>[[5,['x',.22*Math.max(0,osc(t,1.7))]]]},
  shake:{d:1.3,w:t=>[[5,['y',.3*osc(t,1.8)]]]},
  bow:{d:1.8,w:t=>{const a=.55*Math.sin(Math.min(1,t/1.8)*Math.PI);return[[1,['x',a*.5]],[2,['x',a*.5]],[5,['x',a*.3]]]}},
  laugh:{d:1.8,w:t=>[[2,['x',-.08+.07*osc(t,4)]],[5,['x',-.15+.05*osc(t,4)]]]}
}
const TL=new THREE.TextureLoader(),SK={},C=THREE.ShaderChunk,skinTex=()=>SK.p||(SK.p=Promise.all([['../models/skin_lut.png',1],['../models/pores.png',0]].map(([u,c])=>TL.loadAsync(new URL(u,import.meta.url).href).then(t=>(t.flipY=false,t.colorSpace=c?THREE.SRGBColorSpace:THREE.NoColorSpace,t.wrapS=t.wrapT=THREE.RepeatWrapping,t)))).then(([l,q])=>(SK.lut=l,SK.pores=q)))
const LP=C.lights_physical_pars_fragment.replace('reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );','PhysicalMaterial m2=material;m2.roughness=max(material.roughness*.55,.08);reflectedLight.directSpecular+=irradiance*skinCav*skinAO*(BRDF_GGX(directLight.direction,geometryViewDir,geometryNormal,material)*.85+BRDF_GGX(directLight.direction,geometryViewDir,geometryNormal,m2)*.15);').replace('reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );','float sc=skinCurv*skinAO*skinAO;vec3 la=texture2D(skinLut,vec2(dot(skinN0,directLight.direction)*.5+.5,sc)).rgb,lb=texture2D(skinLut,vec2(dot(geometryNormal,directLight.direction)*.5+.5,sc)).rgb;reflectedLight.directDiffuse+=directLight.color*vec3(mix(lb.r,la.r,skinAO),lb.g,lb.b)*mix(1.,skinAO,.5)*BRDF_Lambert(material.diffuseColor);'),NM='skinN0=normal;skinCurv=clamp(length(fwidth(normal))/max(length(fwidth(vViewPosition)),1e-6)*.002*sssAmt,0.,.7);\n'+C.normal_fragment_maps.replace('mapN.xy *= normalScale;','mapN.xy *= normalScale;vec4 pz=texture2D(poreMap,vNormalMapUv*poreScale);float ps=poreAmt*texture2D(roughnessMap,vRoughnessMapUv).b;mapN=normalize(vec3(mapN.xy+(pz.xy*2.-1.)*ps,mapN.z));skinCav=mix(1.,pz.a,.6*ps);skinAO=texture2D(roughnessMap,vRoughnessMapUv).r;')
const HS='uniform float hairShift,hairRough,hairSpec;vec3 hairT,hairCol;float hairId=.5,hairAO=1.,hairBL=1.;float hG(float b,float x){return exp(-.5*x*x/(b*b))/(2.5066*b);}float hF(float c){return .0465+.9535*pow(1.-c,5.);}vec3 hairS(vec3 L,vec3 V){vec3 T=hairT;float sL=dot(T,L),sV=dot(T,V),cD=max(cos(.5*abs(asin(clamp(sV,-1.,1.))-asin(clamp(sL,-1.,1.)))),.05),a=hairShift+(hairId-.5)*.06,b=hairRough*hairRough+.02;vec3 Lp=L-sL*T,Vp=V-sV*T,c=max(hairCol,vec3(1e-3));float cP=dot(Lp,Vp)*inversesqrt(dot(Lp,Lp)*dot(Vp,Vp)+1e-4),cH=sqrt(clamp(.5+.5*cP,0.,1.)),sa=sin(-2.*a),ca=cos(-2.*a),r=2.*sa*(ca*cH*sqrt(max(1.-sV*sV,0.))+sa*sV),ia=1./(1.19/cD+.36*cD),h=cH*(1.+ia*(.6-.8*cP)),f=hF(cD*sqrt(clamp(1.-h*h,0.,1.))),f2=hF(cD*.5);return hairAO*(vec3(hG(b*1.414*max(cH,.05),sL+sV-r)*.25*cH*hF(sqrt(clamp(.5+.5*dot(L,V),0.,1.)))*hairSpec)+hairBL*hG(b*.5,sL+sV-a)*exp(-3.65*cP-3.98)*(1.-f)*(1.-f)*pow(c,vec3(.5*sqrt(max(1.-h*h*ia*ia,0.))/cD))+hG(b*2.,sL+sV-4.*a)*exp(17.*cP-16.78)*(1.-f2)*(1.-f2)*f2*pow(c,vec3(.8/cD)));}',HP=C.lights_physical_pars_fragment.replace('reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );','reflectedLight.directSpecular+=directLight.color*hairS(directLight.direction,geometryViewDir);').replace('reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );','reflectedLight.directDiffuse+=directLight.color*BRDF_Lambert(material.diffuseColor)*mix(clamp((dot(geometryNormal,directLight.direction)+.5)/1.5,0.,1.),sqrt(max(1.-pow(dot(hairT,directLight.direction),2.),0.)),.35);')
function hairLook(m){const u={hairShift:{value:.035},hairRough:{value:m.roughness},hairSpec:{value:1.}};m.alphaToCoverage=true;m.alphaTest=.4;m.roughness=.75;m.defines={...m.defines,USE_TANGENT:''};m.userData.hair=u;m.customProgramCacheKey=()=>'hair'
  m.onBeforeCompile=s=>{Object.assign(s.uniforms,u);s.fragmentShader=s.fragmentShader.replace('#include <common>','#include <common>\n'+HS).replace('#include <lights_physical_pars_fragment>',HP).replace('#include <map_fragment>','#include <map_fragment>\nhairCol=diffuseColor.rgb;vec2 hz=vMapUv*vec2(textureSize(map,0)),hx=dFdx(hz),hy=dFdy(hz);diffuseColor.a*=1.+max(0.,.5*log2(max(dot(hx,hx),dot(hy,hy))))*.25;').replace('#include <normal_fragment_begin>','#include <normal_fragment_begin>\nhairT=-normalize(vTangent);vec3 hd=texture2D(aoMap,vAoMapUv).rgb;hairId=hd.g;hairAO=hd.r;\n#ifdef USE_COLOR\nhairAO*=vColor.r;hairBL=smoothstep(.6,.95,vColor.r);\n#endif')}}
function skinLook(o,m){const A=o.geometry.attributes.position.array,U=o.geometry.attributes.uv.array,I=o.geometry.index.array;let a3=0,a2=0;for(let i=0;i<I.length;i+=3){const a=I[i]*3,b=I[i+1]*3,c=I[i+2]*3,ux=A[b]-A[a],uy=A[b+1]-A[a+1],uz=A[b+2]-A[a+2],vx=A[c]-A[a],vy=A[c+1]-A[a+1],vz=A[c+2]-A[a+2],p=I[i]*2,q=I[i+1]*2,r=I[i+2]*2;a3+=Math.hypot(uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx);a2+=Math.abs((U[q]-U[p])*(U[r+1]-U[p+1])-(U[r]-U[p])*(U[q+1]-U[p+1]))}
  const k=Math.sqrt(a3/Math.max(a2,1e-12))*1e3/8,r=m.map?.image?Math.sqrt(m.map.image.width/m.map.image.height):1,u={skinLut:{value:SK.lut},poreMap:{value:SK.pores},poreScale:{value:new THREE.Vector2(k*r,k/r)},poreAmt:{value:m.normalMap?.55:0},sssAmt:{value:.8}};m.defines={...m.defines,SKIN:''};m.customProgramCacheKey=()=>'skin'
  m.onBeforeCompile=s=>{Object.assign(s.uniforms,u);s.fragmentShader=s.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D skinLut,poreMap;uniform vec2 poreScale;uniform float poreAmt,sssAmt;vec3 skinN0;float skinCurv,skinCav=1.,skinAO=1.;').replace('#include <lights_physical_pars_fragment>',LP).replace('#include <normal_fragment_maps>',NM)}}
const look=o=>{const m=o.material,k=m?.userData?.amni;k==='skin'?skinLook(o,m):k==='hair'?hairLook(m):k==='eye'&&(o.material=new THREE.MeshPhysicalMaterial({name:m.name,map:m.map,alphaTest:m.alphaTest,side:m.side,roughness:.35,clearcoat:1,clearcoatRoughness:.03}))}
const parseGltf=buf=>new Promise((ok,no)=>loader.parse(buf,'',ok,no)),loadGltf=url=>new Promise((ok,no)=>loader.load(url,ok,undefined,no))
const origName=(g,o)=>{const a=g.parser.associations.get(o);return a&&a.nodes!==undefined?g.parser.json.nodes[a.nodes]?.name||o.name:o.name}
function skeletonOf(g){let best=null;g.scene.traverse(o=>{o.isSkinnedMesh&&(!best||o.skeleton.bones.length>best.skeleton.bones.length)&&(best=o)});const bones=best?best.skeleton.bones.slice():[];bones.length||g.scene.traverse(o=>o.isBone&&bones.push(o));return bones}
function frame(core,g,holder,root,target){
  const bones=skeletonOf(g),names=bones.map(b=>origName(g,b)),parents=bones.map(b=>bones.indexOf(b.parent)),pos=()=>{root.updateMatrixWorld(true);const p=new Float64Array(bones.length*3),w=new THREE.Vector3();bones.forEach((b,i)=>{b.getWorldPosition(w);p.set([w.x,w.y,w.z],3*i)});return p}
  const fit=()=>{root.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(holder,true),h=box.max.y-box.min.y;if(target&&h>1e-4){holder.scale.multiplyScalar(target/h);root.updateMatrixWorld(true);box.setFromObject(holder,true)}const c=box.getCenter(new THREE.Vector3());holder.position.x-=c.x;holder.position.z-=c.z;holder.position.y-=box.min.y;root.updateMatrixWorld(true)}
  fit();let r=core.rig(names,parents,pos())
  if(r.slot[7]>=0&&r.slot[11]>=0){const p=pos();p[3*r.slot[7]]<p[3*r.slot[11]]&&(holder.rotation.y+=Math.PI,fit(),r=core.rig(names,parents,pos()))}
  root.updateMatrixWorld(true);const rest=new Float64Array(264),q=new THREE.Quaternion(),w=new THREE.Vector3()
  r.slot.forEach((bi,k)=>{if(bi<0)return;const b=bones[bi];b.getWorldQuaternion(q);rest.set([q.x,q.y,q.z,q.w],12*k);b.getWorldPosition(w);rest.set([w.x,w.y,w.z],12*k+4);b.parent.getWorldQuaternion(q);rest.set([q.x,q.y,q.z,q.w],12*k+7);rest[12*k+11]=1})
  return{bones,names,slot:r.slot,count:r.count,humanoid:r.humanoid,rest}
}
export async function loadLibrary(core,url){
  const g=await loadGltf(url),holder=new THREE.Group(),root=new THREE.Group();holder.add(g.scene);root.add(holder);const f=frame(core,g,holder,root,0),mixer=new THREE.AnimationMixer(g.scene),q=new THREE.Quaternion(),w=new THREE.Vector3(),clips=[]
  for(const clip of g.animations){if(/_RM$/.test(clip.name))continue;const nf=Math.max(2,Math.min(1000,Math.round(clip.duration*FPS)+1)),fr=new Float64Array(91*nf),act=mixer.clipAction(clip);mixer.stopAllAction();act.reset().setLoop(THREE.LoopOnce,1).play();act.clampWhenFinished=true
    for(let i=0;i<nf;i++){mixer.setTime(Math.min(clip.duration,i/FPS));root.updateMatrixWorld(true);f.slot.forEach((bi,k)=>{if(bi<0){fr.set([0,0,0,1],91*i+4*k);return}f.bones[bi].getWorldQuaternion(q);fr.set([q.x,q.y,q.z,q.w],91*i+4*k)});f.slot[0]>=0&&(f.bones[f.slot[0]].getWorldPosition(w),fr.set([w.x,w.y,w.z],91*i+88))}
    act.stop();clips.push({name:clip.name,nf,frames:fr,duration:(nf-1)/FPS,loop:/_Loop$|^A_TPose$/.test(clip.name)})}
  mixer.stopAllAction();return{slot:f.slot,rest:f.rest,clips,gltf:g,mannequin:()=>g}
}
export async function loadAvatar(core,src,lib){
  const g=src.parser?src:typeof src==='string'?await loadGltf(src):await parseGltf(src),root=new THREE.Group(),holder=new THREE.Group(),json=g.parser.json
  holder.add(g.scene);root.add(holder);json.extensions?.VRM&&(holder.rotation.y=Math.PI)
  await skinTex();g.scene.traverse(o=>{o.isMesh&&(o.castShadow=true,o.receiveShadow=true,o.frustumCulled=false,look(o))})
  const f=frame(core,g,holder,root,HEIGHT);if(!f.humanoid)throw new Error(`This model has no humanoid skeleton the companion can drive (${f.count}/22 body parts found). Try a rigged .glb or .vrm.`)
  const mixer=new THREE.AnimationMixer(g.scene),actions={},restQ=f.bones.map(b=>b.quaternion.clone()),hips=f.bones[f.slot[0]],pinv=new THREE.Matrix4().copy(hips.parent.matrixWorld).invert(),tmp=new THREE.Vector3()
  for(const c of lib.clips){const out=core.retarget(lib.slot,lib.rest,f.slot,f.rest,c.frames,c.nf),nf=out.length/91,times=Float32Array.from({length:nf},(_,i)=>i/FPS),tracks=[]
    f.slot.forEach((bi,k)=>{if(bi<0||lib.slot[k]<0)return;const vals=new Float32Array(4*nf);for(let i=0;i<nf;i++)vals.set(out.subarray(91*i+4*k,91*i+4*k+4),4*i);tracks.push(new THREE.QuaternionKeyframeTrack(f.bones[bi].uuid+'.quaternion',times,vals))})
    const pv=new Float32Array(3*nf);for(let i=0;i<nf;i++){tmp.set(out[91*i+88],out[91*i+89],out[91*i+90]).applyMatrix4(pinv);pv.set([tmp.x,tmp.y,tmp.z],3*i)}tracks.push(new THREE.VectorKeyframeTrack(hips.uuid+'.position',times,pv))
    const a=mixer.clipAction(new THREE.AnimationClip(c.name,c.duration,tracks));a.loop=c.loop?THREE.LoopRepeat:THREE.LoopOnce;a.clampWhenFinished=!c.loop;actions[c.name]=a}
  const byNode=new Map();g.scene.traverse(o=>{const a=g.parser.associations.get(o);a?.nodes!==undefined&&!byNode.has(a.nodes)&&byNode.set(a.nodes,o)})
  const cs=(json.nodes||[]).flatMap((n,i)=>{const c=n.extensions?.VRMC_node_constraint?.constraint,d=byNode.get(i),[kind,v]=c?Object.entries(c)[0]||[]:[],src=v&&byNode.get(v.source);return d&&src?[{kind,d,s:src,w:v.weight??1,axis:v.rollAxis||v.aimAxis,dr:d.quaternion.clone(),sr:src.quaternion.clone()}]:[]}),cons=[];while(cs.length){const i=cs.findIndex(c=>!cs.some(o=>o!==c&&o.d===c.s));cons.push(...cs.splice(Math.max(0,i),1))}
  const morphs={};g.scene.traverse(o=>{if(!o.morphTargetDictionary)return;for(const[n,i]of Object.entries(o.morphTargetDictionary))for(const[k,re]of Object.entries(MORPH))re.test(n)&&(morphs[k]=morphs[k]||[]).push([o,i])})
  return new Avatar({core,g,root,holder,mixer,actions,f,restQ,morphs,lib,cons})
}
class Avatar{
  constructor(o){Object.assign(this,o);this.slot=o.f.slot;this.bones=o.f.bones;this.rest=o.f.rest;this.cur=null;this.queue=[];this.emotes=[];this.face={};this.faceT={};this.talk=0;this.blinkT=2;this.look=null;this.lookW=0;this.live=new Float64Array(264);this.want=new Float64Array(110);this.track=null;this.trackW=0;this.time=0;this.relax()
    this.mixer.addEventListener('finished',e=>{if(e.action!==this.cur)return;const n=this.queue.shift();n?this.playClip(n,.2):this.base()});this.base(0)}
  has(n){return!!this.actions[n]}
  base(fade=.35){this.playClip(this.sitting?'Sitting_Idle_Loop':this.talk>0?'Relax_Talk_Loop':'Relax_Loop',fade)}
  relax(){const s=this.slot,B=this.bones,hips=B[s[0]],hp=hips.position.clone(),nf=4*FPS+1,times=Float32Array.from({length:nf},(_,i)=>i/FPS),W=new Float64Array(110),Q=THREE.Quaternion,rr=this.root.quaternion.clone(),keep=B.map(b=>b.quaternion.clone());this.root.quaternion.identity()
    for(const talk of[0,1]){const vals=s.map(()=>new Float32Array(4*nf)),pv=new Float32Array(3*nf)
      for(let i=0;i<nf;i++){const ph=Math.PI*2*i/(nf-1),g=k=>talk?Math.max(0,Math.sin(ph*2+k*Math.PI)):0;B.forEach((b,k)=>b.quaternion.copy(this.restQ[k]));const L=this.livePack();W.fill(0)
        for(const[u,f,x,k]of[[7,8,1,0],[11,12,-1,1]]){const d=v3(x*.15,-.985,.1+.02*Math.sin(ph+k)).normalize(),e=v3(x*(.05-.1*g(k)),-.92+.62*g(k),.38+.45*g(k)).normalize();W.set([d.x,d.y,d.z,0,2],5*u);W.set([e.x,e.y,e.z,0,2],5*f)}
        for(const[k,a,ax]of[[3,.012*Math.sin(ph),'x'],[5,talk?.05*Math.sin(ph*3):.015*Math.sin(ph+1),'x']]){const q=new Q().setFromAxisAngle(v3(ax==='x'?1:0,0,0),a).multiply(new Q().fromArray(L,12*k));W.set([q.x,q.y,q.z,q.w,1],5*k)}
        const out=this.core.solve(s,L,W);s.forEach((bi,k)=>{bi>=0&&vals[k].set(out[5*k+4]>.5?out.subarray(5*k,5*k+4):this.restQ[bi].toArray(),4*i)});pv.set([hp.x,hp.y,hp.z],3*i)}
      const tracks=s.flatMap((bi,k)=>bi<0?[]:[new THREE.QuaternionKeyframeTrack(B[bi].uuid+'.quaternion',times,vals[k])]).concat(new THREE.VectorKeyframeTrack(hips.uuid+'.position',times,pv)),a=this.mixer.clipAction(new THREE.AnimationClip(talk?'Relax_Talk_Loop':'Relax_Loop',(nf-1)/FPS,tracks));a.loop=THREE.LoopRepeat;this.actions[a.getClip().name]=a}
    B.forEach((b,k)=>b.quaternion.copy(keep[k]));this.root.quaternion.copy(rr)}
  playClip(name,fade=.3){const a=this.actions[name];if(!a||a===this.cur&&a.isRunning())return!!a;a.reset().setEffectiveWeight(1).play();this.cur?a.crossFadeFrom(this.cur,fade,false):a.fadeIn(fade);this.cur=a;return true}
  anim(n){if(n==='spin'){this.spin=1.2;return true}if(n==='idle'||n==='stand'){const was=this.sitting;this.sitting=false;this.queue=[];was&&this.has('Sitting_Exit')?this.playClip('Sitting_Exit'):this.base();return true}const s=ANIM[n];if(!s)return false;const l=[].concat(s).filter(x=>this.has(x));if(!l.length)return false;this.sitting=n==='sit';this.queue=l.slice(1);return this.playClip(l[0])}
  loco(on,run){on?this.playClip(run&&this.has('Jog_Fwd_Loop')?'Jog_Fwd_Loop':'Walk_Loop',.25):(this.cur===this.actions.Walk_Loop||this.cur===this.actions.Jog_Fwd_Loop)&&this.base(.3)}
  emote(n){if(n==='tpose')return this.anim('tpose');const e=EMOTE[n];if(!e)return false;this.emotes=this.emotes.filter(x=>x.n!==n);this.emotes.push({n,e,t:0});return true}
  setFace(n,v=1,hold=2.5){this.faceT[n]=v;hold&&setTimeout(()=>this.faceT[n]=0,hold*1000)}
  speaking(on){this.talk=on?1:0;!this.sitting&&(this.cur===this.actions.Relax_Loop||this.cur===this.actions.Relax_Talk_Loop)&&this.base(.5)}
  lookAt(p,w=1){this.look=p;this.lookTarget=w}
  pose(out,w=1){this.track=out;this.trackTarget=w}
  applyCons(){const Q=THREE.Quaternion,V=THREE.Vector3;for(const c of this.cons){const ds=new Q().copy(c.sr).invert().multiply(c.s.quaternion)
    if(c.kind==='rotation')c.d.quaternion.copy(c.dr).multiply(new Q().slerp(ds,c.w))
    else if(c.kind==='roll'){const inD=new Q().copy(c.dr).invert().multiply(new Q().copy(c.sr).multiply(ds).multiply(new Q().copy(c.sr).invert())).multiply(c.dr),ax=new V(c.axis==='X'?1:0,c.axis==='Y'?1:0,c.axis==='Z'?1:0),tw=new Q().setFromUnitVectors(ax,ax.clone().applyQuaternion(inD)).invert().multiply(inD);c.d.quaternion.copy(c.dr).multiply(new Q().slerp(tw,c.w))}
    else if(c.kind==='aim'){const pw=c.d.parent.getWorldQuaternion(new Q()),m=/^Negative/.test(c.axis)?-1:1,a=c.axis.slice(-1),from=new V(a==='X'?m:0,a==='Y'?m:0,a==='Z'?m:0).applyQuaternion(pw.clone().multiply(c.dr)),to=c.s.getWorldPosition(new V()).sub(c.d.getWorldPosition(new V())).normalize(),t=new Q().slerp(new Q().setFromUnitVectors(from,to),c.w).multiply(pw).multiply(c.dr);c.d.quaternion.copy(pw.invert().multiply(t))}}}
  setMorph(k,v){for(const[o,i]of this.morphs[k]||[])o.morphTargetInfluences[i]=v}
  livePack(){const q=new THREE.Quaternion(),w=new THREE.Vector3(),L=this.live;this.root.updateMatrixWorld(true);this.slot.forEach((bi,k)=>{if(bi<0){L[12*k+11]=0;return}const b=this.bones[bi];b.getWorldQuaternion(q);L.set([q.x,q.y,q.z,q.w],12*k);b.getWorldPosition(w);L.set([w.x,w.y,w.z],12*k+4);b.parent.getWorldQuaternion(q);L.set([q.x,q.y,q.z,q.w],12*k+7);L[12*k+11]=1});return L}
  update(dt){
    this.time+=dt;this.mixer.update(dt);this.spin>0&&(this.spin-=dt,this.holder.rotation.y+=dt*Math.PI*2/1.2,this.spin<=0&&(this.holder.rotation.y=Math.round(this.holder.rotation.y/Math.PI)*Math.PI))
    this.trackW+=((this.track?this.trackTarget:0)-this.trackW)*Math.min(1,dt*7)
    if(this.track&&this.trackW>.01){const q=new THREE.Quaternion();this.slot.forEach((bi,k)=>{bi>=0&&this.track[5*k+4]>.5&&this.bones[bi].quaternion.slerp(q.fromArray(this.track,5*k),this.trackW)})}
    this.lookW+=((this.look?this.lookTarget:0)-this.lookW)*Math.min(1,dt*4)
    const W=this.want;W.fill(0);let any=false;const rq=this.root.getWorldQuaternion(new THREE.Quaternion()),L=this.emotes.length||this.lookW>.01?this.livePack():null,wt=new Float64Array(22)
    for(const x of this.emotes){x.t+=dt;const env=sm(x.t/.3)*sm((x.e.d-x.t)/.35);for(const[k,v]of x.e.w(x.t)){if(this.slot[k]<0)continue;any=true;wt[k]=Math.max(wt[k],env);if(Array.isArray(v)){const ax=v3(v[0]==='x'?1:0,v[0]==='y'?1:0,v[0]==='z'?1:0).applyQuaternion(rq),qq=new THREE.Quaternion().setFromAxisAngle(ax,v[1]).multiply(new THREE.Quaternion().fromArray(L,12*k));W.set([qq.x,qq.y,qq.z,qq.w,1],5*k)}else{const d=v.clone().normalize().applyQuaternion(rq);W.set([d.x,d.y,d.z,0,2],5*k)}}}
    this.emotes=this.emotes.filter(x=>x.t<x.e.d)
    if(this.lookW>.01&&this.look&&this.slot[5]>=0&&!W[5*5+4]){const hq=new THREE.Quaternion().fromArray(L,60),h0=new THREE.Quaternion().fromArray(this.rest,60),fwd=v3(0,0,1).applyQuaternion(hq.clone().multiply(h0.invert())),hp=v3(L[64],L[65],L[66]),to=this.look.clone().sub(hp).normalize(),qf=new THREE.Quaternion().setFromUnitVectors(fwd,to),ang=2*Math.acos(Math.min(1,Math.abs(qf.w))),lim=1.05;ang>lim&&qf.slerp(new THREE.Quaternion(),1-lim/ang);for(const[k,s]of[[4,.4],[5,.7]]){if(this.slot[k]<0||W[5*k+4])continue;const qq=new THREE.Quaternion().slerp(qf,s).multiply(new THREE.Quaternion().fromArray(L,12*k));W.set([qq.x,qq.y,qq.z,qq.w,1],5*k);wt[k]=Math.max(wt[k],this.lookW);any=true}}
    if(any){const out=this.core.solve(this.slot,L,W),q=new THREE.Quaternion();this.slot.forEach((bi,k)=>{bi>=0&&out[5*k+4]>.5&&wt[k]>0&&this.bones[bi].quaternion.slerp(q.fromArray(out,5*k),wt[k])})}
    this.cons.length&&this.applyCons()
    this.blinkT-=dt;const bl=this.blinkT<0?1:0;this.blinkT<-.12&&(this.blinkT=2+Math.random()*3.5)
    const mouth=this.talk?Math.max(0,.35+.35*Math.sin(this.time*17)+.2*Math.sin(this.time*29)):0
    for(const k of['smile','surprised','sad','wink'])this.face[k]=(this.face[k]||0)+((this.faceT[k]||0)-(this.face[k]||0))*Math.min(1,dt*8),this.setMorph(k,this.face[k])
    this.setMorph('open',mouth);this.setMorph('blink',Math.max(bl,this.face.wink>.5?0:0))
  }
  dispose(){this.mixer.stopAllAction();this.root.removeFromParent();this.root.traverse(o=>{o.geometry?.dispose();[].concat(o.material||[]).forEach(m=>{for(const v of Object.values(m))v?.isTexture&&v.dispose();m.dispose()})})}
}
export const ANIMS=Object.keys(ANIM).concat(['spin']),EMOTES=Object.keys(EMOTE).concat(['tpose'])
