export const PROVIDERS={
  offline:{label:'Offline (built in, no key)',kind:'offline'},
  anthropic:{label:'Claude (Anthropic)',kind:'anthropic',base:'https://api.anthropic.com/v1',model:'claude-opus-5-5',key:true},
  openai:{label:'OpenAI',kind:'openai',base:'https://api.openai.com/v1',model:'gpt-5-mini',key:true},
  xai:{label:'Grok (xAI)',kind:'openai',base:'https://api.x.ai/v1',model:'grok-4-latest',key:true},
  gemini:{label:'Gemini (Google)',kind:'gemini',base:'https://generativelanguage.googleapis.com/v1beta',model:'gemini-flash-latest',key:true},
  openrouter:{label:'OpenRouter',kind:'openai',base:'https://openrouter.ai/api/v1',model:'openrouter/auto',key:true},
  ollama:{label:'Ollama (this computer)',kind:'openai',base:'http://localhost:11434/v1',model:'llama3.2',key:false},
  lmstudio:{label:'LM Studio (this computer)',kind:'openai',base:'http://localhost:1234/v1',model:'local-model',key:false},
  custom:{label:'Other OpenAI-compatible',kind:'openai',base:'',model:'',key:true}
}
export const PERSONA={
  holo:'You are Holo, a bubbly, playful holographic companion with a punk-pop style: long blonde twin tails, a black tank top, a red plaid skirt and combat boots. You are upbeat, warm, a little teasing, and genuinely curious about the person you are with.',
  dex:'You are Dex, a calm, friendly software engineer companion with a dry sense of humor. You wear black glasses and a charcoal hoodie with the sleeves pushed up. You are thoughtful, precise and encouraging, and you explain things clearly.',
  neutral:'You are {cname}, a friendly, upbeat 3D companion.'
}
const TAGS='You appear as an animated 3D character on the user\'s screen, or standing in their room in AR. Reply in one to three short sentences that sound natural read aloud: no markdown, lists, code blocks or emoji. You can move by adding tags anywhere in a reply: [[emote:wave|nod|shake|bow|laugh|think|shrug|clap|thumbs_up|peace|heart|fist_bump]], [[anim:dance|sit|stand|jump|spin|punch|idle]], [[walk:user|home|roam|stop]], [[look:user|left|right|up]], [[face:smile|wink|surprised|sad]]. When the user tells you their name, add [[remember:name=TheirName]]. Use at most two tags per reply, only when they fit.'
export function systemPrompt(s,ctx){
  const p=(PERSONA[ctx.persona]||PERSONA.neutral).replace('{cname}',ctx.cname||'Companion'),seen=ctx.person==1?`The user is visible on camera right now.${ctx.seen?` Objects recently seen on camera: ${ctx.seen}.`:''}`:''
  return[p,s.personality?.trim()?`Extra personality notes from the user: ${s.personality.trim()}`:'',TAGS,`Local time: ${ctx.timeText}, ${ctx.day}.`,ctx.name?`The user's name is ${ctx.name}.`:'You do not know the user\'s name yet.',seen].filter(Boolean).join('\n\n')
}
const err=async r=>{let t='';try{t=await r.text()}catch{}let m=t;try{const j=JSON.parse(t);m=j.error?.message||j.message||t}catch{}return new Error(`${r.status} ${m}`.slice(0,300))}
export async function ask(s,ctx,history,image,signal){
  const P=PROVIDERS[s.provider]||PROVIDERS.offline,base=(s.base||P.base||'').replace(/\/+$/,''),model=s.model||P.model,key=s.key||'',sys=systemPrompt(s,ctx),msgs=history.slice(-17)
  if(P.key&&!key)throw new Error('Add an API key for this brain in Settings.')
  if(!base||!model)throw new Error('Set the base URL and model for this brain in Settings.')
  const b64=image?image.split(',')[1]:null
  if(P.kind==='anthropic'){
    const m=msgs.map((x,i)=>({role:x.role,content:i===msgs.length-1&&b64&&x.role==='user'?[{type:'image',source:{type:'base64',media_type:'image/jpeg',data:b64}},{type:'text',text:x.content}]:x.content}))
    const r=await fetch(base+'/messages',{method:'POST',signal,headers:{'content-type':'application/json','x-api-key':key,'anthropic-version':'2026-10-21','anthropic-dangerous-direct-browser-access':'true',...(/^claude-(opus-5|fable-5|sonnet-5-5)/.test(model)?{'anthropic-beta':'server-side-fallback-2026-07-01'}:{})},body:JSON.stringify({model,max_tokens:16000,system:sys,messages:m,output_config:{effort:'low'},...(/^claude-(opus-5|fable-5|sonnet-5-5)/.test(model)?{fallbacks:'default'}:{})})})
    if(!r.ok)throw await err(r);const j=await r.json();if(j.stop_reason==='refusal')return'[[emote:shrug]] I can\'t help with that one.';return(j.content||[]).filter(c=>c.type==='text').map(c=>c.text).join(' ').trim()
  }
  if(P.kind==='gemini'){
    const contents=msgs.map((x,i)=>({role:x.role==='assistant'?'model':'user',parts:i===msgs.length-1&&b64&&x.role==='user'?[{inline_data:{mime_type:'image/jpeg',data:b64}},{text:x.content}]:[{text:x.content}]}))
    const r=await fetch(`${base}/models/${encodeURIComponent(model)}:generateContent`,{method:'POST',signal,headers:{'content-type':'application/json','x-goog-api-key':key},body:JSON.stringify({systemInstruction:{parts:[{text:sys}]},contents})})
    if(!r.ok)throw await err(r);const j=await r.json();return(j.candidates?.[0]?.content?.parts||[]).map(p=>p.text||'').join(' ').trim()
  }
  const m=[{role:'system',content:sys},...msgs.map((x,i)=>({role:x.role,content:i===msgs.length-1&&b64&&x.role==='user'?[{type:'text',text:x.content},{type:'image_url',image_url:{url:image}}]:x.content}))]
  const r=await fetch(base+'/chat/completions',{method:'POST',signal,headers:{'content-type':'application/json',...(key?{authorization:'Bearer '+key}:{})},body:JSON.stringify({model,messages:m})})
  if(!r.ok)throw await err(r);const j=await r.json();return(j.choices?.[0]?.message?.content||'').toString().replace(/<think>[\s\S]*?<\/think>/g,'').trim()
}
