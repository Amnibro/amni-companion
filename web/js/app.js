import * as THREE from 'three'
import {OrbitControls} from '../vendor/three/controls/OrbitControls.js'
import {RoomEnvironment} from '../vendor/three/environments/RoomEnvironment.js'
import {loadCore} from './core.js'
import {loadLibrary,loadAvatar} from './avatar.js'
import {PROVIDERS,ask} from './brain.js'
import * as voice from './voice.js'
import {Senses} from './senses.js'
import * as store from './store.js'
import {arSupported,startAR} from './xr.js'
const VERSION='1.1.1',$=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],BASE=new URL('../',import.meta.url),now=()=>performance.now()
const STOCK={holo:{name:'Holo',file:'models/holo.glb',img:'models/holo.webp',persona:'holo',blurb:'Bubbly punk-pop holo buddy'},dex:{name:'Dex',file:'models/dex.glb',img:'models/dex.webp',persona:'dex',blurb:'Calm engineer, dry wit'},mannequin:{name:'Mannequin',cname:'Amni',file:'anim/AnimationLibrary_Godot_Standard.gltf',img:'models/mannequin.webp',persona:'neutral',blurb:'Plain and simple'}}
const COOL={wave:7000,clap:7000,hands_up:7000,thumbs_up:7000,thumbs_down:7000,peace:7000,love:7000,fist:7000,pointing_up:7000,point:7000,wink:10000,nod:14000,head_shake:14000,object:4000},reacted={}
let S=store.load(),core,lib,av=null,avMeta={name:'',persona:'neutral'},senses=null,listener=null,xr=null,mode='room',busy=false,talking=false,lastReact=0,home=new THREE.Vector3(),go=null,roam=0,lookOff=null,history=S.remember?S.history||[]:[],ctrl=null,roomView=null,greeted=false
const save=()=>{S.history=history;store.save(S)}
const canvas=$('#stage'),renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});renderer.setPixelRatio(Math.min(2,devicePixelRatio));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,1,.05,100),clock=new THREE.Clock();camera.position.set(0,1.27,4.7)
scene.environment=new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(),.04).texture
const keyL=new THREE.DirectionalLight(0xffffff,1.7);keyL.position.set(1.4,3.2,2.1);keyL.castShadow=true;keyL.shadow.mapSize.set(1024,1024);Object.assign(keyL.shadow.camera,{left:-2,right:2,top:2,bottom:-2,near:.5,far:10});keyL.shadow.radius=4;scene.add(keyL)
const rim=new THREE.DirectionalLight(0xa98bff,1.1);rim.position.set(-2,2.4,-2.8);scene.add(rim,new THREE.HemisphereLight(0xc4dcff,0x1e1530,.55))
const pad=new THREE.Group(),shadow=new THREE.Mesh(new THREE.CircleGeometry(1.7,70).rotateX(-Math.PI/2),new THREE.ShadowMaterial({opacity:.35}));shadow.receiveShadow=true
const ringM=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{t:{value:0}},vertexShader:'varying vec2 v;void main(){v=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec2 v;uniform float t;void main(){float r=length(v-.5)*2.;float g=smoothstep(.97,.9,r)*smoothstep(.7,.9,r)+.35*smoothstep(1.,.2,r)*(.5+.5*sin(r*28.-t*1.7))*smoothstep(.97,.8,r)*.35;vec3 c=mix(vec3(.5,.95,1.),vec3(.66,.55,1.),v.x);gl_FragColor=vec4(c*g,g);}'})
const ring=new THREE.Mesh(new THREE.PlaneGeometry(2.1,2.1).rotateX(-Math.PI/2),ringM);ring.position.y=.003;pad.add(shadow,ring);scene.add(pad)
const controls=new OrbitControls(camera,canvas);controls.target.set(0,.95,0);controls.enableDamping=true;controls.minDistance=1.1;controls.maxDistance=8;controls.maxPolarAngle=Math.PI*.57;controls.enablePan=false;controls.update()
function resize(){const w=innerWidth,h=innerHeight,lift=Math.min(140,h*.11);renderer.setSize(w,h,false);camera.aspect=w/h;camera.fov=w<h?42:35;mode==='xr'?camera.clearViewOffset():camera.setViewOffset(w,h,0,lift,w,h);camera.updateProjectionMatrix()}
addEventListener('resize',resize);resize()
const status=(t,ms)=>{const e=$('#status');e.textContent=t||'';e.hidden=!t;clearTimeout(status.h);t&&ms&&(status.h=setTimeout(()=>e.hidden=true,ms))}
const toast=(t,ms=5000)=>{const e=$('#toast');e.textContent=t;e.hidden=false;clearTimeout(toast.h);toast.h=setTimeout(()=>e.hidden=true,ms)}
const logLine=(cls,t)=>{const p=document.createElement('p');p.className=cls;p.textContent=t;const l=$('#log');l.append(p);l.scrollTop=l.scrollHeight;while(l.children.length>80)l.firstChild.remove()}
let bubbleT=0;const bubble=(t,thinking)=>{const b=$('#bubble');b.textContent=t;b.classList.toggle('thinking',!!thinking);b.hidden=!t;b.style.opacity=1;bubbleT=thinking?1e9:now()+Math.max(3500,t.length*70)}
const persona=()=>S.persona==='auto'?avMeta.persona:S.persona,cname=()=>S.cname||avMeta.name||'Companion'
function context(){const d=new Date(),seen=senses?.running&&senses.seenAt&&now()-senses.seenAt<60000?senses.seen.join(','):'';return{persona:persona(),name:S.name,cname:cname(),hour:d.getHours(),minute:d.getMinutes(),day:d.toLocaleDateString('en-US',{weekday:'long'}),seen,person:senses?.present?1:0,seed:Math.floor(Math.random()*1e6),timeText:d.toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'})}}
const userPos=()=>(xr?renderer.xr.getCamera():camera).getWorldPosition(new THREE.Vector3())
function floorToward(p,dist){const r=av.root.position,d=new THREE.Vector3(p.x-r.x,0,p.z-r.z),l=d.length();return l<=dist?r.clone():r.clone().add(d.multiplyScalar((l-dist)/l))}
function walkTo(p,o={}){if(!av)return;go={p:new THREE.Vector3(p.x,av.root.position.y,p.z),run:o.run,then:o.then};av.anim('idle')}
function act(kind,arg){
  if(!av)return
  if(kind==='emote')av.emote(arg)||av.anim(arg)
  else if(kind==='anim')av.anim(arg)||av.emote(arg)
  else if(kind==='walk'){roam=0;arg==='user'?walkTo(floorToward(userPos(),xr?.7:1.2)):arg==='home'?walkTo(home):arg==='roam'?(roam=3,nextRoam()):(go=null,av.loco(false))}
  else if(kind==='look')lookOff=arg==='user'?null:{dir:arg,until:now()+2500}
  else if(kind==='face')av.setFace({smile:'smile',happy:'smile',wink:'wink',surprised:'surprised',surprise:'surprised',sad:'sad'}[arg]||arg)
  else if(kind==='remember'){const m=/^name=(.{1,40})$/.exec(arg);m&&(S.name=m[1].trim(),save())}
}
function nextRoam(){if(roam-->0){const a=Math.random()*Math.PI*2,r=.5+Math.random()*1.1;walkTo(new THREE.Vector3(home.x+Math.cos(a)*r,0,home.z+Math.sin(a)*r),{then:()=>setTimeout(nextRoam,1400)})}}
function respond(reply,record){
  if(!reply)return;const{clean,tags}=core.tags(reply);record&&(history.push({role:'assistant',content:reply}),save());tags.forEach(t=>act(t.kind,t.arg))
  if(!clean)return;bubble(clean);logLine('bot',clean)
  if(S.speak&&voice.canSpeak){listener?.pause(true);voice.speak(clean,{voice:S.voice,persona:persona(),rate:S.rate,onstart:()=>{talking=true;av?.speaking(true)},onend:()=>{talking=false;av?.speaking(false);listener?.pause(false)}})}
  else{av?.speaking(true);setTimeout(()=>av?.speaking(false),Math.min(7000,clean.length*55))}
}
async function send(text){
  text=(text||'').trim();if(!text||!core)return;greeted=true;voice.hush();logLine('user',text);history.push({role:'user',content:text});save()
  const ctx=context(),offline=S.provider==='offline';let reply=''
  if(offline)reply=core.reply(ctx,text)
  else{busy=true;bubble('…',true);const img=senses?.running&&/\b(see|look|this|showing|holding|wearing|camera|what is it|what's this|how do i look)\b/i.test(text)?senses.snapshot():null
    try{ctrl=new AbortController();reply=await ask({...S,key:S.keys[S.provider]||''},ctx,history,img,ctrl.signal)}catch(e){e.name!=='AbortError'&&toast(`AI brain error: ${e.message}. Using the offline brain for now.`,7000);reply=core.reply(ctx,text)}busy=false}
  respond(reply||core.reply(ctx,text),true)
}
function onSense(e){
  if(e.name==='enter'||e.name==='leave')updateMirror()
  const ck=e.name==='object'?'object:'+e.label:e.name;if(!S.react||busy||talking||now()-lastReact<3500||e.name==='open_palm'||now()-(reacted[ck]||-1e9)<(COOL[e.name]||30000))return;reacted[ck]=now()
  const ptr=e.name==='point'?' '+((e.arg===1)===(S.camera==='user')?'left':'right'):'',u='@'+e.name+(e.name==='object'?' '+e.label:ptr),r=core.reply(context(),u)
  r&&(lastReact=now(),respond(r,false))
}
async function setCamera(on){
  if(!on){senses?.stop();roomView&&(camera.position.copy(roomView.p),controls.target.copy(roomView.t),controls.update(),roomView=null);xr||(home.set(0,0,0),pad.position.copy(home),av&&(go=null,av.root.position.copy(home)));document.body.classList.remove('camera','selfie');$('#camBtn').classList.remove('on');mode=xr?'xr':'room';av?.pose(null);updateMirror();pad.visible=true;ring.visible=true;return}
  try{senses=senses||new Senses(core,BASE,{event:onSense,ready:n=>n==='pose'&&status('Camera senses ready',2500),error:e=>toast('Recognition could not start: '+e.message,7000)});senses.cfg=S.senses;status('Starting camera…');await senses.start($('#cam'),S.camera);mode='camera';roomView=roomView||{p:camera.position.clone(),t:controls.target.clone()};camera.position.set(0,1.1,4.9);controls.target.set(0,1.2,0);controls.update();home.set(.62,0,0);pad.position.copy(home);av&&(go=null,av.root.position.copy(home));document.body.classList.add('camera');document.body.classList.toggle('selfie',S.camera==='user');$('#camBtn').classList.add('on');ring.visible=false;status('Loading recognition models…',4000);updateMirror()}
  catch(e){status('');toast(e.name==='NotAllowedError'?'Camera permission was denied. Allow it in your browser to use Camera AR.':'Camera unavailable: '+e.message,7000);setCamera(false)}
}
function updateMirror(){const c=$('#mirrorChip');c.hidden=mode!=='camera';c.classList.toggle('on',!!S.track);c.textContent=S.track?'Stop mirroring':'Mirror me'}
async function toggleAR(){
  if(xr){xr.end();return}
  try{setCamera(false);xr=await startAR(renderer,scene,$('#hud'),p=>{av&&(av.root.position.copy(p),home.copy(p),pad.position.copy(p),go=null)},()=>{xr=null;mode='room';av&&av.root.position.set(0,0,0);home.set(0,0,0);pad.position.set(0,0,0);ring.visible=true;$('#arBtn').classList.remove('on');document.body.classList.remove('xr')});mode='xr';ring.visible=false;$('#arBtn').classList.add('on');document.body.classList.add('xr');status('Point at the floor, then tap to place',5000)}
  catch(e){toast('AR could not start: '+e.message,7000)}
}
let yaw=0;function tick(t,frame){
  const dt=Math.min(.05,clock.getDelta());ringM.uniforms.t.value+=dt;xr?.frame(frame)
  if(av){const r=av.root
    if(go){const d=new THREE.Vector3(go.p.x-r.position.x,0,go.p.z-r.position.z),l=d.length();if(l>.04){av.loco(true,go.run);const want=Math.atan2(d.x,d.z);yaw+=Math.atan2(Math.sin(want-yaw),Math.cos(want-yaw))*Math.min(1,dt*7);r.position.addScaledVector(d.normalize(),Math.min(l,(go.run?2.1:.95)*r.scale.x*dt))}else{const th=go.then;go=null;av.loco(false);th?.()}}
    else if(!av.spin){const u=userPos(),want=Math.atan2(u.x-r.position.x,u.z-r.position.z),df=Math.atan2(Math.sin(want-yaw),Math.cos(want-yaw));Math.abs(df)>.35&&(yaw+=df*Math.min(1,dt*2.1))}
    r.rotation.y=yaw
    let lp=userPos();if(mode==='camera'&&senses?.nose){const n=senses.nose,s=S.camera==='user'?1:-1;lp=camera.localToWorld(new THREE.Vector3((.5-n[0])*s*-1.4,(.5-n[1])*.9,-.2))}
    if(lookOff){if(now()>lookOff.until)lookOff=null;else{const o={left:[-1.7,0],right:[1.7,0],up:[0,1.7]}[lookOff.dir]||[0,0];lp=r.localToWorld(new THREE.Vector3(o[0],1.5+o[1],1.4))}}
    av.lookAt(lp,go?0:.95)
    if(mode==='camera'&&S.track&&senses?.world){const res=core.pose(senses.world,S.mirror,now()/1000,av.slot,av.rest);av.pose(res.out,res.n?1:0)}else av.pose(null)
    av.update(dt)
    const b=$('#bubble');if(!b.hidden){const hb=av.bones[av.slot[5]],p=hb.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0,.32*r.scale.x,0)).project(xr?renderer.xr.getCamera():camera),x=(p.x*.5+.5)*innerWidth,y=(-p.y*.5+.5)*innerHeight;b.style.left=Math.max(110,Math.min(innerWidth-110,x))+'px';b.style.top=Math.max(120,Math.min(innerHeight-170,y))+'px';now()>bubbleT&&(b.style.opacity=0,now()>bubbleT+400&&(b.hidden=true))}}
  xr||controls.update();renderer.render(scene,camera)
}
async function modelBytes(id){if(id.startsWith('user:')){const m=await store.models.get(id);if(!m)throw new Error('That model is no longer saved here.');avMeta={name:m.name.replace(/\.(glb|vrm)$/i,''),persona:m.persona||'neutral'};return m.blob.arrayBuffer()}const k=id.replace('stock:',''),s=STOCK[k]||STOCK.holo;avMeta={name:s.cname||s.name,persona:s.persona};if(k==='mannequin')return new URL(s.file,BASE).href;const r=await fetch(new URL(s.file,BASE));if(!r.ok)throw new Error(`${s.name} isn't available yet.`);return r.arrayBuffer()}
async function useModel(id,quiet){
  status('Loading model…');try{const src=await modelBytes(id),next=await loadAvatar(core,src,lib);av?.dispose();av=next;scene.add(av.root);av.root.position.copy(home);av.root.scale.setScalar(S.scale);yaw=Math.atan2(camera.position.x,camera.position.z);S.model_id=id;save();$('#who').textContent=cname();renderModels();$('#rig').textContent=`Body parts matched: ${av.f.count} of 22.${av.morphs.open?' Talking mouth found.':''}${av.morphs.blink?' Blinks.':''}`;status('');quiet||respond(core.reply(context(),'who are you'),false)}
  catch(e){status('');toast(e.message,8000);if(!av&&id!=='stock:mannequin')return useModel(id==='stock:holo'?'stock:mannequin':'stock:holo',true)}
}
async function addFile(f){
  if(!f)return;if(!/\.(glb|vrm)$/i.test(f.name))return toast('Use a .glb or .vrm file (a single binary glTF).');if(f.size>200*1048576)return toast('That file is over 200 MB; try a lighter model.')
  status('Checking your model…');const buf=await f.arrayBuffer();try{const test=await loadAvatar(core,buf.slice(0),lib);test.dispose();const id=await store.models.put(f.name,buf);await useModel(id)}catch(e){status('');toast(e.message,9000)}
}
async function renderModels(){
  $('#stock').innerHTML='';for(const[k,s]of Object.entries(STOCK)){const b=document.createElement('button');b.className='card'+(S.model_id==='stock:'+k?' on':'');b.innerHTML=`<img alt="" src="${s.img}" onerror="this.outerHTML='<div class=ph></div>'"><b>${s.name}</b><br><small>${s.blurb}</small>`;b.onclick=()=>useModel('stock:'+k);$('#stock').append(b)}
  const mine=await store.models.list(),l=$('#mine');l.innerHTML=mine.length?'':'<p class="hint">None yet.</p>';for(const m of mine){const d=document.createElement('div');d.className='item'+(S.model_id===m.id?' on':'');d.innerHTML=`<span></span><small>${(m.size/1048576).toFixed(1)} MB</small><button class="ghost" aria-label="Delete">Delete</button>`;d.querySelector('span').textContent=m.name;d.querySelector('span').onclick=()=>useModel(m.id);d.querySelector('button').onclick=async()=>{await store.models.del(m.id);S.model_id===m.id?useModel('stock:holo'):renderModels()};l.append(d)}
}
function renderBrain(){const P=PROVIDERS[S.provider]||PROVIDERS.offline,off=P.kind==='offline';$('#provider').value=S.provider;['#r-base','#r-model'].forEach(s=>$(s).hidden=off);$('#r-key').hidden=off||!P.key;$('#base').value=S.provider===S.lastProvider&&S.base||P.base||'';$('#base').placeholder=P.base||'https://…/v1';$('#model').value=S.provider===S.lastProvider&&S.model||P.model||'';$('#key').value=S.keys[S.provider]||'';$('#brainNote').textContent=off?'':S.provider==='ollama'?'Ollama must allow this site: start it with OLLAMA_ORIGINS set to this page\'s origin.':S.provider==='lmstudio'?'Turn on CORS in LM Studio\'s server settings.':S.provider==='xai'||S.provider==='openai'?'If the service blocks browser requests, use OpenRouter with the same model instead.':''}
function bindSettings(){
  const sel=$('#provider');sel.innerHTML=Object.entries(PROVIDERS).map(([k,p])=>`<option value="${k}">${p.label}</option>`).join('');sel.onchange=()=>{S.provider=sel.value;S.base='';S.model='';S.lastProvider=S.provider;save();renderBrain()};renderBrain()
  $('#base').oninput=e=>{S.base=e.target.value.trim();S.lastProvider=S.provider;save()};$('#model').oninput=e=>{S.model=e.target.value.trim();S.lastProvider=S.provider;save()};$('#key').oninput=e=>{S.keys={...S.keys,[S.provider]:e.target.value.trim()};save()}
  $('#showKey').onclick=()=>{const k=$('#key');k.type=k.type==='password'?'text':'password';$('#showKey').textContent=k.type==='password'?'Show':'Hide'}
  $('#personality').value=S.personality;$('#personality').oninput=e=>{S.personality=e.target.value;save()}
  $('#remember').checked=S.remember;$('#remember').onchange=e=>{S.remember=e.target.checked;save()};$('#forget').onclick=()=>{history=[];save();$('#log').innerHTML='';toast('Conversation cleared.')}
  $('#testBrain').onclick=async()=>{if(S.provider==='offline')return toast('The offline brain is always ready.');status('Testing…');try{const r=await ask({...S,key:S.keys[S.provider]||''},context(),[{role:'user',content:'Say hello in five words or fewer.'}]);status('');toast('Connected: '+core.tags(r).clean,7000)}catch(e){status('');toast('Failed: '+e.message,9000)}}
  $('#scale').value=S.scale;$('#scale').oninput=e=>{S.scale=+e.target.value;av?.root.scale.setScalar(S.scale);save()}
  $('#cname').value=S.cname;$('#cname').oninput=e=>{S.cname=e.target.value.trim();$('#who').textContent=cname();save()}
  $('#persona').value=S.persona;$('#persona').onchange=e=>{S.persona=e.target.value;save()}
  $('#camera').value=S.camera;$('#camera').onchange=e=>{S.camera=e.target.value;S.mirror=S.camera==='user';$('#mirror').checked=S.mirror;save();mode==='camera'&&setCamera(true)}
  $$('[data-sense]').forEach(c=>{c.checked=S.senses[c.dataset.sense];c.onchange=()=>{S.senses={...S.senses,[c.dataset.sense]:c.checked};senses&&(senses.cfg=S.senses);save()}})
  $('#react').checked=S.react;$('#react').onchange=e=>{S.react=e.target.checked;save()};$('#mirror').checked=S.mirror;$('#mirror').onchange=e=>{S.mirror=e.target.checked;save()}
  $('#speak').checked=S.speak;$('#speak').onchange=e=>{S.speak=e.target.checked;S.speak||voice.hush();save()}
  const fillVoices=()=>{const v=voice.voices();$('#voice').innerHTML='<option value="">Automatic</option>'+v.map(x=>`<option value="${x.voiceURI.replace(/"/g,'&quot;')}">${x.name} (${x.lang})</option>`).join('');$('#voice').value=S.voice};fillVoices();speechSynthesis?.addEventListener?.('voiceschanged',fillVoices)
  $('#voice').onchange=e=>{S.voice=e.target.value;save()};$('#rate').value=S.rate;$('#rate').oninput=e=>{S.rate=+e.target.value;save()}
  $('#listen').value=S.listen;$('#listen').onchange=e=>{S.listen=e.target.value;listener?.stop();save()}
  $('#voiceNote').textContent=voice.canListen?'':'This browser has no speech recognition; you can still type.';$('#mic').hidden=!voice.canListen
  $('#wipe').onclick=async()=>{if(!confirm('Erase all models, settings, keys and conversation saved by Amni-Companion in this browser?'))return;await store.wipe();location.reload()}
  $('#ver').textContent=VERSION
}
function bindUI(){
  $$('nav [data-panel]').forEach(b=>b.onclick=()=>{const p=$('#p-'+b.dataset.panel),open=p.hidden;$$('.panel').forEach(x=>x.hidden=true);$$('nav [data-panel]').forEach(x=>x.classList.remove('on'));p.hidden=!open;b.classList.toggle('on',open);open&&b.dataset.panel==='models'&&renderModels()})
  $$('.panel .x').forEach(x=>x.onclick=()=>{x.closest('.panel').hidden=true;$$('nav [data-panel]').forEach(b=>b.classList.remove('on'))})
  $('#chat').onsubmit=e=>{e.preventDefault();const v=$('#say').value;$('#say').value='';send(v)}
  $('#logBtn').onclick=()=>{const l=$('#log');l.hidden=!l.hidden;$('#logBtn').classList.toggle('on',!l.hidden)}
  $$('#chips button').forEach(b=>b.onclick=()=>{if(b.dataset.say)return send(b.dataset.say);const a=b.dataset.act;if(a==='mirror'){S.track=!S.track;save();updateMirror();return}if(a==='sit'){av?.sitting?act('anim','stand'):act('anim','sit');b.textContent=av?.sitting?'Stand':'Sit';return}const[k,v]=a.split(':');act(k,v)})
  $('#camBtn').onclick=()=>setCamera(mode!=='camera');$('#arBtn').onclick=toggleAR
  $('#file').onchange=e=>{addFile(e.target.files[0]);e.target.value=''}
  let dz=0;addEventListener('dragenter',e=>{e.preventDefault();dz++;$('#drop').hidden=false});addEventListener('dragleave',()=>{--dz<=0&&($('#drop').hidden=true,dz=0)});addEventListener('dragover',e=>e.preventDefault());addEventListener('drop',e=>{e.preventDefault();dz=0;$('#drop').hidden=true;addFile(e.dataTransfer.files[0])})
  listener=new voice.Listener(t=>send(t),st=>{$('#mic').classList.toggle('listening',st==='listening'||st==='on');st==='denied'&&toast('Microphone permission was denied.')})
  $('#mic').onclick=async()=>{if(listener.on){listener.stop();return}try{await listener.start(S.listen==='hands',S.lang)}catch(e){toast(e.message)}}
  document.addEventListener('visibilitychange',()=>document.hidden&&voice.hush())
}
async function boot(){
  try{
    $('#loadMsg').textContent='Starting the Helium core…';core=await loadCore(new URL('companion.wasm',BASE));globalThis.amniCore=core
    $('#loadMsg').textContent='Loading animations…';lib=await loadLibrary(core,new URL('anim/AnimationLibrary_Godot_Standard.gltf',BASE).href)
    bindUI();bindSettings();$('#loadMsg').textContent='Bringing your companion in…';await useModel(S.model_id,true)
    renderer.setAnimationLoop(tick);$('#loading').classList.add('done');setTimeout(()=>greeted||respond(core.reply(context(),'hello'),false),700)
    history.forEach(h=>logLine(h.role==='user'?'user':'bot',h.role==='user'?h.content:core.tags(h.content).clean))
    arSupported().then(ok=>$('#arBtn').hidden=!ok)
    'serviceWorker'in navigator&&location.protocol==='https:'&&navigator.serviceWorker.register('sw.js').catch(()=>{})
  }catch(e){console.error(e);$('#loadMsg').textContent='Could not start: '+e.message}
}
boot()
globalThis.amni={get av(){return av},get core(){return core},send,act,useModel,setCamera,get S(){return S}}
