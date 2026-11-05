import {start} from '../heview/helium.js'
export async function heView(canvas,glb,o={}){
  const V={},keep=(id,p,n)=>{V[id]=[Number(p),Number(n)]},te=new TextEncoder()
  const rt=await start({wasm:o.wasm||new URL('../heview/view.wasm',import.meta.url).href,canvas,files:{'/m/avatar.glb':glb},args:['view','/m/avatar.glb'],imports:{hv_f32:keep,hv_i32:keep,hv_bytes:keep}})
  await rt.done
  const view=(T,id)=>new T(rt.mem().buffer,V[id][0],V[id][1])
  return{rt,bones:names=>{const b=te.encode(names.join('\n'));view(Uint8Array,2).set(b);return rt.call('hv_bones',b.length)},nodes:ix=>{view(Int32Array,3).set(ix);return rt.call('hv_nodes',ix.length)},pose:a=>view(Float32Array,0).set(a),place:m=>view(Float32Array,4).set(m),camera:(eye,target,fov,pad=[0,0,0])=>view(Float32Array,1).set([...eye,...target,fov,0,...pad]),stop:()=>rt.call('hv_stop')}
}
export async function heMirror(av,glb){
  const cv=document.createElement('canvas');cv.id='hestage';cv.style.cssText='position:fixed;left:0;top:0;width:100%;height:100%;pointer-events:none';document.body.prepend(cv)
  const v=await heView(cv,glb),objs=[...av.byNode],P=new Float32Array(10*objs.length)
  v.nodes(objs.map(x=>x[0]));av.g.scene.traverse(o=>o.isMesh&&(o.visible=false))
  return{v,cv,sync(cam,pad){objs.forEach(([,o],k)=>P.set([o.position.x,o.position.y,o.position.z,o.quaternion.x,o.quaternion.y,o.quaternion.z,o.quaternion.w,o.scale.x,o.scale.y,o.scale.z],10*k));v.pose(P);v.place(av.g.scene.matrixWorld.elements)
    const m=cam.matrixWorld.elements,h=innerHeight,lift=cam.view?.enabled?cam.view.offsetY:0;cv.style.top=-2*lift+'px';cv.style.height=h+2*lift+'px'
    v.camera([m[12],m[13],m[14]],[m[12]-m[8],m[13]-m[9],m[14]-m[10]],2*Math.atan(Math.tan(cam.fov*Math.PI/360)*(h+2*lift)/h),pad?[pad.x,pad.y,pad.z]:[0,0,0])},
    dispose(){v.stop();cv.remove()}}
}
