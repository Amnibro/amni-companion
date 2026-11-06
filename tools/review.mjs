import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..'),[,,glb,out]=process.argv,T={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.gltf':'model/gltf+json','.glb':'model/gltf-binary'}
const V=[['Front','rest',0,0,1,4.2,.88],['Three-quarter back','rest',0,135,1,4.2,.88],['Side','rest',0,90,1,4.2,.88],['Back','rest',0,180,1,4.2,.88],['Back of head','rest',0,180,1.5,1.2,1.45],['Side of head','rest',0,90,1.5,1.2,1.45],['Back of torso','rest',0,180,1.1,1.8,1.05],['Shoes','rest',0,150,.2,1.4,.15],['Walk','Walk_Loop',.3,150,1,4.2,.88],['Sit','Sitting_Idle_Loop',1,200,.8,4.2,.6],['Dance','Dance_Loop',1,160,1,4.2,.88],['Idle','Relax_Loop',1,30,1,4.2,.88]]
const {chromium}=createRequire(path.join(process.env.PW||path.join(process.env.HOME,'ai/amni-games/amni-splash/node_modules'),'/'))('playwright-core')
const srv=http.createServer((q,s)=>{const u=decodeURIComponent(q.url.split('?')[0]),f=u.startsWith('/@glb')?path.resolve(glb):u.startsWith('/@cloth')?path.resolve(glb).replace(/\.glb$/,'.cloth'):path.join(root,path.normalize(u));fs.readFile(f,(e,d)=>{s.writeHead(e?404:200,{'content-type':T[path.extname(f)]||'application/octet-stream'});s.end(e?'':d)})}).listen(0,'127.0.0.1')
await new Promise(o=>srv.once('listening',o))
const b=await chromium.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome-stable',headless:true,args:['--enable-unsafe-webgpu','--enable-features=Vulkan','--use-angle=vulkan','--no-first-run']})
try{const p=await b.newPage({viewport:{width:384,height:576}});p.on('pageerror',e=>console.log('pageerror',e.message));await p.goto(`http://127.0.0.1:${srv.address().port}/tools/review.html`);await p.waitForFunction(()=>globalThis.ready,null,{timeout:180000})
  await p.evaluate(()=>load('/@glb'));const shots=[],stats=[];for(const v of V){await p.evaluate(v=>pose(v),v);await p.waitForTimeout(1500);shots.push((await p.screenshot()).toString('base64'));stats.push({view:v[0],garments:await p.evaluate(()=>stats())})}
  const d=await p.evaluate(([s,l])=>sheet(s,l,4),[shots,V.map(v=>v[0])]);fs.writeFileSync(out,Buffer.from(d.split(',')[1],'base64'));fs.writeFileSync(out.replace(/\.png$/,'')+'.cloth.json',JSON.stringify(stats));console.log('review sheet',out);for(const x of stats)console.log(x.view,JSON.stringify(x.garments))}
finally{await b.close();srv.close()}
