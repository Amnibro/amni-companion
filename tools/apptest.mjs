import http from 'node:http'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import zlib from 'node:zlib'
import {createRequire} from 'node:module'
const root=path.resolve(process.env.WEB||path.join(path.dirname(new URL(import.meta.url).pathname),'../web')),T={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.gltf':'model/gltf+json','.glb':'model/gltf-binary'}
const {chromium}=createRequire(path.join(process.env.PW||path.join(process.env.HOME,'ai/amni-games/amni-splash/node_modules'),'/'))('playwright-core')
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'companion-app.')),cam=path.join(tmp,'cam.y4m'),CW=640,CH=480,lum=Buffer.from({length:CW*CH},(_,i)=>40+(i%CW*150/CW|0)+((i/CW|0)*60/CH|0))
fs.writeFileSync(cam,Buffer.concat([Buffer.from(`YUV4MPEG2 W${CW} H${CH} F5:1 Ip A1:1 C420jpeg\n`),...Array(5).fill(Buffer.concat([Buffer.from('FRAME\n'),lum,Buffer.alloc(CW*CH/2,128)]))]))
const srv=http.createServer((q,s)=>{const u=decodeURIComponent(q.url.split('?')[0]),f=path.join(root,path.normalize(u.endsWith('/')?u+'index.html':u));fs.readFile(f,(e,d)=>{s.writeHead(e?404:200,{'content-type':T[path.extname(f)]||'application/octet-stream'});s.end(e?'':d)})}).listen(0,'127.0.0.1')
await new Promise(o=>srv.once('listening',o))
const png=b=>{let o=8,w=0,h=0,ch=0;const id=[];while(o<b.length){const n=b.readUInt32BE(o),t=b.toString('latin1',o+4,o+8),d=b.subarray(o+8,o+8+n);t==='IHDR'?(w=d.readUInt32BE(0),h=d.readUInt32BE(4),ch=d[9]===6?4:3):t==='IDAT'&&id.push(d);o+=12+n}const r=zlib.inflateSync(Buffer.concat(id)),s=w*ch,px=Buffer.alloc(s*h);for(let y=0;y<h;y++){const f=r[y*(s+1)],q=y*s;for(let x=0;x<s;x++){const a=x>=ch?px[q+x-ch]:0,u=y?px[q-s+x]:0,c=x>=ch&&y?px[q-s+x-ch]:0,e=a+u-c,ea=Math.abs(e-a),eu=Math.abs(e-u),ec=Math.abs(e-c);px[q+x]=r[y*(s+1)+1+x]+(f===1?a:f===2?u:f===3?a+u>>1:f===4?(ea<=eu&&ea<=ec?a:eu<=ec?u:c):0)}}return{w,h,ch,px}}
const differ=(a,b)=>{const x=png(a),y=png(b);let n=0;for(let i=0;i<x.w*x.h;i++){const o=i*x.ch,k=i*y.ch;Math.abs(x.px[o]-y.px[k])+Math.abs(x.px[o+1]-y.px[k+1])+Math.abs(x.px[o+2]-y.px[k+2])>48&&n++}return n/(x.w*x.h)}
let fail=0
const ok=(c,m,x='')=>{console.log((c?'PASS ':'FAIL ')+m+(x?' ('+x+')':''));c||fail++}
const b=await chromium.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome-stable',headless:true,args:['--enable-unsafe-webgpu','--enable-features=Vulkan','--use-angle=vulkan','--no-first-run','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-video-capture='+cam,'--autoplay-policy=no-user-gesture-required']})
try{
  const p=await b.newPage({viewport:{width:900,height:700}}),errs=[]
  p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>m.type()==='error'&&errs.push(m.text()))
  const settled=()=>p.waitForFunction(()=>document.getElementById('loading').classList.contains('done')&&document.getElementById('hestage')&&document.getElementById('status').hidden,null,{timeout:240000,polling:500}).then(()=>true,()=>false)
  const shown=s=>p.waitForSelector(s,{state:'visible',timeout:30000}).then(()=>true,()=>false)
  const panel=k=>p.click('button[data-panel='+k+']').then(()=>shown('#p-'+k))
  const close=async k=>{await p.click('#p-'+k+' .x');await p.waitForSelector('#p-'+k,{state:'hidden',timeout:10000})}
  const pick=async n=>{await p.click('#stock .card:has(b:text-is("'+n+'"))');await p.waitForTimeout(1500);return settled()}
  const mode=on=>p.waitForFunction(v=>document.body.classList.contains('camera')===v,on,{timeout:60000}).then(()=>true,()=>false)
  await p.goto(`http://127.0.0.1:${srv.address().port}/`)
  ok(await settled(),'app starts and the default model loads');await p.waitForTimeout(4000)
  const feet=await p.evaluate(()=>new Promise(done=>{const a=globalThis.amni,pr=[null,null],rnd=Math.random,t0=performance.now();let s=0,n=0,sd=7;Math.random=()=>(sd=sd*16807%2147483647)/2147483647;a.act('walk','roam');const f=()=>{const L=a.av.live;for(const k of[0,1]){const m=a.av.v.foot(k),q=[L[196+48*k],L[198+48*k],m];pr[k]&&pr[k][2]===1&&m===1&&(s+=Math.hypot(q[0]-pr[k][0],q[1]-pr[k][1]),n++);pr[k]=q}performance.now()-t0<7000?requestAnimationFrame(f):(Math.random=rnd,a.act('walk','stop'),done([s,n]))};requestAnimationFrame(f)}))
  ok(feet[1]>60&&feet[0]<.03,'planted feet stay put on a walk',(feet[0]*1000).toFixed(1)+' mm over '+feet[1]+' planted frames');await p.waitForTimeout(1500)
  ok(await panel('models'),'Models panel opens')
  const cards=(await p.locator('#stock .card b').allTextContents()).join()
  ok(cards==='Holo,Dex,Mannequin','stock models listed',cards)
  ok(await p.isVisible('#look'),'Look panel shown');await p.click('#lk-apply');await p.waitForTimeout(4000);ok(await p.isHidden('#status'),'Apply look settles')
  ok(await pick('Dex'),'Dex loads');await close('models');await p.waitForTimeout(4000)
  await p.click('button[data-say="Tell me a joke"]');ok(await shown('#bubble'),'Joke chip gets a reply')
  await p.click('#say');await p.keyboard.type('hello there');await p.click('#send');ok(await shown('#bubble'),'typed message gets a reply')
  ok(await panel('models')&&await pick('Holo'),'back to Holo');await close('models')
  ok(await panel('settings'),'Settings panel opens');await close('settings');ok(await panel('brain'),'AI brain panel opens');await close('brain')
  const over=async()=>{const solo=await p.addStyleTag({content:'body>*:not(#cam):not(#hestage){visibility:hidden!important}'});await p.waitForTimeout(400);const both=await p.screenshot(),hide=await p.addStyleTag({content:'#hestage{visibility:hidden!important}'});await p.waitForTimeout(400);const f=differ(both,await p.screenshot());await hide.evaluate(e=>e.remove());await solo.evaluate(e=>e.remove());return f}
  const ar=async m=>{await p.click('#camBtn');ok(await mode(true),'Camera AR starts'+m);await p.waitForTimeout(8000);const f=await over();ok(f>0.004&&f<0.5,'companion stands over the camera picture'+m,(100*f).toFixed(1)+' % of the screen');await p.click('#camBtn');ok(await mode(false),'Camera AR stops'+m)}
  await ar('')
  ok(await panel('models'),'Models panel reopens');const[fc]=await Promise.all([p.waitForEvent('filechooser'),p.click('label.file')])
  await fc.setFiles({name:'my model.glb',mimeType:'model/gltf-binary',buffer:fs.readFileSync(path.join(root,'models/dex.glb'))});await p.waitForTimeout(1500)
  const mine=await settled()&&(await p.locator('#mine .item span').allTextContents()).join();ok(mine==='my model.glb','your own .glb loads',String(mine));await close('models');await p.waitForTimeout(4000)
  await ar(', your own model')
  const real=errs.filter(e=>!/favicon|Failed to load resource|TensorFlow Lite|NotAllowedError|Permission|speech|SpeechSynthesis|getUserMedia/i.test(e))
  ok(real.length===0,'no page errors',real.slice(0,4).join(' | ').slice(0,400))
}finally{await b.close();srv.close();fs.rmSync(tmp,{recursive:true,force:true})}
console.log(fail?fail+' FAILED':'ALL PASS');process.exit(fail?1:0)
