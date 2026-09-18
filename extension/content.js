(async()=>{
  if(globalThis.__aquarioDispose){globalThis.__aquarioDispose();return;}
  const host=document.createElement('div');host.id='aquario-floating';
  host.style.cssText='position:fixed!important;right:24px!important;bottom:24px!important;z-index:2147483647!important;width:min(400px,95vw)!important;';
  const shadow=host.attachShadow({mode:'closed'});
  const style=document.createElement('style');style.textContent=':host{all:initial}section{border:1px solid #769b8e;border-radius:18px;overflow:hidden;box-shadow:0 12px 45px #0006;background:#152c31;color:#d8e8dc;font:12px system-ui}header{display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:move;touch-action:none}span{flex:1}button{background:transparent;border:0;color:inherit;cursor:pointer;font:inherit;padding:3px}canvas{display:block;width:100%;image-rendering:pixelated}';shadow.append(style);
  const section=document.createElement('section'),header=document.createElement('header'),title=document.createElement('span');title.textContent='AQUÁRIO · seu pequeno intervalo';
  const pause=document.createElement('button');pause.textContent='Pausar';const close=document.createElement('button');close.textContent='×';close.setAttribute('aria-label','Fechar aquário');
  header.append(title,pause,close);const canvas=document.createElement('canvas');canvas.width=480;canvas.height=290;canvas.setAttribute('aria-label','Aquário virtual');section.append(header,canvas);shadow.append(section);document.documentElement.append(host);
  const renderer=new globalThis.AquarioRenderer(canvas,p=>chrome.runtime.getURL(p));
  const catalog=await (await fetch(chrome.runtime.getURL('assets/catalog.json'))).json();
  async function refresh(){const {config={ids:[]}}=await chrome.storage.local.get('config');renderer.set((config.ids||[]).map(id=>catalog.find(i=>i.id===id)).filter(Boolean),config.geo);renderer.paused=!!config.paused;pause.textContent=renderer.paused?'Retomar':'Pausar';}
  const listener=(_,area)=>{if(area==='local')refresh();};chrome.storage.onChanged.addListener(listener);await refresh();
  globalThis.__aquarioDispose=()=>{renderer.destroy();chrome.storage.onChanged.removeListener(listener);host.remove();delete globalThis.__aquarioDispose;};close.onclick=globalThis.__aquarioDispose;
  pause.onclick=async()=>{const {config}=await chrome.storage.local.get('config');await chrome.storage.local.set({config:{...config,paused:!renderer.paused}});};
  let drag=null;header.onpointerdown=e=>{if(e.target.tagName==='BUTTON')return;const r=host.getBoundingClientRect();drag={x:e.clientX-r.left,y:e.clientY-r.top};header.setPointerCapture(e.pointerId);};
  header.onpointermove=e=>{if(!drag)return;host.style.setProperty('right','auto','important');host.style.setProperty('bottom','auto','important');host.style.setProperty('left',Math.max(0,Math.min(innerWidth-host.offsetWidth,e.clientX-drag.x))+'px','important');host.style.setProperty('top',Math.max(0,Math.min(innerHeight-host.offsetHeight,e.clientY-drag.y))+'px','important');};header.onpointerup=()=>drag=null;
})();
