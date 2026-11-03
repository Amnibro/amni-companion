import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..'),cache=process.env.MP_CACHE||path.join(process.env.HOME,'.cache/amni-companion/mediapipe'),[,,img,out]=process.argv,T={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.png':'image/png'},G='https://storage.googleapis.com/mediapipe-models/'
fs.mkdirSync(cache,{recursive:true})
for(const[f,u]of[['pose_landmarker_heavy.task','pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task'],['selfie_multiclass_256x256.tflite','image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite']])fs.existsSync(path.join(cache,f))||fs.writeFileSync(path.join(cache,f),Buffer.from(await (await fetch(G+u)).arrayBuffer()))
const {chromium}=createRequire(path.join(process.env.PW||path.join(process.env.HOME,'ai/amni-games/amni-splash/node_modules'),'/'))('playwright-core')
const srv=http.createServer((q,s)=>{const u=decodeURIComponent(q.url.split('?')[0]),f=u.startsWith('/@img')?path.resolve(img):u.startsWith('/@cache/')?path.join(cache,path.basename(u)):path.join(root,path.normalize(u));fs.readFile(f,(e,d)=>{s.writeHead(e?404:200,{'content-type':T[path.extname(f)]||'application/octet-stream'});s.end(e?'':d)})}).listen(0,'127.0.0.1')
await new Promise(o=>srv.once('listening',o))
const b=await chromium.launch({executablePath:process.env.CHROME||path.join(process.env.HOME,'.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'),args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']})
try{const p=await b.newPage();p.on('pageerror',e=>console.log('pageerror',e.message));await p.goto(`http://127.0.0.1:${srv.address().port}/tools/analyze.html`);await p.waitForFunction(()=>globalThis.ready,null,{timeout:180000})
  const r=await p.evaluate(()=>analyze('/@img'));fs.writeFileSync(out.replace(/\.json$/,'_cls.png'),Buffer.from(r.classes.split(',')[1],'base64'));delete r.classes;fs.writeFileSync(out,JSON.stringify(r));console.log(out,'pose',r.pose?r.pose.length:0,'face',r.face?r.face.length:0)}
finally{await b.close();srv.close()}
