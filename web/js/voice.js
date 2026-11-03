const SR=globalThis.SpeechRecognition||globalThis.webkitSpeechRecognition,syn=globalThis.speechSynthesis
const FEMALE=/female|samantha|zira|aria|jenny|ava|allison|karen|moira|tessa|serena|victoria|susan|google us english|natural.*(emma|michelle)/i,MALE=/\bmale\b|daniel|alex|guy|david|mark|fred|tom|aaron|rishi|google uk english male|natural.*(brian|christopher)/i
export const canListen=!!SR,canSpeak=!!syn
export function voices(){return syn?syn.getVoices().filter(v=>/^en/i.test(v.lang)).concat(syn.getVoices().filter(v=>!/^en/i.test(v.lang))):[]}
export function pickVoice(uri,persona){const all=voices();return all.find(v=>v.voiceURI===uri)||(persona==='dex'?all.find(v=>MALE.test(v.name)):persona==='holo'?all.find(v=>FEMALE.test(v.name)):null)||all.find(v=>v.default)||all[0]||null}
export function speak(text,o={}){return new Promise(res=>{if(!syn||!text){res();return}syn.cancel();const u=new SpeechSynthesisUtterance(text.slice(0,700)),v=pickVoice(o.voice,o.persona);v&&(u.voice=v,u.lang=v.lang);u.rate=o.rate||1;u.pitch=o.pitch??(o.persona==='holo'?1.15:o.persona==='dex'?.95:1);u.onstart=()=>o.onstart?.();u.onend=u.onerror=()=>{o.onend?.();res()};syn.speak(u)})}
export function hush(){syn?.cancel()}
export class Listener{
  constructor(onText,onState){this.onText=onText;this.onState=onState;this.on=false;this.paused=false;this.local=false}
  async start(continuous,lang){if(!SR)throw new Error('This browser has no speech recognition. Try Chrome, Edge or Safari, or type instead.');this.stop();this.continuous=continuous;this.lang=lang||navigator.language||'en-US';try{this.local=!!(SR.available&&await SR.available({langs:[this.lang],processLocally:true})==='available')}catch{this.local=false}this.on=true;this.run()}
  run(){if(!this.on||this.paused)return;const r=new SR();this.r=r;r.lang=this.lang;r.interimResults=false;r.continuous=!!this.continuous;r.maxAlternatives=1;try{this.local&&(r.processLocally=true)}catch{}r.onresult=e=>{const t=Array.from(e.results).slice(e.resultIndex).filter(x=>x.isFinal).map(x=>x[0].transcript).join(' ').trim();t&&this.onText(t)};r.onerror=e=>{(e.error==='not-allowed'||e.error==='service-not-allowed')&&(this.on=false,this.onState?.('denied'))};r.onend=()=>{this.r=null;this.on&&this.continuous&&!this.paused?setTimeout(()=>this.run(),250):(this.on=this.on&&this.continuous,this.onState?.(this.on?'on':'off'))};try{r.start();this.onState?.('listening')}catch{this.onState?.('off')}}
  pause(p){this.paused=p;p?this.r?.abort():this.run()}
  stop(){this.on=false;this.r?.abort();this.r=null;this.onState?.('off')}
}
