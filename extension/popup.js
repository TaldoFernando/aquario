(async()=>{
  const $=id=>document.getElementById(id), native=typeof chrome!=='undefined'&&!!chrome.storage;
  const catalog=await(await fetch('assets/catalog.json')).json();
  const available=catalog.filter(i=>i.sprite), byID=new Map(catalog.map(i=>[i.id,i]));
  let config=native?(await chrome.storage.local.get('config')).config:null;
  config=config||{version:1,ids:[],geo:null,paused:false,clock:null,realScale:false};
  let draft=[...(config.ids||[])],pickId=null;
  const renderer=new AquarioRenderer($('tank'));renderer.paused=!!config.paused;
  const combo=$('combo'),toggleBtn=$('species-toggle'),list=$('species'),preview=$('species-preview');
  function setPick(id){pickId=id;const i=id?byID.get(id):null;$('species-label').textContent=i?i.name:'Escolher…';const thumb=$('species-thumb');thumb.hidden=!i;if(i)thumb.src=i.sprite;}
  function closeList(){list.hidden=true;toggleBtn.setAttribute('aria-expanded','false');preview.hidden=true;}
  toggleBtn.onclick=()=>{if(list.hidden){list.hidden=false;toggleBtn.setAttribute('aria-expanded','true');}else closeList();};
  document.addEventListener('click',e=>{if(!combo.contains(e.target))closeList();});
  function buildSpecies(){
    list.replaceChildren();const opts=available.filter(i=>!draft.includes(i.id));
    for(const i of opts){const b=document.createElement('button');b.type='button';b.className='combo-item';b.setAttribute('role','option');const img=document.createElement('img');img.src=i.sprite;img.alt='';const span=document.createElement('span');span.textContent=i.name;b.append(img,span);b.onmouseenter=()=>{const p=preview.querySelector('img');p.src=i.sprite;preview.hidden=false;b.classList.add('active');};b.onmouseleave=()=>{preview.hidden=true;b.classList.remove('active');};b.onclick=()=>{setPick(i.id);closeList();};list.append(b);}
    if(opts.length&&!opts.some(o=>o.id===pickId))setPick(opts[0].id);else if(!opts.length)setPick(null);
    $('add').disabled=!opts.length;
  }
  async function persist(next){config=next;if(native)await chrome.storage.local.set({config});}
  function currentDate(){const d=new Date();if(config.clock){const[h,m]=config.clock.split(':').map(Number);if(Number.isFinite(h))d.setHours(h,m||0,0,0);}return d;}
  function phase(){const p=AquarioSolar.phase(currentDate(),config.geo);$('phase').textContent=p.label;$('location').textContent=(config.geo?'Posição solar · '+(config.clock?'horário escolhido':'localização do dispositivo'):'Ciclo aproximado · '+(config.clock?'horário escolhido':'horário local'));}
  function render(){
    $('selected').replaceChildren();
    for(const id of draft){const i=byID.get(id);if(!i)continue;const row=document.createElement('div');row.className='animal';const img=document.createElement('img');img.src=i.sprite;img.alt='';const text=document.createElement('div'),name=document.createElement('strong'),sci=document.createElement('small');name.textContent=i.name;sci.textContent=i.scientific_name||i.kind;text.append(name,sci);const remove=document.createElement('button');remove.textContent='×';remove.setAttribute('aria-label','Remover '+i.name);remove.onclick=()=>{draft=draft.filter(x=>x!==id);persist({...config,ids:[...draft]});render();};row.append(img,text,remove);$('selected').append(row);}
    $('count').textContent=draft.length+' espécies';buildSpecies();syncLightControls();
    renderer.clock=config.clock;renderer.realScale=!!config.realScale;$('scale').textContent=config.realScale?'Escala: real':'Escala: fictícia';
    renderer.set(draft.map(id=>byID.get(id)).filter(Boolean),config.geo);phase();
    $('pause').textContent=config.paused?'Retomar':'Pausar';
  }
  $('available').textContent=`${available.length} espécies com sprites · ${catalog.length} fichas no catálogo`;
  $('add').onclick=()=>{const id=pickId;if(id&&!draft.includes(id)&&draft.length<60){draft.push(id);persist({...config,ids:[...draft]});render();}};
  $('geo').onclick=async()=>{
    try{
      if(native && !await chrome.permissions.request({permissions:['geolocation']}))throw new Error('Localização não autorizada; mantendo ciclo por horário local.');
      const pos=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{timeout:12000,maximumAge:3600000,enableHighAccuracy:false}));
      await persist({...config,geo:{latitude:Math.round(pos.coords.latitude*100)/100,longitude:Math.round(pos.coords.longitude*100)/100,updatedAt:new Date().toISOString()}});render();
    }catch(error){$('message').textContent=error.message||'Localização indisponível; mantendo o horário local.';}
  };
  function applyCustomPlace(){const latitude=parseFloat($('lat').value),longitude=parseFloat($('lon').value);if(Number.isFinite(latitude)&&Number.isFinite(longitude)){config.geo={latitude,longitude,updatedAt:new Date().toISOString()};persist({...config});render();}}
  function syncLightControls(){
    $('clock').value=config.clock||'';const p=$('place');
    if(!config.geo)p.value='device';
    else{const hit=[...p.options].find(o=>o.value!=='device'&&o.value!=='custom'&&Math.abs(parseFloat(o.value.split(',')[0])-config.geo.latitude)<.05&&Math.abs(parseFloat(o.value.split(',')[1])-config.geo.longitude)<.05);if(hit)p.value=hit.value;else{p.value='custom';$('lat').value=config.geo.latitude;$('lon').value=config.geo.longitude;}}
    $('custom-place').hidden=p.value!=='custom';
  }
  function formatClock(v){const d=(v||'').replace(/\D/g,'').slice(0,4);if(d.length<=2)return d;if(d.length===3&&+d.slice(0,2)>=24)return d[0]+':'+d.slice(1);return d.slice(0,2)+':'+d.slice(2);}
  function normalizeClock(v){let d=(v||'').replace(/\D/g,'').slice(0,4);if(d.length===2)d+='00';else if(d.length===3)d='0'+d;if(d.length!==4)return null;const h=+d.slice(0,2),m=+d.slice(2);return h<24&&m<60?String(h).padStart(2,'0')+':'+String(m).padStart(2,'0'):null;}
  $('clock').oninput=()=>{const el=$('clock');el.value=formatClock(el.value);};
  $('clock').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();$('clock-apply').click();}};
  $('clock-apply').onclick=()=>{const v=normalizeClock($('clock').value);if(!v){$('message').textContent='Hora inválida. Digite no formato HHMM, ex.: 1530.';return;}$('clock').value=v;config.clock=v;persist({...config});render();};
  $('clock-reset').onclick=()=>{config.clock=null;$('clock').value='';persist({...config});render();};
  $('place').onchange=()=>{const v=$('place').value;$('custom-place').hidden=v!=='custom';if(v==='device')config.geo=null;else if(v==='custom'){config.geo=null;applyCustomPlace();return;}else{const[latitude,longitude]=v.split(',').map(Number);config.geo={latitude,longitude,updatedAt:new Date().toISOString()};}persist({...config});render();};
  $('lat').onchange=applyCustomPlace;$('lon').onchange=applyCustomPlace;
  $('scale').onclick=async()=>{await persist({...config,realScale:!config.realScale});render();};
  $('pause').onclick=async()=>{await persist({...config,paused:!config.paused});renderer.paused=config.paused;render();};
  $('float').onclick=async()=>{
    if(!native){$('message').textContent='Carregue a pasta extension como extensão descompactada no Chrome.';return;}
    try{const [tab]=await chrome.tabs.query({active:true,currentWindow:true});await chrome.scripting.executeScript({target:{tabId:tab.id},files:['solar.js','renderer.js','content.js']});window.close();}catch(error){$('message').textContent='Abra uma página HTTP/HTTPS comum. O Chrome bloqueia injeção em páginas internas e na loja.';}
  };
  if(!native){$('message').textContent='Prévia visual · nenhuma configuração é gravada nesta página.';}
  render();const timer=setInterval(phase,60000);window.addEventListener('pagehide',()=>{clearInterval(timer);renderer.destroy();});
})();
