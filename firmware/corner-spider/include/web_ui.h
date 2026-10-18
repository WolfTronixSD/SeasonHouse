#pragma once
#include <pgmspace.h>

// The control page, served straight from the ESP32 so it works with no internet.
static const char INDEX_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SeasonHouse Prop</title>
<style>
:root{--bg:#0b0710;--panel:#1a1022;--line:#3a2547;--txt:#eadff2;--dim:#9c88aa;--acc:#ff6a00;--red:#e0182d;--grn:#5fd16b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.4 system-ui,sans-serif}
header{padding:18px 16px 8px;text-align:center}
h1{margin:0;font-size:28px;letter-spacing:1px;color:var(--acc);text-shadow:0 0 12px #ff6a0080}
#st{color:var(--dim);font-size:14px;margin-top:4px}
main{max-width:720px;margin:auto;padding:8px 16px 40px}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;margin:12px 0}
h2{margin:0 0 10px;font-size:15px;text-transform:uppercase;letter-spacing:2px;color:var(--dim)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
button{font:inherit;color:var(--txt);background:#2a1836;border:1px solid var(--line);border-radius:10px;padding:14px 10px;cursor:pointer}
button:active{transform:scale(.97)}
button.show small{display:block;font-weight:400;color:var(--dim);font-size:12px}
button.show{background:linear-gradient(160deg,#3b1450,#22102c);font-weight:600}
button.show.on{outline:2px solid var(--acc);box-shadow:0 0 18px #ff6a0090}
#stop{width:100%;background:var(--red);border:0;font-size:20px;font-weight:800;padding:16px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0}
.row label{min-width:90px;color:var(--dim)}
input[type=range]{flex:1}input[type=text],input[type=number],select{font:inherit;background:#120a18;color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:8px;min-width:0;flex:1}
.tog{padding:10px 14px}.tog.on{background:var(--grn);color:#062;border-color:var(--grn);font-weight:700}
.pill{display:inline-block;padding:2px 8px;border-radius:99px;background:#2a1836;margin:2px;font-size:13px}
.ok{color:var(--grn)}.bad{color:var(--red)}
#bar{height:10px;background:#120a18;border-radius:99px;overflow:hidden;border:1px solid var(--line)}
#bar i{display:block;height:100%;width:0;background:var(--acc);transition:width .3s}
</style></head><body>
<header><h1 id="ttl">SEASONHOUSE</h1><div id="st">connecting...</div></header>
<main>
<section><button id="stop" onclick="api('stop')">STOP</button></section>

<section><h2>Season</h2><div class="row"><select id="season" onchange="season(this.value)"></select></div></section>

<section><h2>Shows</h2><div class="grid" id="shows"></div></section>

<section><h2>Triggers</h2>
 <div class="row"><button class="tog" id="arm" onclick="api('arm?on='+(S.armed?0:1))">Motion sensor</button>
 <button class="tog" id="party" onclick="api('party?on='+(S.party?0:1))">Party mode (random scares)</button></div>
 <div id="sensors"></div>
</section>

<section><h2>Eyes, sound, lights</h2>
 <div class="row"><label>Eyes</label><select id="eyes" onchange="api('eyes?mode='+this.value)">
  <option>off</option><option>glow</option><option>full</option><option>pulse</option><option>flicker</option><option>blink</option><option>disco</option></select></div>
 <div class="row"><label>Volume</label><input type="range" id="vol" min="0" max="30" onchange="api('vol?v='+this.value)"></div>
 <div class="grid" id="sounds"></div>
 <h2 style="margin-top:14px">WLED</h2><div class="grid" id="wledb"></div>
 <div class="row"><label>WLED IP</label><input type="text" id="wh"><button onclick="api('wled?host='+encodeURIComponent(wh.value))">Save</button></div>
</section>

<section><h2>Setup: drop length</h2>
 <div id="bar"><i></i></div>
 <div class="row" style="margin-top:8px"><span id="pos"></span></div>
 <div class="row">
  <button onclick="api('jog?steps=-500')">Up 500</button><button onclick="api('jog?steps=-100')">Up 100</button>
  <button onclick="api('jog?steps=100')">Down 100</button><button onclick="api('jog?steps=500')">Down 500</button></div>
 <div class="row"><button onclick="api('setdrop')">Save current spot as full drop</button><button onclick="api('home')">Re-home (wind up)</button></div>
</section>
</main>
<script>
let S={};const $=id=>document.getElementById(id);
async function api(p){try{const r=await fetch('/api/'+p);S=await r.json();draw()}catch(e){$('st').textContent='spider offline?'}}
function draw(){
 $('st').innerHTML=(S.show?'<b style="color:var(--acc)">PLAYING: '+S.show+'</b>':(S.homing?'homing...':(S.homed?'lurking in the corner':'<span class=bad>not homed</span>')))+' &middot; '+S.ip;
 document.querySelectorAll('.show').forEach(b=>b.classList.toggle('on',b.dataset.id==S.show));
 $('arm').classList.toggle('on',S.armed);$('party').classList.toggle('on',S.party);
 if(document.activeElement!==$('vol'))$('vol').value=S.vol;
 if(document.activeElement!==$('eyes'))$('eyes').value=S.eyes;
 if(document.activeElement!==$('wh'))$('wh').value=S.wled;
 $('sensors').innerHTML='<span class=pill>PIR: '+(S.pir?'<b class=ok>motion</b>':'quiet')+'</span><span class=pill>Top switch: '+(S.top?'pressed':'open')+'</span><span class=pill>MP3: '+(S.mp3?'<span class=ok>ok</span>':'<span class=bad>missing</span>')+'</span>';
 $('pos').textContent='Position '+S.pos+' / '+S.drop+' steps';
 $('bar').firstChild.style.width=Math.min(100,100*S.pos/S.drop)+'%';
}
function btn(parent,html,cls,fn){const b=document.createElement('button');b.innerHTML=html;if(cls)b.className=cls;b.onclick=fn;$(parent).appendChild(b);return b}
async function season(id){
 const r=await fetch('/api/season'+(id?'?s='+id:''));const d=await r.json();
 $('ttl').textContent=d.character.toUpperCase();
 $('season').innerHTML=d.seasons.map(x=>'<option value="'+x.id+'"'+(x.id==d.season?' selected':'')+'>'+x.label+'</option>').join('');
 $('shows').innerHTML='';d.shows.forEach(s=>{btn('shows',s.label+'<small>'+s.hint+'</small>','show',()=>api('run?show='+s.id)).dataset.id=s.id});
 $('sounds').innerHTML='';d.sounds.forEach((n,i)=>{if(i!=6)btn('sounds',n,'',()=>api('sound?t='+(i+1)))});btn('sounds','Chitter','',()=>api('chitter'));
 $('wledb').innerHTML='';d.wled.forEach((n,i)=>btn('wledb',n,'',()=>api('wled?slot='+(i+1))));
}
season();
api('status');setInterval(()=>api('status'),1000);
</script></body></html>)HTML";
