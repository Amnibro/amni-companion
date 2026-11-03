export const COCO=['person','bicycle','car','motorcycle','airplane','bus','train','truck','boat','traffic light','fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow','elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee','skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle','wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange','broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant','bed','dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone','microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear','hair drier','toothbrush']
const GEST={None:0,Closed_Fist:1,Open_Palm:2,Pointing_Up:3,Thumb_Down:4,Thumb_Up:5,Victory:6,ILoveYou:7}
export class Senses{
  constructor(core,base,on){this.core=core;this.base=base;this.on=on;this.tasks={};this.video=null;this.stream=null;this.running=false;this.n=0;this.present=false;this.nose=null;this.seen=[];this.world=null;this.cfg={pose:true,hands:true,face:true,objects:true}}
  async start(video,facing='user'){
    this.stop();this.video=video;this.facing=facing
    this.stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:facing,width:{ideal:640},height:{ideal:480}},audio:false});video.srcObject=this.stream;video.muted=true;video.playsInline=true;await video.play()
    this.running=true;this.loading=this.loading||this.load().catch(e=>{this.loading=null;this.on.error?.(e)});this.loop()}
  async load(){
    const V=await import('../vendor/mediapipe/vision_bundle.mjs'),fs=await V.FilesetResolver.forVisionTasks(new URL('vendor/mediapipe',this.base).href.replace(/\/?$/,'')),m=f=>new URL('vendor/mediapipe/'+f,this.base).href
    const mk=async(C,o)=>{try{return await C.createFromOptions(fs,{...o,baseOptions:{...o.baseOptions,delegate:'GPU'},runningMode:'VIDEO'})}catch{return C.createFromOptions(fs,{...o,baseOptions:{...o.baseOptions,delegate:'CPU'},runningMode:'VIDEO'})}}
    this.tasks.pose=await mk(V.PoseLandmarker,{baseOptions:{modelAssetPath:m('pose_landmarker_lite.task')},numPoses:1});this.on.ready?.('pose')
    this.tasks.hands=await mk(V.GestureRecognizer,{baseOptions:{modelAssetPath:m('gesture_recognizer.task')},numHands:2});this.on.ready?.('hands')
    this.tasks.face=await mk(V.FaceLandmarker,{baseOptions:{modelAssetPath:m('face_landmarker.task')},numFaces:1,outputFaceBlendshapes:true,outputFacialTransformationMatrixes:true});this.on.ready?.('face')
    this.tasks.objects=await mk(V.ObjectDetector,{baseOptions:{modelAssetPath:m('efficientdet_lite0.tflite')},scoreThreshold:.5,maxResults:5});this.on.ready?.('objects')
  }
  loop(){if(!this.running)return;const v=this.video;v.requestVideoFrameCallback?v.requestVideoFrameCallback(()=>this.tick()):requestAnimationFrame(()=>this.tick())}
  tick(){
    if(!this.running)return;const v=this.video,t=performance.now(),n=this.n++,T=this.tasks,c=this.cfg
    if(v.readyState>=2&&v.videoWidth&&t-(this.last||0)>=45){this.last=t
      const pose=new Float64Array(134),hands=new Float64Array(4),face=new Float64Array(55),objs=new Float64Array(17)
      pose[133]=v.videoWidth/v.videoHeight
      try{if(T.pose&&(c.pose||this.track)){const r=T.pose.detectForVideo(v,t),lm=r.landmarks?.[0],wl=r.worldLandmarks?.[0];if(lm){pose[132]=1;lm.forEach((p,i)=>pose.set([p.x,p.y,p.z,p.visibility??1],4*i));this.nose=[lm[0].x,lm[0].y];if(wl){const w=new Float64Array(132);wl.forEach((p,i)=>w.set([p.x,p.y,p.z,lm[i].visibility??1],4*i));this.world=w}}else this.world=null}}catch{}
      try{if(T.hands&&c.hands&&n%2===0){const r=T.hands.recognizeForVideo(v,t);(r.gestures||[]).slice(0,2).forEach((g,i)=>hands.set([GEST[g[0]?.categoryName]||0,g[0]?.score||0],2*i));this.hands=hands}else this.hands&&hands.set(this.hands)}catch{}
      try{if(T.face&&c.face&&n%2===1){const r=T.face.detectForVideo(v,t),bs=r.faceBlendshapes?.[0]?.categories,mx=r.facialTransformationMatrixes?.[0]?.data;if(bs){bs.forEach(b=>b.index<52&&(face[b.index]=b.score));if(mx){face[52]=Math.atan2(mx[8],mx[10]);face[53]=Math.asin(Math.max(-1,Math.min(1,-mx[9])))}face[54]=1}this.face=face}else this.face&&face.set(this.face)}catch{}
      try{if(T.objects&&c.objects&&n%7===3){const r=T.objects.detectForVideo(v,t);let k=0;for(const d of r.detections||[]){const cat=d.categories?.[0],id=COCO.indexOf(cat?.categoryName);if(id<0||k>=8)continue;objs.set([id,cat.score],2*k);k++}objs[16]=k;this.objs=objs;for(let i=0;i<k;i++){const l=COCO[objs[2*i]];l!=='person'&&(this.seen=[l,...this.seen.filter(x=>x!==l)].slice(0,4),this.seenAt=t)}}else this.objs&&objs.set(this.objs)}catch{}
      this.present=pose[132]>.5;const ev=this.core.sense(t/1000,pose,hands,face,objs);for(const e of ev)this.on.event?.({...e,label:e.name==='object'?COCO[e.arg]:''})
      this.on.frame?.(this)}
    this.loop()}
  snapshot(w=512){const v=this.video;if(!v?.videoWidth)return null;const c=document.createElement('canvas'),s=w/Math.max(v.videoWidth,v.videoHeight);c.width=Math.round(v.videoWidth*s);c.height=Math.round(v.videoHeight*s);c.getContext('2d').drawImage(v,0,0,c.width,c.height);return c.toDataURL('image/jpeg',.82)}
  stop(){this.running=false;this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;this.video&&(this.video.srcObject=null);this.present=false;this.world=null;this.core.senseReset();this.core.poseReset()}
}
