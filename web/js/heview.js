import {start} from '../heview/helium.js'
export async function heView(canvas,glb,o={}){
  const V={},keep=(id,p,n)=>{V[id]=[Number(p),Number(n)]},te=new TextEncoder()
  const rt=await start({wasm:o.wasm||new URL('../heview/view.wasm',import.meta.url).href,canvas,files:{'/m/avatar.glb':glb},args:['view','/m/avatar.glb'],imports:{hv_f32:keep,hv_bytes:keep}})
  await rt.done
  const f32=id=>new Float32Array(rt.mem().buffer,V[id][0],V[id][1]),u8=id=>new Uint8Array(rt.mem().buffer,V[id][0],V[id][1])
  return{rt,bones:names=>{const b=te.encode(names.join('\n'));u8(2).set(b);return rt.call('hv_bones',b.length)},pose:a=>f32(0).set(a),camera:(eye,target,fov)=>f32(1).set([...eye,...target,fov])}
}
