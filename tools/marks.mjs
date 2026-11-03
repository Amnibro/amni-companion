import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..'),[,,model,out]=process.argv,T={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json','.png':'image/png','.gltf':'model/gltf+json'}
const {chromium}=createRequire(process.env.PW||path.join(process.env.HOME,'ai/amni-games/amni-splash/node_modules/'))('playwright-core')
const srv=http.createServer((q,s)=>{const f=q.url.startsWith('/@model')?path.resolve(path.dirname(model),decodeURIComponent(q.url.slice(8).split('?')[0])):path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(f,(e,d)=>{s.writeHead(e?404:200,{'content-type':T[path.extname(f)]||'application/octet-stream'});s.end(e?'':d)})}).listen(0,'127.0.0.1')
await new Promise(o=>srv.once('listening',o))
const b=await chromium.launch({executablePath:process.env.CHROME||path.join(process.env.HOME,'.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'),args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']})
try{const p=await b.newPage();await p.goto(`http://127.0.0.1:${srv.address().port}/tools/marks.html`);await p.waitForFunction(()=>globalThis.ready,null,{timeout:120000})
  const r=await p.evaluate(u=>marks(u),'/@model/'+encodeURIComponent(path.basename(model)));fs.writeFileSync(out,JSON.stringify({pts:r.pts||null,missed:r.missed,error:r.error}));fs.writeFileSync(out.replace(/\.json$/,'.jpg'),Buffer.from((r.img||'').split(',')[1]||'','base64'));console.log(out,r.error||`${r.pts.length} landmarks, ${r.missed} missed`)}
finally{await b.close();srv.close()}
