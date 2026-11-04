import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..'),[,,glb,out]=process.argv,T={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.gltf':'model/gltf+json','.glb':'model/gltf-binary'}
const V=[['Front','rest',0,0,1,4.2,.88],['Three-quarter back','rest',0,135,1,4.2,.88],['Side','rest',0,90,1,4.2,.88],['Back','rest',0,180,1,4.2,.88],['Back of head','rest',0,180,1.5,1.2,1.45],['Side of head','rest',0,90,1.5,1.2,1.45],['Back of torso','rest',0,180,1.1,1.8,1.05],['Shoes','rest',0,150,.2,1.4,.15],['Walk','Walk_Loop',.3,150,1,4.2,.88],['Sit','Sitting_Idle_Loop',1,200,.8,4.2,.6],['Dance','Dance_Loop',1,160,1,4.2,.88],['Idle','Relax_Loop',1,30,1,4.2,.88]]
const {chromium}=createRequire(path.join(process.env.PW||path.join(process.env.HOME,'ai/amni-games/amni-splash/node_modules'),'/'))('playwright-core')
const srv=http.createServer((q,s)=>{const u=decodeURIComponent(q.url.split('?')[0]),f=u.startsWith('/@glb')?path.resolve(glb):path.join(root,path.normalize(u));fs.readFile(f,(e,d)=>{s.writeHead(e?404:200,{'content-type':T[path.extname(f)]||'application/octet-stream'});s.end(e?'':d)})}).listen(0,'127.0.0.1')
await new Promise(o=>srv.once('listening',o))
const b=await chromium.launch({executablePath:process.env.CHROME||path.join(process.env.HOME,'.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'),args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']})
try{const p=await b.newPage();p.on('pageerror',e=>console.log('pageerror',e.message));await p.goto(`http://127.0.0.1:${srv.address().port}/tools/review.html`);await p.waitForFunction(()=>globalThis.ready,null,{timeout:180000})
  const d=await p.evaluate(([v])=>review('/@glb',v),[V]);fs.writeFileSync(out,Buffer.from(d.split(',')[1],'base64'));console.log('review sheet',out)}
finally{await b.close();srv.close()}
