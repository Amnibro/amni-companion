const KEY='amni-companion:settings',DB='amni-companion'
export const DEFAULTS={provider:'offline',base:'',model:'',key:'',keys:{},persona:'auto',cname:'',name:'',personality:'',model_id:'stock:holo',scale:1,speak:true,voice:'',rate:1,listen:'push',lang:'',senses:{pose:true,hands:true,face:true,objects:true},react:true,mirror:true,track:false,camera:'user',remember:false,history:[]}
export function load(){try{const s=JSON.parse(localStorage.getItem(KEY)||'{}');return{...DEFAULTS,...s,senses:{...DEFAULTS.senses,...s.senses}}}catch{return{...DEFAULTS}}}
export function save(s){try{localStorage.setItem(KEY,JSON.stringify({...s,history:s.remember?s.history.slice(-40):[]}))}catch{}}
export function wipe(){try{localStorage.removeItem(KEY)}catch{}return new Promise(r=>{try{const q=indexedDB.deleteDatabase(DB);q.onsuccess=q.onerror=q.onblocked=()=>r()}catch{r()}})}
const db=()=>new Promise((ok,no)=>{const q=indexedDB.open(DB,1);q.onupgradeneeded=()=>q.result.createObjectStore('models',{keyPath:'id'});q.onsuccess=()=>ok(q.result);q.onerror=()=>no(q.error)})
const tx=async(mode,f)=>{const d=await db();return new Promise((ok,no)=>{const t=d.transaction('models',mode),r=f(t.objectStore('models'));t.oncomplete=()=>ok(r?.result);t.onerror=()=>no(t.error)})}
export const models={
  list:async()=>{try{return(await tx('readonly',s=>s.getAll())||[]).map(({id,name,size,added,persona})=>({id,name,size,added,persona}))}catch{return[]}},
  get:async id=>{try{return await tx('readonly',s=>s.get(id))}catch{return null}},
  put:async(name,buf,persona='neutral')=>{const id='user:'+Date.now().toString(36);await tx('readwrite',s=>s.put({id,name,size:buf.byteLength,added:Date.now(),persona,blob:new Blob([buf])}));return id},
  del:async id=>{try{await tx('readwrite',s=>s.delete(id))}catch{}}
}
