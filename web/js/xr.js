import * as THREE from 'three'
export async function arSupported(){try{return!!(navigator.xr&&await navigator.xr.isSessionSupported('immersive-ar'))}catch{return false}}
export async function startAR(renderer,scene,overlay,onPlace,onEnd){
  const s=await navigator.xr.requestSession('immersive-ar',{requiredFeatures:['hit-test'],optionalFeatures:['local-floor','dom-overlay','light-estimation'],domOverlay:{root:overlay}})
  renderer.xr.enabled=true;renderer.xr.setReferenceSpaceType('local');await renderer.xr.setSession(s)
  const viewer=await s.requestReferenceSpace('viewer'),src=await s.requestHitTestSource({space:viewer}),reticle=new THREE.Mesh(new THREE.RingGeometry(.11,.14,40).rotateX(-Math.PI/2),new THREE.MeshBasicMaterial({color:0x7ff3ff,transparent:true,opacity:.85}))
  reticle.matrixAutoUpdate=false;reticle.visible=false;scene.add(reticle);let placed=false
  const hit=f=>{const h=f.getHitTestResults(src)[0],ref=renderer.xr.getReferenceSpace(),p=h&&h.getPose(ref);reticle.visible=!!p;p&&reticle.matrix.fromArray(p.transform.matrix)}
  s.addEventListener('select',()=>{if(!reticle.visible)return;const p=new THREE.Vector3().setFromMatrixPosition(reticle.matrix);onPlace(p);placed=true})
  s.addEventListener('end',()=>{src.cancel?.();reticle.removeFromParent();renderer.xr.enabled=false;onEnd()})
  return{session:s,frame:f=>f&&hit(f),get placed(){return placed},end:()=>s.end()}
}
