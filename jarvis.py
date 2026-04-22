#!/usr/bin/env python3
"""J.A.R.V.I.S. - Just A Rather Very Intelligent System"""

import os, sys, time, math, random, struct, threading, subprocess, webbrowser, json, asyncio, tempfile

try:
    import numpy as _np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import anthropic
    import pyaudio
    import pygame
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    import speech_recognition as sr
    import psutil
    import pyautogui
    import pygetwindow as gw
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
except ImportError as e:
    print(f"Missing dependency: {e}"); print("Run: python setup_jarvis.py"); sys.exit(1)

import urllib.parse

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "jarvis_config.json")
SOUNDS_DIR  = os.path.join(BASE_DIR, "sounds")
TTS_VOICE   = "en-GB-RyanNeural"   # British male — closest to JARVIS

def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key: return key
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f: return json.load(f).get("api_key", "")
    return ""

def save_api_key(key):
    with open(CONFIG_PATH, "w") as f: json.dump({"api_key": key}, f)

API_KEY = load_api_key()

# ─── Spotify ──────────────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID",     "3772f28ca5c541e0a970a60274c84a68")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "d91e6f1761f940bb84ac6ce628bdd127")

def make_spotify():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET: return None
    try:
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    except Exception as e:
        print(f"Spotify init error: {e}"); return None

sp = make_spotify()

def find_song():
    if not os.path.exists(SOUNDS_DIR): return None
    for ext in (".mp3", ".webm", ".ogg", ".wav"):
        for f in os.listdir(SOUNDS_DIR):
            if f.endswith(ext): return os.path.join(SOUNDS_DIR, f)
    return None

SONG_PATH = find_song() or r"C:\Users\filip\Desktop\claudecode\sounds\iron_man.mp3"
if not os.path.exists(SONG_PATH): SONG_PATH = None

# ─── Mind Map HTML Template ───────────────────────────────────────────────────
MINDMAP_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>__TITLE__ — Mind Map</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#04080f; font-family:'Consolas','Share Tech Mono',monospace; overflow:hidden; width:100vw; height:100vh; color:#e8f4f8; }
  #header { position:fixed; top:0; left:0; right:0; height:32px; background:rgba(0,0,0,0.88); border-bottom:1px solid rgba(0,255,200,0.18); display:flex; align-items:center; justify-content:center; z-index:100; }
  #header span { font-size:11px; letter-spacing:3px; color:rgba(0,255,200,0.7); text-transform:uppercase; }
  .scanline { position:fixed; top:32px; left:0; right:0; bottom:0; background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,200,0.010) 2px,rgba(0,255,200,0.010) 4px); pointer-events:none; z-index:50; }
  #canvas-wrap { position:fixed; top:32px; left:0; right:0; bottom:0; cursor:grab; }
  #canvas-wrap.dragging { cursor:grabbing; }
  svg#map { width:100%; height:100%; display:block; }
  .edge { fill:none; stroke-width:1.2; opacity:0.25; transition:opacity 0.2s,stroke-width 0.2s; }
  .edge.bright { opacity:0.9; stroke-width:2; }
  .edge.dim    { opacity:0.04; }
  .node-group  { cursor:pointer; }
  .node-circle { transition:filter 0.2s; }
  .node-group:hover .node-circle { filter:drop-shadow(0 0 14px currentColor) drop-shadow(0 0 4px currentColor); }
  .node-group.highlighted .node-circle { filter:drop-shadow(0 0 18px currentColor); }
  .node-group.dim { opacity:0.12; }
  .node-label { pointer-events:none; font-weight:700; letter-spacing:0.5px; }
  #tooltip { position:fixed; z-index:200; display:none; background:rgba(4,8,15,0.97); border:1px solid rgba(0,255,200,0.3); border-radius:8px; padding:14px 16px; max-width:320px; box-shadow:0 0 28px rgba(0,255,200,0.13),inset 0 0 28px rgba(0,255,200,0.03); pointer-events:none; backdrop-filter:blur(8px); }
  #tt-title { font-size:14px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:7px; }
  #tt-body  { font-size:12px; color:rgba(232,244,248,0.78); line-height:1.55; }
  #legend { position:fixed; top:46px; left:14px; z-index:100; background:rgba(4,8,15,0.65); border:1px solid rgba(0,255,200,0.14); border-radius:6px; padding:10px 12px; backdrop-filter:blur(4px); }
  #legend .leg-title { font-size:9px; color:rgba(0,255,200,0.5); letter-spacing:2px; margin-bottom:8px; }
  .leg-item { display:flex; align-items:center; gap:7px; font-size:10px; color:rgba(232,244,248,0.6); margin:3px 0; }
  .leg-dot  { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
  #controls { position:fixed; bottom:18px; right:18px; z-index:100; display:flex; flex-direction:column; gap:6px; }
  .ctrl-btn { width:36px; height:36px; border-radius:6px; background:rgba(0,255,200,0.07); border:1px solid rgba(0,255,200,0.28); color:#00ffc8; font-size:17px; cursor:pointer; display:flex; align-items:center; justify-content:center; font-family:'Consolas',monospace; transition:all 0.2s; }
  .ctrl-btn:hover { background:rgba(0,255,200,0.16); box-shadow:0 0 12px rgba(0,255,200,0.32); }
  #hint { position:fixed; bottom:18px; left:50%; transform:translateX(-50%); font-size:9px; color:rgba(0,255,200,0.3); letter-spacing:3px; text-transform:uppercase; z-index:100; pointer-events:none; }
  .ring { fill:none; stroke:#00ffc8; }
  .ring1 { animation:pulse1 3s ease-in-out infinite; }
  .ring2 { animation:pulse2 3s ease-in-out infinite; animation-delay:1.5s; }
  @keyframes pulse1 { 0%,100%{r:58;opacity:.16;} 50%{r:66;opacity:.30;} }
  @keyframes pulse2 { 0%,100%{r:78;opacity:.07;} 50%{r:86;opacity:.14;} }
</style>
</head>
<body>
<div id="header"><span>// __TITLE__ &nbsp;&middot;&nbsp; JARVIS KNOWLEDGE ATLAS</span></div>
<div class="scanline"></div>
<div id="legend"><div class="leg-title">// CATEGORIES</div><div id="legend-items"></div></div>
<div id="canvas-wrap"><svg id="map" xmlns="http://www.w3.org/2000/svg"></svg></div>
<div id="controls">
  <button class="ctrl-btn" id="zoomIn">+</button>
  <button class="ctrl-btn" id="zoomOut">&minus;</button>
  <button class="ctrl-btn" id="resetBtn" title="Reset">&#x2316;</button>
</div>
<div id="hint">DRAG TO PAN &middot; SCROLL TO ZOOM &middot; HOVER FOR INFO</div>
<div id="tooltip"><div id="tt-title"></div><div id="tt-body"></div></div>
<script>
const RAW_NODES = __NODES_JSON__;
const RAW_EDGES = __EDGES_JSON__;
const RAW_CATS  = __CATEGORIES_JSON__;

const CAT = {};
RAW_CATS.forEach(function(c){ CAT[c.name] = c.color; });

const nodeById = {};
RAW_NODES.forEach(function(n){ nodeById[n.id] = n; });
const children = {};
RAW_NODES.forEach(function(n){
  const pid = n.parent_id;
  if(pid){ if(!children[pid]) children[pid]=[]; children[pid].push(n.id); }
});

const RADII = [0, 220, 430, 620, 800];
const POSITIONS = {};

function getDepth(id, visited){
  visited = visited || new Set();
  if(visited.has(id)) return 0;
  visited.add(id);
  const n = nodeById[id];
  if(!n || !n.parent_id) return 0;
  return 1 + getDepth(n.parent_id, visited);
}

function layoutSubtree(id, startAngle, endAngle, depth){
  const angle = (startAngle + endAngle) / 2;
  const r = RADII[depth] !== undefined ? RADII[depth] : depth * 210;
  POSITIONS[id] = { x: Math.cos(angle)*r, y: Math.sin(angle)*r };
  const kids = children[id] || [];
  if(kids.length === 0) return;
  const span = endAngle - startAngle;
  const step = span / kids.length;
  kids.forEach(function(kid, i){
    layoutSubtree(kid, startAngle + i*step, startAngle + (i+1)*step, depth+1);
  });
}

let rootId = null;
RAW_NODES.forEach(function(n){ if(!n.parent_id) rootId = n.id; });
if(rootId){
  POSITIONS[rootId] = {x:0, y:0};
  const rootKids = children[rootId] || [];
  const step = (2 * Math.PI) / Math.max(rootKids.length, 1);
  rootKids.forEach(function(kid, i){
    layoutSubtree(kid, i*step - Math.PI/2, (i+1)*step - Math.PI/2, 1);
  });
}

const EDGES = [];
RAW_NODES.forEach(function(n){
  if(n.parent_id && nodeById[n.parent_id]) EDGES.push([n.parent_id, n.id]);
});
RAW_EDGES.forEach(function(e){ EDGES.push(e); });

const SVG_NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('map');
let vbW=2400, vbH=1800, vbX=-1200, vbY=-900;
function setVB(){ svg.setAttribute('viewBox', vbX+' '+vbY+' '+vbW+' '+vbH); }
setVB();

const gridG = document.createElementNS(SVG_NS,'g');
for(let x=-1400;x<=1400;x+=90){
  const l=document.createElementNS(SVG_NS,'line');
  l.setAttribute('x1',x);l.setAttribute('y1',-1100);l.setAttribute('x2',x);l.setAttribute('y2',1100);
  l.setAttribute('stroke','rgba(0,255,200,0.025)');l.setAttribute('stroke-width','1');
  gridG.appendChild(l);
}
for(let y=-1100;y<=1100;y+=90){
  const l=document.createElementNS(SVG_NS,'line');
  l.setAttribute('x1',-1400);l.setAttribute('y1',y);l.setAttribute('x2',1400);l.setAttribute('y2',y);
  l.setAttribute('stroke','rgba(0,255,200,0.025)');l.setAttribute('stroke-width','1');
  gridG.appendChild(l);
}
svg.appendChild(gridG);

['ring ring1','ring ring2'].forEach(function(cls){
  const c=document.createElementNS(SVG_NS,'circle');
  c.setAttribute('cx',0);c.setAttribute('cy',0);c.setAttribute('class',cls);
  svg.appendChild(c);
});

const edgesG = document.createElementNS(SVG_NS,'g');
svg.appendChild(edgesG);
EDGES.forEach(function(pair){
  const a=pair[0],b=pair[1];
  const A=nodeById[a],B=nodeById[b];
  if(!A||!B) return;
  const px=POSITIONS[a],py=POSITIONS[b];
  if(!px||!py) return;
  const mx=(px.x+py.x)/2, my=(px.y+py.y)/2;
  const dx=py.x-px.x, dy=py.y-px.y;
  const len=Math.sqrt(dx*dx+dy*dy)||1;
  const off=Math.min(70, len*0.14);
  const ox=-dy/len*off, oy=dx/len*off;
  const path=document.createElementNS(SVG_NS,'path');
  path.setAttribute('d','M '+px.x+' '+px.y+' Q '+(mx+ox)+' '+(my+oy)+' '+py.x+' '+py.y);
  path.setAttribute('class','edge');
  const col = CAT[A.category] || '#00ffc8';
  path.setAttribute('stroke', col);
  path.dataset.a=a; path.dataset.b=b;
  edgesG.appendChild(path);
});

const nodesG = document.createElementNS(SVG_NS,'g');
svg.appendChild(nodesG);
RAW_NODES.forEach(function(n){
  const pos = POSITIONS[n.id];
  if(!pos) return;
  const color = CAT[n.category] || '#00ffc8';
  const isRoot = !n.parent_id;
  const depth = getDepth(n.id);
  const r = isRoot ? 52 : (depth===1 ? 34 : (depth===2 ? 24 : 18));

  const g=document.createElementNS(SVG_NS,'g');
  g.setAttribute('class','node-group');
  g.setAttribute('transform','translate('+pos.x+','+pos.y+')');
  g.dataset.id=n.id;

  const halo=document.createElementNS(SVG_NS,'circle');
  halo.setAttribute('r',r+5);halo.setAttribute('fill',color);halo.setAttribute('opacity','0.055');
  g.appendChild(halo);

  const c=document.createElementNS(SVG_NS,'circle');
  c.setAttribute('r',r);c.setAttribute('fill','#04080f');
  c.setAttribute('stroke',color);c.setAttribute('stroke-width',isRoot?2.5:1.8);
  c.setAttribute('class','node-circle');c.style.color=color;
  g.appendChild(c);

  const dot=document.createElementNS(SVG_NS,'circle');
  dot.setAttribute('r',2.5);dot.setAttribute('cx',0);dot.setAttribute('cy',r-9);
  dot.setAttribute('fill',color);dot.setAttribute('opacity','0.65');
  g.appendChild(dot);

  const lines=(n.label||'').split('\n');
  const fs = isRoot?15:(depth===1?12:(depth===2?10:9));
  const lh=fs+2;
  const startY=-(lines.length*lh)/2+fs-2;
  lines.forEach(function(line,i){
    const t=document.createElementNS(SVG_NS,'text');
    t.setAttribute('x',0);t.setAttribute('y',startY+i*lh);
    t.setAttribute('text-anchor','middle');t.setAttribute('class','node-label');
    t.setAttribute('fill',color);t.setAttribute('font-size',fs);
    t.setAttribute('font-family',"'Consolas','Share Tech Mono',monospace");
    t.textContent=line; g.appendChild(t);
  });

  nodesG.appendChild(g);
  g.addEventListener('mouseenter',function(e){ showTT(n,color,e); hlConn(n.id,true); });
  g.addEventListener('mousemove',moveTT);
  g.addEventListener('mouseleave',function(){ hideTT(); hlConn(n.id,false); });
});

const tooltip=document.getElementById('tooltip');
const ttTitle=document.getElementById('tt-title');
const ttBody=document.getElementById('tt-body');
function showTT(n,color,e){
  ttTitle.textContent=(n.label||'').replace(/\n/g,' ');
  ttTitle.style.color=color;
  ttBody.textContent=n.info||'';
  tooltip.style.borderColor=color+'88';
  tooltip.style.boxShadow='0 0 28px '+color+'20,inset 0 0 28px '+color+'09';
  tooltip.style.display='block';
  moveTT(e);
}
function moveTT(e){
  const pad=16,tw=tooltip.offsetWidth,th=tooltip.offsetHeight;
  let x=e.clientX+pad,y=e.clientY+pad;
  if(x+tw>window.innerWidth-10) x=e.clientX-tw-pad;
  if(y+th>window.innerHeight-10) y=e.clientY-th-pad;
  tooltip.style.left=x+'px'; tooltip.style.top=y+'px';
}
function hideTT(){ tooltip.style.display='none'; }

function hlConn(id,on){
  const conn=new Set([id]);
  EDGES.forEach(function(p){ if(p[0]===id)conn.add(p[1]); if(p[1]===id)conn.add(p[0]); });
  document.querySelectorAll('.node-group').forEach(function(g){
    if(!on){g.classList.remove('dim','highlighted');return;}
    if(conn.has(g.dataset.id)) g.classList.add('highlighted'); else g.classList.add('dim');
  });
  document.querySelectorAll('.edge').forEach(function(edge){
    if(!on){edge.classList.remove('bright','dim');return;}
    if(edge.dataset.a===id||edge.dataset.b===id) edge.classList.add('bright'); else edge.classList.add('dim');
  });
}

const wrap=document.getElementById('canvas-wrap');
let isDown=false,sx=0,sy=0,svbX=0,svbY=0;
wrap.addEventListener('mousedown',function(e){
  if(e.target.closest('.node-group'))return;
  isDown=true;wrap.classList.add('dragging');
  sx=e.clientX;sy=e.clientY;svbX=vbX;svbY=vbY;
});
window.addEventListener('mousemove',function(e){
  if(!isDown)return;
  const sc=vbW/wrap.clientWidth;
  vbX=svbX-(e.clientX-sx)*sc; vbY=svbY-(e.clientY-sy)*sc; setVB();
});
window.addEventListener('mouseup',function(){isDown=false;wrap.classList.remove('dragging');});

wrap.addEventListener('wheel',function(e){
  e.preventDefault();
  const f=e.deltaY>0?1.12:0.89;
  const nW=vbW*f,nH=vbH*f;
  if(nW<400||nW>5200)return;
  const rect=wrap.getBoundingClientRect();
  vbX+=(vbW-nW)*((e.clientX-rect.left)/rect.width);
  vbY+=(vbH-nH)*((e.clientY-rect.top)/rect.height);
  vbW=nW;vbH=nH;setVB();
},{passive:false});

function zoomBy(f){
  const nW=vbW*f,nH=vbH*f;
  if(nW<400||nW>5200)return;
  vbX+=(vbW-nW)/2;vbY+=(vbH-nH)/2;vbW=nW;vbH=nH;setVB();
}
document.getElementById('zoomIn').addEventListener('click',function(){zoomBy(0.85);});
document.getElementById('zoomOut').addEventListener('click',function(){zoomBy(1.18);});
document.getElementById('resetBtn').addEventListener('click',function(){
  vbW=2400;vbH=1800;vbX=-1200;vbY=-900;setVB();
});

const legEl=document.getElementById('legend-items');
RAW_CATS.forEach(function(c){
  const d=document.createElement('div');
  d.className='leg-item';
  d.innerHTML='<span class="leg-dot" style="background:'+c.color+';box-shadow:0 0 5px '+c.color+';"></span><span>'+c.name+'</span>';
  legEl.appendChild(d);
});
</script>
</body>
</html>"""

# ─── Chart HTML Template ──────────────────────────────────────────────────────
CHART_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><title>__TITLE__</title>
<style>
* {margin:0;padding:0;box-sizing:border-box}
body {background:#04080f;font-family:'Consolas',monospace;color:#e8f4f8;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#hdr {height:36px;background:rgba(0,0,0,.9);border-bottom:1px solid rgba(0,255,200,.2);display:flex;align-items:center;justify-content:center;letter-spacing:3px;font-size:11px;color:rgba(0,255,200,.7);text-transform:uppercase;flex-shrink:0}
.scanline {position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,200,.007) 2px,rgba(0,255,200,.007) 4px);pointer-events:none;z-index:5}
#wrap {flex:1;display:flex;align-items:center;justify-content:center;padding:28px 36px 20px}
</style>
</head>
<body>
<div id="hdr">// __TITLE__</div>
<div class="scanline"></div>
<div id="wrap"></div>
<script>
const TYPE='__CHART_TYPE__',LABELS=__LABELS_JSON__,VALUES=__VALUES_JSON__,COLORS=__COLORS_JSON__,X_LABEL='__X_LABEL__',Y_LABEL='__Y_LABEL__';
const NS='http://www.w3.org/2000/svg';
function el(tag,a,txt){const e=document.createElementNS(NS,tag);Object.entries(a||{}).forEach(([k,v])=>e.setAttribute(k,v));if(txt!==undefined)e.textContent=txt;return e}
const wrap=document.getElementById('wrap');
const W=Math.min(wrap.clientWidth||900,1100),H=Math.min(wrap.clientHeight||560,640);

function addGlow(svg){const d=el('defs');const f=el('filter',{id:'glow'});const b=el('feGaussianBlur',{stdDeviation:'5',result:'b'});const m=el('feMerge');m.appendChild(el('feMergeNode',{in:'b'}));m.appendChild(el('feMergeNode',{in:'SourceGraphic'}));f.appendChild(b);f.appendChild(m);d.appendChild(f);svg.insertBefore(d,svg.firstChild);}

if(TYPE==='pie'||TYPE==='donut'){
  const svg=el('svg',{width:W,height:H});
  addGlow(svg);
  const cx=W/2,cy=H/2+10,R=Math.min(W*.38,H*.42),inner=TYPE==='donut'?R*.5:0;
  const total=VALUES.reduce((a,b)=>a+b,0);
  let ang=-Math.PI/2;
  VALUES.forEach((v,i)=>{
    const a=2*Math.PI*(v/total),col=COLORS[i%COLORS.length];
    const x1=cx+R*Math.cos(ang),y1=cy+R*Math.sin(ang),x2=cx+R*Math.cos(ang+a),y2=cy+R*Math.sin(ang+a);
    const lf=a>Math.PI?1:0;
    let d;
    if(inner>0){const ix1=cx+inner*Math.cos(ang),iy1=cy+inner*Math.sin(ang),ix2=cx+inner*Math.cos(ang+a),iy2=cy+inner*Math.sin(ang+a);d=`M${ix1},${iy1} L${x1},${y1} A${R},${R},0,${lf},1,${x2},${y2} L${ix2},${iy2} A${inner},${inner},0,${lf},0,${ix1},${iy1} Z`;}
    else{d=`M${cx},${cy} L${x1},${y1} A${R},${R},0,${lf},1,${x2},${y2} Z`;}
    const p=el('path',{d,fill:col,opacity:'.82',stroke:'#04080f','stroke-width':'2'});
    p.addEventListener('mouseenter',function(){this.setAttribute('opacity','1');this.setAttribute('filter','url(#glow)');});
    p.addEventListener('mouseleave',function(){this.setAttribute('opacity','.82');this.removeAttribute('filter');});
    svg.appendChild(p);
    const mid=ang+a/2,lr=R*1.22,lx=cx+lr*Math.cos(mid),ly=cy+lr*Math.sin(mid);
    svg.appendChild(el('text',{x:lx,y:ly,'text-anchor':lx<cx?'end':'start','dominant-baseline':'middle',fill:'rgba(232,244,248,.82)','font-size':'12','font-family':"'Consolas',monospace"},`${LABELS[i]}  ${Math.round(v/total*100)}%`));
    ang+=a;
  });
  wrap.appendChild(svg);
} else {
  const PAD={t:45,r:35,b:75,l:75},svg=el('svg',{width:W,height:H});
  addGlow(svg);
  const CW=W-PAD.l-PAD.r,CH=H-PAD.t-PAD.b;
  const maxV=Math.max(...VALUES),minV=Math.min(0,...VALUES),range=maxV-minV||1;
  for(let i=0;i<=5;i++){
    const y=PAD.t+CH*(1-i/5),val=minV+(maxV-minV)*(i/5);
    svg.appendChild(el('line',{x1:PAD.l,y1:y,x2:PAD.l+CW,y2:y,stroke:i===0?'rgba(0,255,200,.3)':'rgba(0,255,200,.07)','stroke-width':'1'}));
    svg.appendChild(el('text',{x:PAD.l-8,y:y,'text-anchor':'end','dominant-baseline':'middle',fill:'rgba(0,255,200,.55)','font-size':'11','font-family':"'Consolas',monospace"},val%1===0?val.toFixed(0):val.toFixed(1)));
  }
  svg.appendChild(el('line',{x1:PAD.l,y1:PAD.t,x2:PAD.l,y2:PAD.t+CH,stroke:'rgba(0,255,200,.3)','stroke-width':'1'}));
  if(Y_LABEL)svg.appendChild(el('text',{transform:`rotate(-90)`,x:-(PAD.t+CH/2),y:16,'text-anchor':'middle',fill:'rgba(0,255,200,.4)','font-size':'11','font-family':"'Consolas',monospace"},Y_LABEL));
  if(TYPE==='bar'){
    const gap=CW/LABELS.length,bw=gap*.62;
    LABELS.forEach((lbl,i)=>{
      const x=PAD.l+i*gap+gap/2,bh=Math.max(2,CH*((VALUES[i]-minV)/range)),by=PAD.t+CH-bh,col=COLORS[i%COLORS.length];
      const r=el('rect',{x:x-bw/2,y:by,width:bw,height:bh,fill:col,opacity:'.78',rx:'3'});
      r.addEventListener('mouseenter',function(){this.setAttribute('opacity','1');this.setAttribute('filter','url(#glow)');});
      r.addEventListener('mouseleave',function(){this.setAttribute('opacity','.78');this.removeAttribute('filter');});
      svg.appendChild(r);
      svg.appendChild(el('text',{x,y:by-7,'text-anchor':'middle',fill:'#e8f4f8','font-size':'11','font-family':"'Consolas',monospace"},VALUES[i]));
      const xl=el('text',{x,y:PAD.t+CH+18,'text-anchor':'middle',fill:'rgba(232,244,248,.6)','font-size':'11','font-family':"'Consolas',monospace"},lbl.length>12?lbl.slice(0,12)+'…':lbl);
      svg.appendChild(xl);
    });
  } else {
    const n=LABELS.length,pts=LABELS.map((_,i)=>[PAD.l+i*(CW/Math.max(n-1,1)),PAD.t+CH*(1-(VALUES[i]-minV)/range)]);
    const area=el('path',{fill:'rgba(0,255,200,.065)'});
    area.setAttribute('d',`M${pts[0][0]},${PAD.t+CH} `+pts.map(p=>`L${p[0]},${p[1]}`).join(' ')+` L${pts[n-1][0]},${PAD.t+CH} Z`);
    svg.appendChild(area);
    const line=el('path',{fill:'none',stroke:COLORS[0]||'#00ffc8','stroke-width':'2.5','stroke-linejoin':'round'});
    line.setAttribute('d','M'+pts.map(p=>p.join(',')).join(' L'));
    svg.appendChild(line);
    pts.forEach(([x,y],i)=>{
      const c=el('circle',{cx:x,cy:y,r:'5',fill:COLORS[i%COLORS.length]||'#00ffc8',stroke:'#04080f','stroke-width':'2'});
      c.addEventListener('mouseenter',function(){this.setAttribute('r','8');});
      c.addEventListener('mouseleave',function(){this.setAttribute('r','5');});
      svg.appendChild(c);
      svg.appendChild(el('text',{x,y:y-14,'text-anchor':'middle',fill:'#e8f4f8','font-size':'11','font-family':"'Consolas',monospace"},VALUES[i]));
      svg.appendChild(el('text',{x,y:PAD.t+CH+18,'text-anchor':'middle',fill:'rgba(232,244,248,.6)','font-size':'11','font-family':"'Consolas',monospace"},LABELS[i].length>12?LABELS[i].slice(0,12)+'…':LABELS[i]));
    });
  }
  if(X_LABEL)svg.appendChild(el('text',{x:PAD.l+CW/2,y:H-4,'text-anchor':'middle',fill:'rgba(0,255,200,.4)','font-size':'11','font-family':"'Consolas',monospace"},X_LABEL));
  wrap.appendChild(svg);
}
</script>
</body>
</html>"""

# ─── Flashcard HTML Template ──────────────────────────────────────────────────
FLASHCARD_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><title>__TOPIC__ — Flashcards</title>
<style>
* {margin:0;padding:0;box-sizing:border-box}
body {background:#04080f;font-family:'Consolas',monospace;color:#e8f4f8;height:100vh;overflow:hidden;display:flex;flex-direction:column;align-items:center;justify-content:center}
#hdr {position:fixed;top:0;left:0;right:0;height:36px;background:rgba(0,0,0,.9);border-bottom:1px solid rgba(0,255,200,.2);display:flex;align-items:center;justify-content:center;letter-spacing:3px;font-size:11px;color:rgba(0,255,200,.7);text-transform:uppercase;z-index:10}
.scanline {position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,200,.007) 2px,rgba(0,255,200,.007) 4px);pointer-events:none;z-index:5}
#prog-wrap {position:fixed;top:36px;left:0;right:0;height:3px;background:rgba(0,255,200,.1)}
#prog-bar {height:100%;background:#00ffc8;transition:width .3s;box-shadow:0 0 8px #00ffc8}
#main {display:flex;flex-direction:column;align-items:center;gap:20px;padding-top:46px}
#scene {width:580px;height:300px;perspective:1200px;cursor:pointer}
#card {width:100%;height:100%;position:relative;transform-style:preserve-3d;transition:transform .55s cubic-bezier(.4,0,.2,1)}
#card.flipped {transform:rotateY(180deg)}
.face {position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:32px;border-radius:14px;backface-visibility:hidden;text-align:center}
.front {background:rgba(0,8,28,.95);border:1px solid rgba(0,255,200,.28);box-shadow:0 0 40px rgba(0,255,200,.07),inset 0 0 30px rgba(0,255,200,.03)}
.back  {background:rgba(0,12,38,.95);border:1px solid rgba(0,160,255,.32);box-shadow:0 0 40px rgba(0,160,255,.09),inset 0 0 30px rgba(0,160,255,.04);transform:rotateY(180deg)}
.tag {font-size:9px;letter-spacing:3px;opacity:.45;margin-bottom:16px;text-transform:uppercase}
.front .tag {color:#00ffc8} .back .tag {color:#00b4ff}
.txt {font-size:18px;line-height:1.65}
.back .txt {font-size:15px;color:rgba(210,232,255,.9)}
.known-badge {position:absolute;top:14px;right:16px;font-size:10px;letter-spacing:2px;color:#00ffc8;opacity:0;transition:opacity .2s}
#card.is-known .known-badge {opacity:.8}
#flip-hint {font-size:9px;letter-spacing:2px;color:rgba(0,255,200,.25);text-transform:uppercase}
.row {display:flex;gap:12px;align-items:center}
.btn {padding:9px 20px;border-radius:8px;border:1px solid rgba(0,255,200,.28);background:rgba(0,255,200,.05);color:#00ffc8;font-family:'Consolas',monospace;font-size:11px;letter-spacing:1px;cursor:pointer;transition:all .2s;text-transform:uppercase}
.btn:hover {background:rgba(0,255,200,.14);box-shadow:0 0 12px rgba(0,255,200,.18)}
.btn.active {border-color:#00ffc8;background:rgba(0,255,200,.14)}
#ctr {font-size:11px;color:rgba(0,255,200,.45);letter-spacing:2px;min-width:80px;text-align:center}
#score {font-size:10px;color:rgba(0,255,200,.3);letter-spacing:2px}
</style>
</head>
<body>
<div id="hdr">// __TOPIC__ &nbsp;&middot;&nbsp; FLASHCARDS</div>
<div class="scanline"></div>
<div id="prog-wrap"><div id="prog-bar"></div></div>
<div id="main">
  <div id="scene"><div id="card">
    <div class="face front"><div class="tag">// question</div><div class="txt" id="ftxt"></div><div class="known-badge">&#10003; KNOWN</div></div>
    <div class="face back"><div class="tag">// answer</div><div class="txt" id="btxt"></div></div>
  </div></div>
  <div id="flip-hint">CLICK CARD &middot; SPACE TO FLIP &middot; ARROWS TO NAVIGATE</div>
  <div class="row">
    <button class="btn" id="prev">&#8592;</button>
    <span id="ctr">1 / 1</span>
    <button class="btn" id="next">&#8594;</button>
  </div>
  <div class="row">
    <button class="btn" id="knownBtn">&#10003; KNOWN</button>
    <button class="btn" id="shuf">&#8635; SHUFFLE</button>
    <button class="btn" id="rst">&#9675; RESET</button>
  </div>
  <div id="score">KNOWN: <span id="kc">0</span> / <span id="tc">0</span></div>
</div>
<script>
const CARDS=__CARDS_JSON__;
let deck=CARDS.map((c,i)=>({...c,oi:i})),idx=0,known=new Set();
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=~~(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function render(){
  const c=deck[idx];
  document.getElementById('ftxt').textContent=c.front;
  document.getElementById('btxt').textContent=c.back;
  document.getElementById('ctr').textContent=`${idx+1} / ${deck.length}`;
  document.getElementById('prog-bar').style.width=`${(idx+1)/deck.length*100}%`;
  document.getElementById('kc').textContent=known.size;
  document.getElementById('tc').textContent=CARDS.length;
  const card=document.getElementById('card');
  card.classList.remove('flipped');
  card.classList.toggle('is-known',known.has(c.oi));
  document.getElementById('knownBtn').classList.toggle('active',known.has(c.oi));
}
document.getElementById('scene').addEventListener('click',()=>document.getElementById('card').classList.toggle('flipped'));
document.getElementById('prev').addEventListener('click',()=>{idx=(idx-1+deck.length)%deck.length;render()});
document.getElementById('next').addEventListener('click',()=>{idx=(idx+1)%deck.length;render()});
document.getElementById('knownBtn').addEventListener('click',()=>{const k=deck[idx].oi;known.has(k)?known.delete(k):known.add(k);render()});
document.getElementById('shuf').addEventListener('click',()=>{shuffle(deck);idx=0;render()});
document.getElementById('rst').addEventListener('click',()=>{deck=CARDS.map((c,i)=>({...c,oi:i}));known.clear();idx=0;render()});
document.addEventListener('keydown',e=>{
  if(e.code==='Space'){e.preventDefault();document.getElementById('card').classList.toggle('flipped')}
  else if(e.code==='ArrowRight')document.getElementById('next').click();
  else if(e.code==='ArrowLeft')document.getElementById('prev').click();
  else if(e.code==='KeyK')document.getElementById('knownBtn').click();
});
render();
</script>
</body>
</html>"""

CHUNK = 1024; FORMAT = pyaudio.paInt16; CHANNELS = 1; RATE = 44100
CLAP_THRESHOLD = 1400; DOUBLE_CLAP_MAX = 1.2; DOUBLE_CLAP_DEBOUNCE = 0.12

# ─── State ────────────────────────────────────────────────────────────────────
active               = False
conversation_history = []
visual_state         = "idle"   # idle | waking | listening | speaking

# ─── News & Weather ───────────────────────────────────────────────────────────
def fetch_weather():
    if not HAS_REQUESTS: return None
    try:
        r = _requests.get("https://wttr.in/?format=%C,+%t", timeout=5)
        return r.text.strip()
    except Exception: return None

def fetch_headlines(count=6):
    if not HAS_FEEDPARSER: return []
    try:
        feed = feedparser.parse('https://feeds.bbci.co.uk/news/world/rss.xml')
        out  = []
        for e in feed.entries[:count]:
            img = None
            for attr in ('media_thumbnail', 'media_content'):
                val = getattr(e, attr, None)
                if val and isinstance(val, list) and val[0].get('url'):
                    img = val[0]['url']; break
            if not img and getattr(e, 'enclosures', None):
                for enc in e.enclosures:
                    if 'image' in enc.get('type',''):
                        img = enc.get('href') or enc.get('url'); break
            out.append({'title': e.title, 'img': img})
        return out
    except Exception: return []

# ─── Memory System ────────────────────────────────────────────────────────────
MEMORY_PATH = os.path.join(BASE_DIR, "jarvis_memory.json")
_memory_lock = threading.Lock()

def _default_memory():
    return {"commands": [], "habits": {}, "birthdays": [],
            "wake_count": 0, "last_wake": 0,
            "gcal_ics_url": "", "gcal_birthdays_ics_url": "",
            "gmail_imap_user": "", "gmail_imap_pass": "",
            "todos": [], "notes": [], "facts": {}, "reminders": []}

def load_memory():
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            base = _default_memory(); base.update(data); return base
        except Exception as e:
            print(f"Memory load error: {e}")
    return _default_memory()

def save_memory(mem):
    with _memory_lock:
        try:
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(mem, f, indent=2, default=str)
        except Exception as e:
            print(f"Memory save error: {e}")

def record_command(command):
    mem = load_memory()
    mem.setdefault("commands", []).append({"text": command, "time": time.time()})
    mem["commands"] = mem["commands"][-200:]
    hour = time.localtime().tm_hour
    habits = mem.setdefault("habits", {})
    habits[f"h{hour}"] = habits.get(f"h{hour}", 0) + 1
    save_memory(mem)

def get_suggestion(mem):
    if not mem: return None
    if mem.get("wake_count", 0) <= 1: return None
    hour = time.localtime().tm_hour
    recent = " ".join((c.get("text","") or "").lower() for c in mem.get("commands", [])[-40:])
    if 6 <= hour < 11 and "spotify" in recent:
        return "Shall I resume your morning playlist?"
    if 20 <= hour or hour < 2:
        return "Working late, I see."
    return None

def build_memory_context(mem):
    if not mem:
        return ""
    lines = []
    wc = mem.get("wake_count", 0)
    lt = time.localtime()
    lines.append(f"Session #{wc}. Current local time: {time.strftime('%A %H:%M', lt)}.")

    cmds = mem.get("commands", [])[-40:]
    if cmds:
        keywords = ["spotify", "music", "jazz", "calendar", "week", "email",
                    "news", "weather", "play", "birthday", "open", "gmail"]
        topics = {}
        for c in cmds:
            t = (c.get("text") or "").lower()
            for k in keywords:
                if k in t:
                    topics[k] = topics.get(k, 0) + 1
        if topics:
            top = sorted(topics.items(), key=lambda x: -x[1])[:5]
            lines.append("Frequent past requests: " + ", ".join(f"{k} (×{v})" for k, v in top) + ".")
        recent = [c.get("text", "") for c in cmds[-5:] if c.get("text")]
        if recent:
            lines.append("Most recent commands: " + " | ".join(recent))

    habits = mem.get("habits", {})
    if habits:
        top_hours = sorted(habits.items(), key=lambda x: -x[1])[:3]
        lines.append("Most active hours: " + ", ".join(f"{h[1:]}:00" for h, _ in top_hours) + ".")

    lines.append(
        "Use this history to phrase suggestions naturally — e.g. 'As always around this hour, "
        "shall I put on some music?' or 'Your usual jazz, sir?'. Weave it in subtly; never read "
        "the data back verbatim, and don't mention that you have a memory log."
    )
    return "\n".join(lines)

# ─── Mind Map Generator ───────────────────────────────────────────────────────
def generate_mindmap_file(topic, nodes, categories):
    import re as _re
    edges = []
    html = MINDMAP_HTML_TEMPLATE
    html = html.replace("__TITLE__",           topic)
    html = html.replace("__NODES_JSON__",      json.dumps(nodes,      ensure_ascii=False))
    html = html.replace("__EDGES_JSON__",      json.dumps(edges,      ensure_ascii=False))
    html = html.replace("__CATEGORIES_JSON__", json.dumps(categories, ensure_ascii=False))
    slug    = _re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    outpath = os.path.join(r"C:\Users\filip\Downloads", f"{slug}-mindmap.html")
    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file:///{outpath.replace(os.sep, '/')}")
    return f"Mind map saved to {outpath} and opened in browser"

# ─── Chart & Flashcard Generators ────────────────────────────────────────────
def generate_chart_file(title, chart_type, labels, values, colors=None, x_label="", y_label=""):
    import re as _re
    if not colors:
        colors = ["#00ffc8","#00b4ff","#ffd700","#ff6b6b","#c77dff","#ff9f43","#48dbfb","#ff9ff3"]
    html = CHART_HTML_TEMPLATE
    html = html.replace("__TITLE__",       title)
    html = html.replace("__CHART_TYPE__",  chart_type)
    html = html.replace("__LABELS_JSON__", json.dumps(labels))
    html = html.replace("__VALUES_JSON__", json.dumps(values))
    html = html.replace("__COLORS_JSON__", json.dumps(colors))
    html = html.replace("__X_LABEL__",    x_label)
    html = html.replace("__Y_LABEL__",    y_label)
    slug    = _re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    outpath = os.path.join(r"C:\Users\filip\Downloads", f"{slug}-chart.html")
    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file:///{outpath.replace(os.sep, '/')}")
    return f"Chart saved to {outpath} and opened in browser"

def generate_flashcard_file(topic, cards):
    import re as _re
    html = FLASHCARD_HTML_TEMPLATE
    html = html.replace("__TOPIC__",      topic)
    html = html.replace("__CARDS_JSON__", json.dumps(cards, ensure_ascii=False))
    slug    = _re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    outpath = os.path.join(r"C:\Users\filip\Downloads", f"{slug}-flashcards.html")
    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file:///{outpath.replace(os.sep, '/')}")
    return f"Flashcards saved to {outpath} and opened in browser"

# ─── To-Do List ───────────────────────────────────────────────────────────────
def manage_todo(action, text="", item_id=None):
    mem   = load_memory()
    todos = mem.setdefault("todos", [])
    if action == "add":
        new_id = max((t.get("id", 0) for t in todos), default=0) + 1
        todos.append({"id": new_id, "text": text, "done": False, "created": time.time()})
        save_memory(mem)
        return f"Added todo #{new_id}: {text}"
    elif action == "complete":
        for t in todos:
            if t.get("id") == item_id or (text and text.lower() in t.get("text","").lower()):
                t["done"] = True; save_memory(mem); return f"Done: {t['text']}"
        return "Item not found."
    elif action == "delete":
        before = len(todos)
        mem["todos"] = [t for t in todos if not (t.get("id") == item_id or (text and text.lower() in t.get("text","").lower()))]
        save_memory(mem)
        return f"Deleted {before - len(mem['todos'])} item(s)."
    elif action == "list":
        pending = [t for t in todos if not t.get("done")]
        done    = [t for t in todos if t.get("done")]
        lines   = [f"PENDING ({len(pending)}):"]
        lines  += [f"  #{t['id']} {t['text']}" for t in pending] or ["  — none"]
        lines  += [f"\nDONE ({len(done)}):"]
        lines  += [f"  #{t['id']} {t['text']}" for t in done[-5:]] or ["  — none"]
        return "\n".join(lines)
    elif action == "clear_done":
        mem["todos"] = [t for t in todos if not t.get("done")]
        save_memory(mem); return "Cleared completed todos."
    return "Unknown action. Use: add, complete, delete, list, clear_done"

# ─── Notes ────────────────────────────────────────────────────────────────────
def take_note(title, content):
    import datetime as _dt
    mem   = load_memory()
    notes = mem.setdefault("notes", [])
    notes.append({"title": title, "content": content, "date": _dt.datetime.now().isoformat()})
    mem["notes"] = notes[-500:]
    save_memory(mem)
    return f"Note saved: '{title}'"

def list_notes(query=""):
    mem   = load_memory()
    notes = mem.get("notes", [])
    if query:
        notes = [n for n in notes if query.lower() in n.get("title","").lower() or query.lower() in n.get("content","").lower()]
    if not notes:
        return "No notes found."
    out = []
    for n in notes[-10:]:
        snippet = n.get("content","")[:120]
        out.append(f"[{n['date'][:10]}] {n['title']}: {snippet}{'…' if len(n.get('content',''))>120 else ''}")
    return "\n".join(out)

# ─── Persistent Facts ─────────────────────────────────────────────────────────
def remember_fact(key, value):
    mem = load_memory()
    mem.setdefault("facts", {})[key] = value
    save_memory(mem)
    return f"Remembered: {key} = {value}"

def recall_facts(key=""):
    mem   = load_memory()
    facts = mem.get("facts", {})
    if not facts:
        return "No facts stored."
    if key:
        return f"{key}: {facts.get(key, 'Not found')}"
    return "\n".join(f"{k}: {v}" for k, v in facts.items())

# ─── Stock / Crypto Prices ────────────────────────────────────────────────────
def get_stock_price(symbol):
    if not HAS_REQUESTS:
        return "requests not available"
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?interval=1d&range=1d"
        r   = _requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        meta = r.json()["chart"]["result"][0]["meta"]
        price    = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        currency = meta.get("currency", "USD")
        name     = meta.get("longName") or meta.get("shortName") or symbol.upper()
        change   = meta.get("regularMarketChangePercent", 0)
        sign     = "+" if change >= 0 else ""
        return f"{name}: {price:.2f} {currency}  ({sign}{change:.2f}%)"
    except Exception as e:
        return f"Could not fetch price for {symbol}: {e}"

# ─── Wikipedia ────────────────────────────────────────────────────────────────
def get_wikipedia(query, sentences=4):
    if not HAS_REQUESTS:
        return "requests not available"
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query)
        r   = _requests.get(url, timeout=8, headers={"User-Agent": "JarvisBot/1.0"})
        if r.status_code == 200:
            import re as _re
            extract = r.json().get("extract", "")
            parts   = _re.split(r'(?<=[.!?])\s+', extract)
            return " ".join(parts[:sentences]) if parts else extract
        return f"No Wikipedia article found for '{query}'"
    except Exception as e:
        return f"Wikipedia error: {e}"

# ─── Process Management ───────────────────────────────────────────────────────
def kill_process_by_name(name):
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if name.lower() in proc.info["name"].lower():
                proc.kill(); killed.append(proc.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return f"Killed: {', '.join(killed)}" if killed else f"No process found matching '{name}'"

# ─── Clipboard ────────────────────────────────────────────────────────────────
def clipboard_get():
    try:
        r = subprocess.run(["powershell","-command","Get-Clipboard"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "(clipboard is empty)"
    except Exception as e:
        return f"Clipboard read error: {e}"

def clipboard_set(text):
    try:
        escaped = text.replace('"', '`"')
        subprocess.run(["powershell","-command",f'Set-Clipboard -Value "{escaped}"'],
                       capture_output=True, text=True, timeout=5)
        return f"Clipboard set ({len(text)} chars)"
    except Exception as e:
        return f"Clipboard write error: {e}"

# ─── File Management ──────────────────────────────────────────────────────────
def download_url_to_file(url, filename=""):
    if not HAS_REQUESTS:
        return "requests not available"
    import re as _re
    if not filename:
        filename = url.split("/")[-1].split("?")[0] or "download"
        filename = _re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    outpath = os.path.join(r"C:\Users\filip\Downloads", filename)
    try:
        r = _requests.get(url, timeout=30, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with open(outpath, "wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        return f"Downloaded to {outpath}"
    except Exception as e:
        return f"Download failed: {e}"

def open_file_default(path):
    try:
        os.startfile(path); return f"Opened {path}"
    except Exception as e:
        return f"Could not open {path}: {e}"

def file_operation(operation, src, dst=""):
    import shutil as _shutil
    try:
        if operation == "move":
            _shutil.move(src, dst); return f"Moved {src} → {dst}"
        elif operation == "copy":
            _shutil.copy2(src, dst); return f"Copied {src} → {dst}"
        elif operation == "delete":
            if os.path.isfile(src): os.remove(src)
            elif os.path.isdir(src): _shutil.rmtree(src)
            return f"Deleted {src}"
        elif operation == "rename":
            os.rename(src, dst); return f"Renamed {src} → {dst}"
        return "Unknown op. Use: move, copy, delete, rename"
    except Exception as e:
        return f"File operation error: {e}"

# ─── Network Info ─────────────────────────────────────────────────────────────
def get_network_info():
    import socket as _socket
    lines = []
    try:
        hostname  = _socket.gethostname()
        local_ip  = _socket.gethostbyname(hostname)
        lines.append(f"Hostname: {hostname}")
        lines.append(f"Local IP: {local_ip}")
    except Exception as e:
        lines.append(f"IP error: {e}")
    try:
        r = subprocess.run(["netsh","wlan","show","interfaces"],
                           capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if "SSID" in line and "BSSID" not in line:
                lines.append(f"WiFi SSID: {line.split(':',1)[1].strip()}"); break
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["powershell","-command",
             "Test-Connection 8.8.8.8 -Count 1 | Select-Object -ExpandProperty ResponseTime"],
            capture_output=True, text=True, timeout=8)
        ms = r.stdout.strip()
        if ms and ms.isdigit():
            lines.append(f"Ping (Google): {ms}ms")
    except Exception:
        pass
    return "\n".join(lines) if lines else "Network info unavailable"

# ─── Timer ────────────────────────────────────────────────────────────────────
def set_timer(seconds, label="Timer"):
    def _run(secs, lbl):
        time.sleep(float(secs))
        speak(f"{lbl} is up, sir.")
        try:
            subprocess.Popen(
                ["powershell","-command",
                 f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");'
                 f'[System.Windows.Forms.MessageBox]::Show("{lbl} complete!", "JARVIS Timer")'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    threading.Thread(target=_run, args=(seconds, label), daemon=True).start()
    m, s = divmod(int(seconds), 60); h, m = divmod(m, 60)
    parts = ([f"{h}h"] if h else []) + ([f"{m}m"] if m else []) + ([f"{s}s"] if s else [])
    return f"Timer set: '{label}' fires in {' '.join(parts) or '0s'}"

# ─── Calendar / Birthdays ─────────────────────────────────────────────────────
def _parse_ics_line(line):
    if ":" not in line: return None, None, {}
    key_part, value = line.split(":", 1)
    params = {}
    if ";" in key_part:
        parts = key_part.split(";")
        key = parts[0]
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1); params[k.upper()] = v
    else:
        key = key_part
    return key.upper(), value, params

def _parse_ics_datetime(value, params):
    import datetime as _dt
    v = value.strip().replace("Z", "")
    try:
        if params.get("VALUE") == "DATE" or len(v) == 8:
            return _dt.datetime.strptime(v[:8], "%Y%m%d")
        return _dt.datetime.strptime(v[:15], "%Y%m%dT%H%M%S")
    except Exception:
        return None

def _unfold_ics(text):
    lines = []
    for raw in text.splitlines():
        if (raw.startswith(" ") or raw.startswith("\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw.rstrip("\r"))
    return lines

def fetch_calendar_events(days=7):
    if not HAS_REQUESTS: return []
    mem = load_memory()
    url = (mem.get("gcal_ics_url") or "").strip()
    if not url: return []
    import datetime as _dt
    try:
        r = _requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"Calendar HTTP {r.status_code}")
            return []
        events = []; in_event = False; cur = {}
        for line in _unfold_ics(r.text):
            if line == "BEGIN:VEVENT": in_event = True; cur = {}
            elif line == "END:VEVENT":
                in_event = False
                if cur.get("start"):
                    events.append(cur)
                cur = {}
            elif in_event:
                key, value, params = _parse_ics_line(line)
                if key == "SUMMARY":
                    cur["summary"] = (value.replace("\\,", ",").replace("\\;", ";")
                                           .replace("\\n", " ").replace("\\N", " ")
                                           .replace("\\\\", "\\").strip())
                elif key == "DTSTART": cur["start"] = _parse_ics_datetime(value, params)
                elif key == "DTEND":   cur["end"]   = _parse_ics_datetime(value, params)
        today = _dt.date.today()
        end_date = today + _dt.timedelta(days=days)
        out = [e for e in events
               if e.get("start") and today <= e["start"].date() < end_date]
        out.sort(key=lambda e: e["start"])
        return out
    except Exception as e:
        print(f"Calendar fetch error: {e}")
        return []

def group_events_by_day(events, days=7):
    import datetime as _dt
    today = _dt.date.today()
    buckets = [[] for _ in range(days)]
    for e in events:
        d = e["start"].date()
        delta = (d - today).days
        if 0 <= delta < days:
            has_time = e["start"].time() != _dt.time(0, 0)
            label = e.get("summary", "(untitled)")
            if has_time:
                label = f"{e['start'].strftime('%H:%M')} {label}"
            buckets[delta].append(label)
    return buckets

def _fetch_birthday_ics():
    """Fetch birthdays from Google Birthday calendar ICS. Returns list of {name, month, day}."""
    if not HAS_REQUESTS: return []
    mem = load_memory()
    url = (mem.get("gcal_birthdays_ics_url") or "").strip()
    if not url: return []
    try:
        r = _requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"Birthday ICS HTTP {r.status_code}"); return []
        events = []; in_event = False; cur = {}
        for line in _unfold_ics(r.text):
            if line == "BEGIN:VEVENT": in_event = True; cur = {}
            elif line == "END:VEVENT":
                in_event = False
                if cur.get("start") and cur.get("summary"):
                    events.append(cur)
                cur = {}
            elif in_event:
                key, value, params = _parse_ics_line(line)
                if key == "SUMMARY":
                    s = (value.replace("\\,", ",").replace("\\;", ";")
                              .replace("\\n", " ").replace("\\\\", "\\").strip())
                    # Google formats these as "Alice Smith's birthday" — strip the suffix
                    low = s.lower()
                    for suf in ("'s birthday", "’s birthday", " birthday"):
                        if low.endswith(suf):
                            s = s[:len(s) - len(suf)]; break
                    cur["summary"] = s.strip()
                elif key == "DTSTART":
                    cur["start"] = _parse_ics_datetime(value, params)
        out = []
        for e in events:
            dt = e.get("start")
            if dt: out.append({"name": e["summary"], "month": dt.month, "day": dt.day})
        return out
    except Exception as e:
        print(f"Birthday ICS fetch error: {e}"); return []

def upcoming_birthdays(days=30):
    import datetime as _dt
    mem = load_memory()
    today = _dt.date.today()
    out = []
    seen = set()

    # manual entries
    for b in mem.get("birthdays", []):
        try:
            name = b["name"]; m, d = b["date"].split("-")
            m, d = int(m), int(d)
        except Exception:
            continue
        key = (name.lower().strip(), m, d)
        if key in seen: continue
        seen.add(key)
        this_year = _dt.date(today.year, m, d)
        if this_year < today:
            this_year = _dt.date(today.year + 1, m, d)
        delta_d = (this_year - today).days
        if 0 <= delta_d <= days:
            out.append({"name": name, "date": this_year, "days": delta_d})

    # ICS-sourced birthdays
    for b in _fetch_birthday_ics():
        try:
            m, d = int(b["month"]), int(b["day"])
        except Exception:
            continue
        key = (b["name"].lower().strip(), m, d)
        if key in seen: continue
        seen.add(key)
        try:
            this_year = _dt.date(today.year, m, d)
        except ValueError:
            continue
        if this_year < today:
            this_year = _dt.date(today.year + 1, m, d)
        delta_d = (this_year - today).days
        if 0 <= delta_d <= days:
            out.append({"name": b["name"], "date": this_year, "days": delta_d})

    out.sort(key=lambda x: x["days"])
    return out

class NewsCard:
    IMG_W, IMG_H = 158, 102
    CARD_W, CARD_H = 475, 120

    def __init__(self, title, tx, ty, delay=0.0, tag="NEWS",
                 img_url=None, fly_dx=-500, fly_dy=0):
        import random as _r
        self.title   = title
        self.tag     = tag
        self.tx, self.ty = tx, ty
        self.x = tx + fly_dx
        self.y = ty + fly_dy
        self.alpha   = 0.0
        self.phase   = _r.uniform(0, 6.283)
        self.delay   = delay
        self.age     = 0.0
        self.alive   = True
        self.lifetime = 45.0
        self.img_surf    = None
        self._img_bytes  = None
        self._dl_done    = False
        self._surf_built = False
        self._glitch_t   = _r.uniform(4, 9)
        self._glitch_on  = False
        self._glitch_dur = 0.0
        if img_url and HAS_REQUESTS:
            import threading
            threading.Thread(target=self._download, args=(img_url,), daemon=True).start()
        else:
            self._dl_done = True

    def _download(self, url):
        try:
            r = _requests.get(url, timeout=6)
            self._img_bytes = r.content
        except Exception:
            pass
        self._dl_done = True

    def _build_surf(self):
        if self._img_bytes:
            try:
                import io as _io
                raw = pygame.image.load(_io.BytesIO(self._img_bytes), "img.jpg")
                raw = pygame.transform.smoothscale(raw, (self.IMG_W, self.IMG_H))
                raw = raw.convert()
                # holographic blue tint
                tint = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
                tint.fill((0, 30, 115, 95))
                raw.blit(tint, (0, 0))
                # horizontal scanlines
                sl = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
                for sy in range(0, self.IMG_H, 2):
                    pygame.draw.line(sl, (0, 0, 0, 72), (0, sy), (self.IMG_W, sy))
                raw.blit(sl, (0, 0))
                # edge vignette
                vg = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
                for edge in range(14):
                    pygame.draw.rect(vg, (0, 0, 0, int(88*(1-edge/14))),
                                     (edge, edge, self.IMG_W-edge*2, self.IMG_H-edge*2), 1)
                raw.blit(vg, (0, 0))
                self.img_surf = raw
            except Exception as ex:
                print(f"[card img] {ex}")
        self._surf_built = True

    def update(self, dt):
        import math as _m, random as _r
        self.age += dt
        if self.age < self.delay:
            return
        a = self.age - self.delay
        if self._dl_done and not self._surf_built:
            self._build_surf()
        if a < 1.0:
            self.alpha = min(1.0, a)
            self.x += (self.tx - self.x) * 0.15
            self.y += (self.ty - self.y) * 0.15
        elif a > self.lifetime - 1.2:
            self.alpha = max(0.0, 1.0 - (a - (self.lifetime - 1.2)) / 1.2)
        else:
            self.y = self.ty + 7 * _m.sin(self.phase + a * 1.05)
        self._glitch_t -= dt
        if self._glitch_t <= 0 and a > 2.0:
            self._glitch_on  = True
            self._glitch_dur = 0.14
            self._glitch_t   = _r.uniform(5, 11)
        if self._glitch_on:
            self._glitch_dur -= dt
            if self._glitch_dur <= 0:
                self._glitch_on = False
        if self.age > self.lifetime + self.delay:
            self.alive = False

    def draw(self, screen, font_tag, font_body):
        import math as _m
        if self.alpha <= 0:
            return
        a   = int(self.alpha * 255)
        W, H = self.CARD_W, self.CARD_H
        x   = int(self.x) - W // 2
        y   = int(self.y) - H // 2

        # dark panel
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((0, 5, 20, int(a * 0.90)))
        screen.blit(bg, (x, y))

        # image section
        ix, iy = x + 8, y + 9
        if self.img_surf:
            ic = self.img_surf.copy()
            ic.set_alpha(a)
            if self._glitch_on:
                off = 3
                for dx2, dy2 in [(-off, 0), (off, 0), (0, -off)]:
                    screen.blit(ic, (ix+dx2, iy+dy2), special_flags=pygame.BLEND_ADD)
            else:
                screen.blit(ic, (ix, iy))
            pygame.draw.rect(screen, (0, 150, 255, int(a*0.65)),
                             (ix-1, iy-1, self.IMG_W+2, self.IMG_H+2), 1)
        else:
            # animated grid placeholder
            pg = pygame.Surface((self.IMG_W, self.IMG_H), pygame.SRCALPHA)
            pg.fill((0, 10, 38, int(a*0.75)))
            ta = self.age * 1.4
            for gi in range(6):
                for gj in range(4):
                    ga = int(25 + 18*_m.sin(ta + gi*0.9 + gj*1.3))
                    gx2 = gi*(self.IMG_W//6); gy2 = gj*(self.IMG_H//4)
                    pygame.draw.rect(pg, (0, 80, 210, ga),
                                     (gx2+2, gy2+2, self.IMG_W//6-4, self.IMG_H//4-4), 1)
            if not self._dl_done:
                dots = "." * (int(self.age*3) % 4)
                lt = font_tag.render("LOADING" + dots, True, (0, 130, 220))
                lt.set_alpha(a // 2)
                pg.blit(lt, (self.IMG_W//2 - lt.get_width()//2, self.IMG_H//2 - 6))
            screen.blit(pg, (ix, iy))
            pygame.draw.rect(screen, (0, 80, 180, int(a*0.5)),
                             (ix-1, iy-1, self.IMG_W+2, self.IMG_H+2), 1)

        # vertical divider
        div_x = ix + self.IMG_W + 6
        pygame.draw.line(screen, (0, 90, 200, int(a*0.45)),
                         (div_x, y+7), (div_x, y+H-7), 1)

        # text section
        tx2 = div_x + 10
        tw  = W - (self.IMG_W + 34)

        # tag label
        ts = font_tag.render(">> " + self.tag, True, (0, 210, 255))
        ts.set_alpha(a)
        screen.blit(ts, (tx2, y+9))
        pygame.draw.line(screen, (0, 140, 255, int(a*0.35)),
                         (tx2, y+22), (tx2+tw-4, y+22), 1)

        # word-wrapped headline
        words = self.title.split()
        lines2 = []; line2 = ""
        for w in words:
            test = (line2 + " " + w).strip()
            if font_body.size(test)[0] < tw - 4:
                line2 = test
            else:
                lines2.append(line2); line2 = w
        lines2.append(line2)
        for i2, ln in enumerate(lines2[:3]):
            col = (235, 242, 255) if i2 == 0 else (165, 188, 220)
            hs  = font_body.render(ln, True, col)
            hs.set_alpha(a)
            screen.blit(hs, (tx2, y+28 + i2*17))

        # lifetime progress bar
        prog = max(0.0, 1.0 - max(0.0, self.age - self.delay) / self.lifetime)
        bx2 = tx2; by2 = y+H-11; bw2 = tw-4
        pygame.draw.rect(screen, (0, 35, 90,  int(a*0.5)),   (bx2, by2, bw2, 3))
        pygame.draw.rect(screen, (0, 170, 255, int(a*0.85)), (bx2, by2, int(bw2*prog), 3))

        # outer border (glows bright during glitch)
        bd = pygame.Surface((W, H), pygame.SRCALPHA)
        bc = (0, 220, 255, int(a*0.9)) if self._glitch_on else (0, 120, 255, int(a*0.55))
        pygame.draw.rect(bd, bc, (0, 0, W, H), 1)
        screen.blit(bd, (x, y))

        # corner ticks
        tc = (0, 200, 255, a)
        for cx2, cy2, sx, sy in [(x,y,1,1),(x+W,y,-1,1),(x,y+H,1,-1),(x+W,y+H,-1,-1)]:
            pygame.draw.lines(screen, tc, False,
                              [(cx2+sx*13, cy2),(cx2, cy2),(cx2, cy2+sy*13)], 1)

class DayCard:
    """Holographic single-day tile — part of the weekly preview strip."""
    DEFAULT_W, DEFAULT_H = 260, 210

    def __init__(self, day_label, events, tx, ty, delay=0.0,
                 fly_dx=0, fly_dy=-700, w=None, h=None, tag_color=(0, 210, 255),
                 lifetime=55.0):
        import random as _r
        self.day_label = day_label
        self.events    = events or []
        self.tx, self.ty = tx, ty
        self.x = tx + fly_dx
        self.y = ty + fly_dy
        self.alpha   = 0.0
        self.delay   = delay
        self.age     = 0.0
        self.alive   = True
        self.lifetime = lifetime
        self.phase   = _r.uniform(0, 6.283)
        self.CARD_W = w or self.DEFAULT_W
        self.CARD_H = h or self.DEFAULT_H
        self.tag_color = tag_color
        self._glitch_t   = _r.uniform(3, 8)
        self._glitch_on  = False
        self._glitch_dur = 0.0

    def update(self, dt):
        import math as _m, random as _r
        self.age += dt
        if self.age < self.delay: return
        a = self.age - self.delay
        if a < 1.0:
            self.alpha = min(1.0, a)
            self.x += (self.tx - self.x) * 0.18
            self.y += (self.ty - self.y) * 0.18
        elif a > self.lifetime - 1.2:
            self.alpha = max(0.0, 1.0 - (a - (self.lifetime - 1.2)) / 1.2)
        else:
            self.y = self.ty + 4 * _m.sin(self.phase + a * 1.1)
        self._glitch_t -= dt
        if self._glitch_t <= 0 and a > 2.0:
            self._glitch_on  = True
            self._glitch_dur = 0.12
            self._glitch_t   = _r.uniform(6, 12)
        if self._glitch_on:
            self._glitch_dur -= dt
            if self._glitch_dur <= 0: self._glitch_on = False
        if self.age > self.lifetime + self.delay:
            self.alive = False

    def draw(self, screen, font_tag, font_body):
        if self.alpha <= 0: return
        a = int(self.alpha * 255)
        W, H = self.CARD_W, self.CARD_H
        x = int(self.x) - W // 2
        y = int(self.y) - H // 2

        # panel
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((0, 5, 22, int(a * 0.88)))
        screen.blit(bg, (x, y))

        # header band
        hh = 26
        hdr = pygame.Surface((W, hh), pygame.SRCALPHA)
        hdr.fill((0, 45, 115, int(a * 0.65)))
        screen.blit(hdr, (x, y))
        ts = font_tag.render(self.day_label, True, (220, 240, 255))
        ts.set_alpha(a)
        screen.blit(ts, (x + W // 2 - ts.get_width() // 2, y + 6))

        # event lines (word-wrapped, max 2 wrapped lines per event)
        yy = y + hh + 8
        max_w = W - 18
        line_h = 17
        if not self.events:
            es = font_body.render("— clear —", True, (100, 140, 200))
            es.set_alpha(int(a * 0.75))
            screen.blit(es, (x + W // 2 - es.get_width() // 2, yy + 10))
        else:
            total_line_budget = max(2, (H - hh - 18) // line_h)
            rendered_count = 0          # how many source events fully fit
            used_lines = 0
            # reserve 1 line for "+N more" footer if needed
            for idx, ev in enumerate(self.events):
                # wrap this event to at most 2 lines
                bullet = "• "
                indent = "  "
                words = str(ev).split()
                wrapped = []
                cur_line = bullet
                for w in words:
                    test = cur_line + (w if cur_line in (bullet, indent) else " " + w)
                    if font_body.size(test)[0] <= max_w:
                        cur_line = test
                    else:
                        wrapped.append(cur_line)
                        cur_line = indent + w
                        if len(wrapped) >= 2:
                            break
                if len(wrapped) < 2:
                    wrapped.append(cur_line)
                # ellipsize last line if it overflows
                last = wrapped[-1]
                if font_body.size(last)[0] > max_w:
                    while font_body.size(last + "…")[0] > max_w and len(last) > 3:
                        last = last[:-1]
                    wrapped[-1] = last + "…"
                # remaining budget check (reserve 1 line for "+N more")
                remaining_events = len(self.events) - idx
                reserve = 1 if remaining_events > 1 else 0
                if used_lines + len(wrapped) > total_line_budget - reserve:
                    break
                col_first  = (215, 232, 255)
                col_cont   = (165, 195, 235)
                for wi, ln in enumerate(wrapped):
                    es = font_body.render(ln, True, col_first if wi == 0 else col_cont)
                    es.set_alpha(a if wi == 0 else int(a * 0.85))
                    screen.blit(es, (x + 8, yy + (used_lines + wi) * line_h))
                used_lines    += len(wrapped)
                rendered_count = idx + 1
            if rendered_count < len(self.events):
                more = font_body.render(f"+{len(self.events) - rendered_count} more",
                                         True, (120, 170, 220))
                more.set_alpha(int(a * 0.85))
                screen.blit(more, (x + 8, yy + used_lines * line_h))

        # border
        bc = ((0, 235, 255, int(a * 0.95)) if self._glitch_on
              else (0, 135, 255, int(a * 0.6)))
        bd = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(bd, bc, (0, 0, W, H), 1)
        pygame.draw.line(bd, bc, (0, hh), (W, hh), 1)
        screen.blit(bd, (x, y))

        # corner ticks
        tc = (0, 210, 255, a)
        for cx2, cy2, sx, sy in [(x,y,1,1),(x+W,y,-1,1),(x,y+H,1,-1),(x+W,y+H,-1,-1)]:
            pygame.draw.lines(screen, tc, False,
                              [(cx2+sx*10, cy2),(cx2, cy2),(cx2, cy2+sy*10)], 1)


class ReminderScreen:
    """Full-screen holographic overlay for viewing, adding and deleting reminders."""

    FIELD_LABELS = ["DATE  (DD/MM/YYYY)", "SUBJECT", "NOTE (optional)"]
    FIELD_KEYS   = ["date", "subject", "note"]

    def __init__(self):
        self.active  = False
        self.mode    = "list"   # "list" | "add"
        self.inputs  = {"date": "", "subject": "", "note": ""}
        self.cur_field = 0
        self.selected  = 0
        self.reminders = []
        self._err = ""
        self._err_t = 0.0
        self._t = 0.0

    def open(self):
        self.active = True
        self.mode   = "list"
        self.inputs = {"date": "", "subject": "", "note": ""}
        self.cur_field = 0
        self._err  = ""
        self._reload()

    def _reload(self):
        import datetime as _dt
        self.reminders = sorted(
            load_memory().get("reminders", []),
            key=lambda r: r.get("date", "")
        )
        self.selected = max(0, min(self.selected, len(self.reminders) - 1))

    @staticmethod
    def _fmt_date(digits):
        d = "".join(c for c in digits if c.isdigit())[:8]
        if len(d) > 4:
            return d[:2] + "/" + d[2:4] + "/" + d[4:]
        if len(d) > 2:
            return d[:2] + "/" + d[2:]
        return d

    def _parse_date(self, s):
        import datetime as _dt
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                return _dt.datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None

    def _save(self):
        date_raw = self.inputs["date"].strip()
        subject  = self.inputs["subject"].strip()
        if not subject:
            self._err = "Subject cannot be empty"; self._err_t = 2.5; return
        date_iso = self._parse_date(date_raw)
        if not date_iso:
            self._err = "Invalid date — use DD/MM/YYYY"; self._err_t = 2.5; return
        mem = load_memory()
        note = self.inputs["note"].strip()
        mem.setdefault("reminders", []).append(
            {"date": date_iso, "subject": subject, "note": note}
        )
        mem["reminders"].sort(key=lambda r: r.get("date", ""))
        save_memory(mem)
        self._reload()
        self.mode = "list"
        self.inputs = {"date": "", "subject": "", "note": ""}
        self.cur_field = 0
        full_topic = f"{subject} — {note}" if note else subject
        threading.Thread(target=run_study_pipeline, args=(full_topic,), daemon=True).start()

    def _delete_selected(self):
        if not self.reminders: return
        mem = load_memory()
        rems = mem.get("reminders", [])
        if 0 <= self.selected < len(rems):
            del rems[self.selected]
            mem["reminders"] = rems
            save_memory(mem)
            self._reload()

    def handle_event(self, event):
        if not self.active: return True
        if event.type != pygame.KEYDOWN: return True
        k = event.key
        if self.mode == "list":
            if k == pygame.K_ESCAPE:
                self.active = False
            elif k == pygame.K_UP:
                self.selected = max(0, self.selected - 1)
            elif k == pygame.K_DOWN:
                self.selected = min(len(self.reminders) - 1, self.selected + 1)
            elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
                self._delete_selected()
            elif k == pygame.K_RETURN or k == pygame.K_n:
                self.mode = "add"
                self.inputs = {"date": "", "subject": "", "note": ""}
                self.cur_field = 0
                self._err = ""
        else:  # add mode
            if k == pygame.K_ESCAPE:
                self.mode = "list"
            elif k == pygame.K_TAB:
                self.cur_field = (self.cur_field + 1) % len(self.FIELD_KEYS)
            elif k == pygame.K_RETURN:
                self._save()
            elif k == pygame.K_BACKSPACE:
                fk = self.FIELD_KEYS[self.cur_field]
                if fk == "date":
                    digits = "".join(c for c in self.inputs["date"] if c.isdigit())
                    self.inputs["date"] = self._fmt_date(digits[:-1])
                else:
                    self.inputs[fk] = self.inputs[fk][:-1]
            elif event.unicode and event.unicode.isprintable():
                fk = self.FIELD_KEYS[self.cur_field]
                if fk == "date":
                    if event.unicode.isdigit():
                        digits = "".join(c for c in self.inputs["date"] if c.isdigit())
                        self.inputs["date"] = self._fmt_date(digits + event.unicode)
                else:
                    self.inputs[fk] += event.unicode
        return True

    def draw(self, screen, font_hud, font_body, t):
        import datetime as _dt
        if not self.active: return
        self._t = t
        if self._err_t > 0: self._err_t -= 0.016

        W, H = screen.get_size()
        today = _dt.date.today().strftime("%Y-%m-%d")

        # dim background
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 2, 12, 210))
        screen.blit(dim, (0, 0))

        PW, PH = min(820, W - 80), min(600, H - 80)
        px, py = (W - PW) // 2, (H - PH) // 2

        # panel background + border
        bg = pygame.Surface((PW, PH), pygame.SRCALPHA)
        bg.fill((0, 6, 22, 240))
        screen.blit(bg, (px, py))
        pygame.draw.rect(screen, (0, 200, 255), (px, py, PW, PH), 1)

        # corner brackets
        sz = 14
        for bx, by, sx, sy in [(px,py,1,1),(px+PW,py,-1,1),(px,py+PH,1,-1),(px+PW,py+PH,-1,-1)]:
            pygame.draw.lines(screen, (0, 255, 200), False,
                              [(bx+sx*sz, by),(bx, by),(bx, by+sy*sz)], 2)

        # header
        title = font_hud.render("J.A.R.V.I.S.  ·  REMINDER SYSTEM", True, (0, 220, 255))
        screen.blit(title, (px + PW//2 - title.get_width()//2, py + 10))
        pygame.draw.line(screen, (0, 140, 200), (px+10, py+34), (px+PW-10, py+34), 1)

        if self.mode == "list":
            self._draw_list(screen, font_hud, font_body, px, py, PW, PH, today, t)
        else:
            self._draw_add(screen, font_hud, font_body, px, py, PW, PH, t)

    def _draw_list(self, screen, font_hud, font_body, px, py, PW, PH, today, t):
        import datetime as _dt
        y = py + 44
        sub = font_body.render(
            f"  {len(self.reminders)} reminder(s)   ↑↓ navigate   DEL remove   ENTER / N  add new   ESC close",
            True, (60, 120, 180))
        screen.blit(sub, (px + 14, y))
        y += 22
        pygame.draw.line(screen, (0, 80, 130), (px+10, y), (px+PW-10, y), 1)
        y += 8

        row_h = 46
        if not self.reminders:
            empty = font_hud.render("No reminders saved.", True, (40, 100, 160))
            screen.blit(empty, (px + PW//2 - empty.get_width()//2, py + PH//2 - 20))
        else:
            for i, rem in enumerate(self.reminders):
                if y + row_h > py + PH - 40: break
                is_sel = (i == self.selected)
                is_today = rem.get("date", "") == today
                is_past  = rem.get("date", "") < today

                row_col = (0, 50, 120, 180) if is_sel else (0, 15, 40, 120)
                row_s = pygame.Surface((PW - 20, row_h - 4), pygame.SRCALPHA)
                row_s.fill(row_col)
                screen.blit(row_s, (px + 10, y))
                if is_sel:
                    pygame.draw.rect(screen, (0, 200, 255), (px+10, y, PW-20, row_h-4), 1)

                date_str = rem.get("date", "")
                try:
                    d = _dt.date.fromisoformat(date_str)
                    date_disp = d.strftime("%d %b %Y")
                except Exception:
                    date_disp = date_str

                if is_today:
                    dc = (255, 220, 60)
                    tag = font_body.render("TODAY", True, (255, 220, 60))
                    screen.blit(tag, (px + PW - tag.get_width() - 16, y + 4))
                elif is_past:
                    dc = (180, 80, 80)
                else:
                    dc = (0, 195, 215)

                ds = font_hud.render(date_disp, True, dc)
                screen.blit(ds, (px + 18, y + 4))
                ss = font_body.render(rem.get("subject", ""), True, (220, 240, 255))
                screen.blit(ss, (px + 18 + ds.get_width() + 14, y + 6))
                note = rem.get("note", "")
                if note:
                    ns = font_body.render(note[:80], True, (100, 160, 200))
                    screen.blit(ns, (px + 18, y + row_h - 18))
                y += row_h

    def _draw_add(self, screen, font_hud, font_body, px, py, PW, PH, t):
        y = py + 50
        title2 = font_hud.render("ADD REMINDER", True, (0, 255, 200))
        screen.blit(title2, (px + PW//2 - title2.get_width()//2, y))
        y += 36

        for i, fk in enumerate(self.FIELD_KEYS):
            is_active = (i == self.cur_field)
            label = font_body.render(self.FIELD_LABELS[i], True,
                                     (0, 220, 255) if is_active else (60, 120, 180))
            screen.blit(label, (px + 40, y))
            y += 20

            field_w = PW - 80
            fb = pygame.Surface((field_w, 32), pygame.SRCALPHA)
            fb.fill((0, 30, 70, 200) if is_active else (0, 10, 30, 160))
            screen.blit(fb, (px + 40, y))
            border_col = (0, 220, 255) if is_active else (0, 80, 130)
            pygame.draw.rect(screen, border_col, (px+40, y, field_w, 32), 1)

            cursor = "_" if is_active and int(t * 2) % 2 == 0 else ""
            val = font_hud.render(self.inputs[fk] + cursor, True, (220, 240, 255))
            screen.blit(val, (px + 48, y + 6))
            y += 46

        if self._err and self._err_t > 0:
            err_s = font_body.render(self._err, True, (255, 80, 80))
            screen.blit(err_s, (px + PW//2 - err_s.get_width()//2, py + PH - 60))

        hint = font_body.render("TAB · next field   ENTER · save   ESC · back", True, (40, 100, 160))
        screen.blit(hint, (px + PW//2 - hint.get_width()//2, py + PH - 34))


class JarvisVisual:
    def __init__(self):
        self.W = self.H = self.cx = self.cy = 0
        self.t            = 0.0
        self.particles    = []
        self.ripples      = []
        self.news_cards   = []
        self.screen       = None
        self.clock        = None
        self.font_hud     = None
        self.font_card_body  = None
        self.font_data    = None
        self._overlay     = None
        self._glow_cache  = {}
        self.reminder_screen = ReminderScreen()
        self._sphere_nodes  = []
        self._sphere_edges  = []
        self._sphere_rot    = 0.0
        self._flow_offsets  = []   # per-edge animated flow pulse position
        self._orbit_labels  = [
            "SYS.OK", "BIOMETRIC.AUTH", "CORE.SYNC", "NET.NODE.3F",
            "ENC.AES-256", "TELEMETRY.LIVE", "RELAY.HUB", "WATCH.ACTIVE",
        ]
        self._orbit_surfs   = []
        # cinematic enhancements
        self.data_streams   = []
        self._ds_font       = None
        self._ds_char_head  = {}
        self._ds_char_body  = {}
        self._grid_surf     = None
        self._grid_y0       = 0
        self._grid_h        = 0
        self._scanline_surf = None
        self.reticules      = []
        self._reticule_cd   = 2.5
        self.power_arcs     = []
        self._arc_cd        = 4.0
        self.diag_bars      = []
        self._bloom_small   = None
        self._bloom_tiny    = None

    def setup(self):
        pygame.display.init(); pygame.font.init()
        info = pygame.display.Info()
        self.W, self.H = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN | pygame.NOFRAME)
        pygame.display.set_caption("J.A.R.V.I.S.")
        self.clock = pygame.time.Clock()
        self.cx, self.cy = self.W // 2, self.H // 2
        try:
            self.font_hud       = pygame.font.SysFont("consolas", 20, bold=True)
            self.font_card_body = pygame.font.SysFont("consolas", 13)
            self.font_data      = pygame.font.SysFont("consolas", 11)
        except Exception:
            self.font_hud = self.font_card_body = self.font_data = pygame.font.Font(None, 18)
        self._overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._init_particles()
        try:
            small = pygame.font.SysFont("consolas", 10, bold=True)
            self._orbit_surfs = [small.render(lbl, True, (130, 200, 255))
                                 for lbl in self._orbit_labels]
        except Exception:
            self._orbit_surfs = []
        self._init_cinematic()
        if HAS_NUMPY:
            self._init_sphere_numpy()
        else:
            self._init_sphere()

    def _init_cinematic(self):
        """Pre-build grid, scanlines, data-stream glyph surfs, diagnostic bars."""
        import random as _r
        # ── Scanline overlay (subtle) ─────────────────────────────────────────
        sl = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        for y in range(0, self.H, 3):
            pygame.draw.line(sl, (0, 15, 30, 22), (0, y), (self.W, y), 1)
        self._scanline_surf = sl

        # ── Perspective grid (vertical converging lines, pre-rendered) ────────
        cx = self.W // 2
        self._grid_h  = int(self.H * 0.36)
        self._grid_y0 = self.H - self._grid_h
        g = pygame.Surface((self.W, self._grid_h), pygame.SRCALPHA)
        for vx in range(-9, 10):
            if vx == 0: continue
            bot_x = cx + vx * (self.W // 11)
            a = max(18, 55 - abs(vx) * 4)
            pygame.draw.line(g, (0, 110, 210, a), (cx, 0), (bot_x, self._grid_h), 1)
        self._grid_surf = g

        # ── Data-stream glyphs (pre-rendered for speed) ───────────────────────
        try:
            self._ds_font = pygame.font.SysFont("consolas", 12, bold=True)
        except Exception:
            self._ds_font = pygame.font.Font(None, 14)
        chars = "0123456789ABCDEF#$%&@*+-=/█▓▒░"
        self._ds_chars = list(chars)
        self._ds_char_head = {c: self._ds_font.render(c, True, (225, 250, 255)) for c in chars}
        self._ds_char_body = {c: self._ds_font.render(c, True, (60, 140, 220))  for c in chars}
        self.data_streams  = []
        # left + right edge columns
        for side, base_x in [("L", 14), ("R", self.W - 14 - 12)]:
            for col_i in range(5):
                stream_len = _r.randint(18, 28)
                x = base_x + (col_i * 16 if side == "L" else -col_i * 16)
                self.data_streams.append({
                    "x": x,
                    "y": _r.uniform(-400, self.H),
                    "speed": _r.uniform(55, 120),
                    "chars": [_r.choice(chars) for _ in range(stream_len)],
                    "swap_t": 0.0,
                    "len": stream_len,
                })

        # ── Bloom scratch surfaces (allocated once) ───────────────────────────
        self._bloom_small = pygame.Surface((self.W // 4, self.H // 4))
        self._bloom_tiny  = pygame.Surface((self.W // 10, self.H // 10))

        # ── Diagnostic bars ───────────────────────────────────────────────────
        import random as _rr
        self.diag_bars = [
            {"label": "CORE PWR",  "value": 0.82, "target": 0.82, "col": (0, 200, 255)},
            {"label": "NEURAL NET","value": 0.91, "target": 0.91, "col": (0, 220, 220)},
            {"label": "UPLINK",    "value": 0.67, "target": 0.67, "col": (100, 180, 255)},
            {"label": "PROCESS",   "value": 0.55, "target": 0.55, "col": (80, 200, 255)},
            {"label": "BIO SCAN",  "value": 0.98, "target": 0.98, "col": (0, 240, 200)},
            {"label": "ENCRYPT",   "value": 0.88, "target": 0.88, "col": (130, 200, 255)},
        ]
        self._diag_t = 0.0

    def _col(self, state):
        return {
            "speaking":  ((0, 180, 255), (0, 100, 220), (0,  50, 160)),
            "listening": ((0, 230, 210), (0, 160, 180), (0,  90, 130)),
            "waking":    ((120, 160, 255), (60, 90, 220), (20, 40, 160)),
        }.get(state, ((30, 120, 240), (15, 70, 190), (5, 30, 120)))

    def _init_particles(self):
        import random as _r, math as _m
        self.particles = []
        for _ in range(22):
            angle  = _r.uniform(0, _m.tau)
            base_r = _r.uniform(215, 330)
            self.particles.append({
                "angle": angle, "base_r": base_r, "r": base_r,
                "speed":   _r.uniform(0.003, 0.010) * _r.choice([-1, 1]),
                "size":    _r.uniform(2, 4.5),
                "alpha":   _r.uniform(0.4, 0.9),
                "y_phase": _r.uniform(0, _m.tau),
                "y_amp":   _r.uniform(6, 18),
                "y_speed": _r.uniform(0.002, 0.006) * _r.choice([-1, 1]),
                "shape":   _r.choices(["dot", "diamond"], weights=[3, 2])[0],
            })

    def _init_sphere(self):
        """Fallback wireframe sphere (no numpy)."""
        import math as _m, random as _r
        N = 58
        golden = (1 + _m.sqrt(5)) / 2
        nodes = []
        for i in range(N):
            theta = _m.acos(max(-1.0, min(1.0, 1 - 2*(i+0.5)/N)))
            phi   = _m.tau * i / golden
            nodes.append((theta, phi))
        self._sphere_nodes = nodes
        def chord(a, b):
            t1,p1 = a; t2,p2 = b
            x1,y1,z1 = _m.sin(t1)*_m.cos(p1), _m.cos(t1), _m.sin(t1)*_m.sin(p1)
            x2,y2,z2 = _m.sin(t2)*_m.cos(p2), _m.cos(t2), _m.sin(t2)*_m.sin(p2)
            return _m.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
        edges = set()
        for i in range(N):
            ds = sorted((chord(nodes[i], nodes[j]), j) for j in range(N) if j != i)
            for _, j in ds[:4]:
                edges.add((min(i,j), max(i,j)))
        self._sphere_edges = list(edges)
        self._flow_offsets = [_r.uniform(0, 1.0) for _ in self._sphere_edges]
        self._glow_cache.clear()

    def _init_sphere_numpy(self):
        """Pre-compute geometry for per-pixel Phong+energy-web sphere."""
        np = _np
        R = 195
        size = R * 2 + 6
        Y, X = np.mgrid[0:size, 0:size]
        c = R + 3
        dx = (X - c).astype(np.float32)
        dy = (Y - c).astype(np.float32)
        r2 = dx**2 + dy**2
        mask = r2 <= float(R * R)
        inv_R = 1.0 / R
        nx = np.where(mask, dx * inv_R, 0.0).astype(np.float32)
        ny = np.where(mask, dy * inv_R, 0.0).astype(np.float32)
        nz = np.where(mask, np.sqrt(np.maximum(0.0, 1.0 - nx**2 - ny**2)), 0.0).astype(np.float32)
        theta = np.arccos(np.clip(ny, -1.0, 1.0)).astype(np.float32)
        phi   = np.arctan2(nx, nz).astype(np.float32)
        # Precompute theta-dependent web envelopes (constant)
        self._sp_sin_t7 = np.sin(theta * 7.0).astype(np.float32)
        self._sp_cos_t5 = np.cos(theta * 5.0).astype(np.float32)
        self._sp_sin_t4 = np.sin(theta * 4.0).astype(np.float32)
        self._sp_mask = mask
        self._sp_nx, self._sp_ny, self._sp_nz = nx, ny, nz
        self._sp_phi  = phi
        self._sp_R    = R
        self._sp_size = size
        self._sp_surf = pygame.Surface((size, size))
        self._sp_surf.set_colorkey((0, 0, 0))
        self._sp_rings = []   # rotating outer ring angles
        self._glow_cache.clear()

    def _render_sphere(self, state, t):
        """Render the numpy Phong+energy-web sphere; return Surface."""
        np = _np
        bright, mid, dim = self._col(state)
        mask = self._sp_mask
        nx, ny, nz = self._sp_nx, self._sp_ny, self._sp_nz
        phi = self._sp_phi

        # Rotating key light
        la  = t * 0.42
        lx_ = math.cos(la) * 0.70
        ly_ = -0.40
        lz_ = math.sin(la) * 0.70 + 0.65
        ln  = math.sqrt(lx_**2 + ly_**2 + lz_**2)
        lx_, ly_, lz_ = lx_/ln, ly_/ln, lz_/ln
        lx = np.float32(lx_); ly = np.float32(ly_); lz = np.float32(lz_)

        diff = np.maximum(0.0, nx*lx + ny*ly + nz*lz)

        # Blinn-Phong specular
        hx_ = lx_; hy_ = ly_; hz_ = lz_ + 1.0
        hn  = math.sqrt(hx_**2 + hy_**2 + hz_**2)
        hx  = np.float32(hx_/hn); hy = np.float32(hy_/hn); hz = np.float32(hz_/hn)
        spec = np.where(mask, np.maximum(0.0, nx*hx + ny*hy + nz*hz)**72, 0.0)

        # Fresnel rim
        fresnel = np.where(mask, (1.0 - nz)**3.5, 0.0)

        # Inner-core glow (center = high nz)
        core_glow = np.where(mask, nz**2 * 0.35, 0.0)

        # Animated energy web — two crossing sine-wave families
        phi_rot = phi + np.float32(t * 0.28)
        web_a = self._sp_sin_t7 * np.cos(phi_rot * np.float32(5.0) + np.float32(t * 0.18))
        web_b = self._sp_cos_t5 * np.sin(phi_rot * np.float32(7.0) + np.float32(t * 0.22))
        web_c = self._sp_sin_t4 * np.cos(phi_rot * np.float32(3.0) - np.float32(t * 0.12))
        web   = np.where(mask, np.exp(-np.abs(web_a + web_b + web_c * 0.5) * 5.0) * 0.85, 0.0)

        pulse = np.float32(1.0 + 0.13 * math.sin(t * (9.5 if state=="speaking" else 2.2)))

        br, bg, bb = bright[0]/255.0, bright[1]/255.0, bright[2]/255.0
        mr, mg, mb = mid[0]/255.0,   mid[1]/255.0,   mid[2]/255.0
        dr, dg, db = dim[0]/255.0,   dim[1]/255.0,   dim[2]/255.0

        r_f = np.where(mask, np.clip((
            dr * 0.08 + mr * diff * 0.45 + br * web * 0.75 +
            br * fresnel * 0.55 + br * core_glow + spec * 0.85) * pulse, 0.0, 1.0), 0.0)
        g_f = np.where(mask, np.clip((
            dg * 0.08 + mg * diff * 0.45 + bg * web * 0.75 +
            bg * fresnel * 0.60 + bg * core_glow + spec * 0.90) * pulse, 0.0, 1.0), 0.0)
        b_f = np.where(mask, np.clip((
            db * 0.12 + mb * diff * 0.50 + bb * web * 0.80 +
            bb * fresnel * 0.80 + bb * core_glow + spec * 1.00) * pulse, 0.0, 1.0), 0.0)

        arr = np.stack([(r_f * 255).astype(np.uint8),
                        (g_f * 255).astype(np.uint8),
                        (b_f * 255).astype(np.uint8)], axis=2)
        pygame.surfarray.blit_array(self._sp_surf,
                                    _np.ascontiguousarray(arr.transpose(1, 0, 2)))
        return self._sp_surf

    def _glow_surf(self, r, rgba):
        key = (r, rgba)
        if key not in self._glow_cache:
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, rgba, (r+1, r+1), r)
            self._glow_cache[key] = s
        return self._glow_cache[key]

    def _blit_c(self, surf, cx, cy):
        self.screen.blit(surf, (cx - surf.get_width()//2, cy - surf.get_height()//2))

    def _ring_on_ov(self, ov, cx, cy, r, offset, tick_n, col, w=1):
        import math as _m
        pygame.draw.circle(ov, col, (cx, cy), r, w)
        major = max(1, tick_n // 4)
        for i in range(tick_n):
            a = offset + i * _m.tau / tick_n
            tl = 9 if i % major == 0 else 4
            ca, sa = _m.cos(a), _m.sin(a)
            pygame.draw.line(ov, col,
                             (int(cx+(r-1)*ca),    int(cy+(r-1)*sa)),
                             (int(cx+(r-1-tl)*ca), int(cy+(r-1-tl)*sa)), 1)

    def _draw_reactor(self, cx, cy, state, t):
        import math as _m, random as _r
        bright, mid, dim = self._col(state)
        R = self._sp_R if HAS_NUMPY else 195

        pulse = (1.0 + 0.22*_m.sin(t*9.5) if state=="speaking"
                 else 1.0+0.14*_m.sin(t*5.5) if state=="waking"
                 else 1.0+0.05*_m.sin(t*1.4))

        # ── Atmospheric halo layers ───────────────────────────────────────────
        for i in range(9, 0, -1):
            ga = int(22*_m.exp(-i*0.42)*pulse)
            self._blit_c(self._glow_surf(R + i*11, (*dim, ga)), cx, cy)

        # ── Numpy pixel-lit sphere ─────────────────────────────────────────────
        if HAS_NUMPY:
            sp = self._render_sphere(state, t)
            self._blit_c(sp, cx, cy)
        else:
            # wireframe fallback (no numpy)
            self._sphere_rot += 0.003
            rot = self._sphere_rot
            ov = self._overlay; ov.fill((0,0,0,0))
            for theta, phi in self._sphere_nodes:
                p  = phi + rot
                x3 = _m.sin(theta)*_m.cos(p)
                y3 = _m.cos(theta)
                z3 = _m.sin(theta)*_m.sin(p)
                if z3 > 0:
                    self._blit_c(self._glow_surf(3, (*bright, int(100*z3))),
                                 cx+int(x3*R), cy-int(y3*R))
            self.screen.blit(ov,(0,0))

        # ── Thin rotating outer rings ──────────────────────────────────────────
        ov = self._overlay; ov.fill((0,0,0,0))
        for ring_r, speed, alpha in [(R+18, 0.25, 38), (R+34, -0.16, 24), (R+52, 0.10, 16)]:
            angle = t * speed
            ring_a = int(alpha * pulse)
            pygame.draw.circle(ov, (*dim, ring_a), (cx, cy), ring_r, 1)
            for k in range(8):
                a = angle + k * _m.tau/8
                pygame.draw.line(ov, (*bright, ring_a//2),
                                 (int(cx+(ring_r-5)*_m.cos(a)), int(cy+(ring_r-5)*_m.sin(a))),
                                 (int(cx+(ring_r+5)*_m.cos(a)), int(cy+(ring_r+5)*_m.sin(a))), 1)
        self.screen.blit(ov, (0,0))

        # ── Core white-hot point ──────────────────────────────────────────────
        core_r = int(14*pulse)
        for i in range(6, 0, -1):
            self._blit_c(self._glow_surf(core_r+i*7, (*bright, int(160*_m.exp(-i*0.6)))), cx, cy)
        self._blit_c(self._glow_surf(core_r,            (*bright, 230)), cx, cy)
        self._blit_c(self._glow_surf(int(core_r*0.5),   (210,235,255,250)), cx, cy)
        self._blit_c(self._glow_surf(max(1,int(core_r*0.2)), (255,255,255,255)), cx, cy)

        # ── Speaking ripples ──────────────────────────────────────────────────
        if state=="speaking" and _r.random()<0.12:
            self.ripples.append({"r": float(R-10), "alpha": 100.0})
        for rp in self.ripples[:]:
            r=int(rp["r"]); a=int(rp["alpha"])
            if a<=0 or r>R+160: self.ripples.remove(rp); continue
            rs=pygame.Surface((r*2+4,r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(rs, (*bright, a), (r+2,r+2), r, 2)
            self._blit_c(rs, cx, cy)
            rp["r"]+=3.2; rp["alpha"]-=3.8

        # ── Orbital data labels ───────────────────────────────────────────────
        if self._orbit_surfs:
            n = len(self._orbit_surfs)
            orbit_r = R + 92
            for i, surf in enumerate(self._orbit_surfs):
                ang = t * 0.14 + i * _m.tau / n
                ox = cx + int(_m.cos(ang) * orbit_r)
                oy = cy + int(_m.sin(ang) * orbit_r * 0.55)  # elliptical
                s  = surf.copy()
                fade = int(120 + 90 * _m.sin(t * 0.8 + i))
                s.set_alpha(max(40, min(220, fade)))
                self.screen.blit(s, (ox - s.get_width() // 2, oy - s.get_height() // 2))

        # ── Lens flare during speaking ────────────────────────────────────────
        if state == "speaking":
            fa = int(30 + 20 * _m.sin(t * 9.5))
            fl = pygame.Surface((self.W, 2), pygame.SRCALPHA)
            fl.fill((*bright, fa))
            self.screen.blit(fl, (0, cy - 1))
            fv = pygame.Surface((2, self.H), pygame.SRCALPHA)
            fv.fill((*bright, fa))
            self.screen.blit(fv, (cx - 1, 0))

        # ── Data readouts ─────────────────────────────────────────────────────
        a_fade = int(110+50*_m.sin(t*0.75))
        for lx,ly,text in [(cx+270,cy-100,f"SYS  {int(50+30*_m.sin(t*0.7))}%"),
                            (cx+270,cy+100,f"MEM  {int(60+20*_m.sin(t*0.5))}%"),
                            (cx-270,cy-100,"NET  ONLINE"),
                            (cx-270,cy+100,f"CPU  {int(40+35*abs(_m.sin(t*0.9)))}%")]:
            s=self.font_data.render(text, True, bright); s.set_alpha(a_fade)
            rx=lx-s.get_width()//2; ry=ly-s.get_height()//2
            self.screen.blit(s,(rx,ry))
            bw=s.get_width()+14; bh=s.get_height()+8
            bs=pygame.Surface((bw,bh),pygame.SRCALPHA)
            pygame.draw.rect(bs,(*bright,int(a_fade*0.40)),(0,0,bw,bh),1)
            self.screen.blit(bs,(rx-7,ry-4))

    def _draw_particles(self, state, t):
        import math as _m
        bright,_,_ = self._col(state)
        ov = self._overlay; ov.fill((0,0,0,0))
        sm = 2.8 if state=="speaking" else 1.5 if state=="listening" else 1.0
        for p in self.particles:
            p["angle"]  += p["speed"]  * sm
            p["y_phase"]+= p["y_speed"]* sm
            tr = p["base_r"]+(35*_m.sin(t*2.5+p["angle"]) if state=="speaking" else 0)
            p["r"]+=(tr-p["r"])*0.06
            x = self.cx+p["r"]*_m.cos(p["angle"])
            y = self.cy+p["r"]*_m.sin(p["angle"])*0.5+p["y_amp"]*_m.sin(p["y_phase"])
            al = p["alpha"]*(0.5+0.5*_m.sin(t*0.9+p["angle"])) if state=="idle" else p["alpha"]
            a=int(al*255); s=max(1,int(p["size"])); ix,iy=int(x),int(y)
            if p["shape"]=="diamond":
                pygame.draw.polygon(ov,(*bright,a),[(ix,iy-s),(ix+s,iy),(ix,iy+s),(ix-s,iy)])
            else:
                pygame.draw.circle(ov,(*bright,a),(ix,iy),s)
        self.screen.blit(ov,(0,0))

    def _draw_corners(self):
        c=(18,55,140); sz=44; W,H=self.W,self.H
        for x0,y0,dx,dy in [(10,10,1,1),(W-10,10,-1,1),(10,H-10,1,-1),(W-10,H-10,-1,-1)]:
            pygame.draw.lines(self.screen,c,False,
                              [(x0+dx*sz,y0),(x0,y0),(x0,y0+dy*sz)],1)

    def _draw_grid_floor(self, t):
        """Scrolling perspective grid at bottom — the Iron Man floor."""
        if self._grid_surf is None: return
        self.screen.blit(self._grid_surf, (0, self._grid_y0))
        num = 14
        for i in range(num):
            tl = ((i / num) + t * 0.06) % 1.0
            y_rel = (tl ** 1.9) * self._grid_h
            y = int(self._grid_y0 + y_rel)
            alpha = int(20 + 85 * tl)
            ls = pygame.Surface((self.W, 1), pygame.SRCALPHA)
            ls.fill((0, 110, 210, alpha))
            self.screen.blit(ls, (0, y))

    def _draw_data_streams(self, dt):
        """Matrix-style glyph columns on left + right edges."""
        import random as _r
        if not self.data_streams or self._ds_font is None: return
        for s in self.data_streams:
            s["y"] += s["speed"] * dt
            s["swap_t"] -= dt
            if s["swap_t"] <= 0:
                idx = _r.randrange(s["len"])
                s["chars"][idx] = _r.choice(self._ds_chars)
                s["swap_t"] = _r.uniform(0.05, 0.22)
            if s["y"] > self.H + 100:
                s["y"] = -s["len"] * 14 - _r.uniform(0, 300)
                s["chars"] = [_r.choice(self._ds_chars) for _ in range(s["len"])]
            head_y = s["y"]
            for i, ch in enumerate(s["chars"]):
                y = int(head_y - i * 14)
                if y < -16 or y > self.H: continue
                if i == 0:
                    surf = self._ds_char_head.get(ch)
                    a = 235
                else:
                    surf = self._ds_char_body.get(ch)
                    fade = max(0.0, 1.0 - i / s["len"])
                    a = int(18 + 180 * fade)
                if surf is None: continue
                surf.set_alpha(a)
                self.screen.blit(surf, (s["x"], y))

    def _spawn_reticule(self):
        import random as _r
        # avoid sphere center area
        while True:
            x = _r.randint(80, self.W - 80)
            y = _r.randint(80, self.H - 120)
            if abs(x - self.cx) > 260 or abs(y - self.cy) > 260:
                break
        self.reticules.append({
            "x": x, "y": y, "age": 0.0, "life": 2.4,
            "rot": _r.uniform(0, 6.283),
            "size": _r.randint(34, 58),
            "label": _r.choice(["TARGET","SCAN","TRACE","LOCK","OBJ.ID"]),
            "code":  f"{_r.randint(100,999)}-{_r.choice('ABCDEFGH')}{_r.randint(10,99)}",
        })

    def _update_reticules(self, dt):
        self._reticule_cd -= dt
        if self._reticule_cd <= 0:
            self._spawn_reticule()
            import random as _r
            self._reticule_cd = _r.uniform(2.8, 5.5)
        for r in self.reticules[:]:
            r["age"] += dt
            r["rot"] += dt * 1.2
            if r["age"] >= r["life"]:
                self.reticules.remove(r)

    def _draw_reticules(self):
        import math as _m
        for r in self.reticules:
            a_norm = r["age"] / r["life"]
            if a_norm < 0.15:
                alpha = a_norm / 0.15
            elif a_norm > 0.75:
                alpha = max(0.0, 1.0 - (a_norm - 0.75) / 0.25)
            else:
                alpha = 1.0
            A = int(alpha * 220)
            if A <= 4: continue
            cx, cy = r["x"], r["y"]
            sz = r["size"]
            # expanding grow-in
            grow = min(1.0, r["age"] * 2.5)
            sz = int(sz * (0.6 + 0.4 * grow))
            col = (0, 230, 255, A)

            # rotating outer square-ring
            pts = []
            for k in range(4):
                ang = r["rot"] + k * _m.pi / 2
                pts.append((cx + int(_m.cos(ang) * sz),
                            cy + int(_m.sin(ang) * sz)))
            ov = pygame.Surface((sz*2+12, sz*2+12), pygame.SRCALPHA)
            ox, oy = cx - sz - 6, cy - sz - 6
            for i in range(4):
                x1, y1 = pts[i][0] - ox, pts[i][1] - oy
                x2, y2 = pts[(i+1)%4][0] - ox, pts[(i+1)%4][1] - oy
                pygame.draw.line(ov, col, (x1, y1), (x2, y2), 1)
            # inner cross
            pygame.draw.line(ov, col, (sz+6, sz-int(sz*0.6)+6), (sz+6, sz+int(sz*0.6)+6), 1)
            pygame.draw.line(ov, col, (sz-int(sz*0.6)+6, sz+6), (sz+int(sz*0.6)+6, sz+6), 1)
            # center dot
            pygame.draw.circle(ov, col, (sz+6, sz+6), 2)
            self.screen.blit(ov, (ox, oy))
            # label
            lbl = self.font_data.render(f"{r['label']}  {r['code']}", True, (0, 230, 255))
            lbl.set_alpha(A)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, cy + sz + 8))

    def _spawn_power_arc(self):
        import random as _r, math as _m
        # arc from sphere surface to random edge point
        R = (self._sp_R if HAS_NUMPY else 195)
        ang = _r.uniform(0, _m.tau)
        start = (int(self.cx + _m.cos(ang) * R), int(self.cy + _m.sin(ang) * R))
        # end: random edge
        edge_choice = _r.choice(["top","bot","left","right"])
        if edge_choice == "top":
            end = (_r.randint(80, self.W-80), _r.randint(20, 180))
        elif edge_choice == "bot":
            end = (_r.randint(80, self.W-80), _r.randint(self.H-240, self.H-60))
        elif edge_choice == "left":
            end = (_r.randint(40, 220), _r.randint(120, self.H-180))
        else:
            end = (_r.randint(self.W-220, self.W-40), _r.randint(120, self.H-180))
        # jagged midpoints
        segs = 10
        pts = []
        for i in range(segs + 1):
            t = i / segs
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            if 0 < i < segs:
                jitter = 28 * (1 - abs(t - 0.5) * 2)
                x += _r.uniform(-jitter, jitter)
                y += _r.uniform(-jitter, jitter)
            pts.append((int(x), int(y)))
        self.power_arcs.append({"pts": pts, "age": 0.0, "life": 0.38})

    def _update_power_arcs(self, dt, state):
        self._arc_cd -= dt
        threshold = (1.6 if state == "speaking"
                     else 3.0 if state == "waking"
                     else 6.0)
        if self._arc_cd <= 0:
            self._spawn_power_arc()
            import random as _r
            self._arc_cd = _r.uniform(threshold * 0.6, threshold * 1.2)
        for a in self.power_arcs[:]:
            a["age"] += dt
            if a["age"] >= a["life"]:
                self.power_arcs.remove(a)

    def _draw_power_arcs(self):
        for a in self.power_arcs:
            prog = a["age"] / a["life"]
            alpha = int(255 * (1.0 - prog))
            if alpha <= 4: continue
            pts = a["pts"]
            # outer glow
            gs = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            pygame.draw.lines(gs, (0, 180, 255, alpha // 3), False, pts, 5)
            pygame.draw.lines(gs, (120, 220, 255, alpha // 2), False, pts, 3)
            pygame.draw.lines(gs, (230, 250, 255, alpha), False, pts, 1)
            self.screen.blit(gs, (0, 0))

    def _draw_diag_panels(self, t, dt):
        """Live animated bars in top-left and top-right corners."""
        import math as _m, random as _r
        self._diag_t += dt
        if self._diag_t > 0.35:
            self._diag_t = 0.0
            for b in self.diag_bars:
                b["target"] = max(0.15, min(1.0, b["target"] + _r.uniform(-0.08, 0.08)))
        for b in self.diag_bars:
            b["value"] += (b["target"] - b["value"]) * 0.10

        panel_w = 180; bar_h = 9; row_h = 22
        # Left panel — first 3 bars
        lx, ly = 18, 18
        header = self.font_data.render("▌ SYSTEM DIAGNOSTIC", True, (80, 180, 255))
        header.set_alpha(180)
        self.screen.blit(header, (lx, ly))
        for i, b in enumerate(self.diag_bars[:3]):
            by = ly + 20 + i * row_h
            lbl = self.font_data.render(b["label"], True, (100, 170, 230))
            lbl.set_alpha(180)
            self.screen.blit(lbl, (lx, by))
            pct = self.font_data.render(f"{int(b['value']*100):>3}%", True, (180, 220, 255))
            pct.set_alpha(200)
            self.screen.blit(pct, (lx + panel_w - 28, by))
            # bar
            bx, bby = lx, by + 13
            s_bg = pygame.Surface((panel_w, bar_h), pygame.SRCALPHA)
            s_bg.fill((0, 30, 70, 140))
            self.screen.blit(s_bg, (bx, bby))
            fill_w = int(panel_w * b["value"])
            s_fg = pygame.Surface((max(1, fill_w), bar_h), pygame.SRCALPHA)
            pulse = int(40 * _m.sin(t * 2.5 + i))
            s_fg.fill((int(b["col"][0]), int(b["col"][1]), int(b["col"][2]), 220))
            self.screen.blit(s_fg, (bx, bby))
            pygame.draw.rect(self.screen, (0, 80, 170), (bx, bby, panel_w, bar_h), 1)

        # Right panel — last 3 bars
        rx = self.W - 18 - panel_w
        ry = 18
        header_r = self.font_data.render("ANALYSIS ▌", True, (80, 180, 255))
        header_r.set_alpha(180)
        self.screen.blit(header_r, (rx + panel_w - header_r.get_width(), ry))
        for i, b in enumerate(self.diag_bars[3:6]):
            by = ry + 20 + i * row_h
            lbl = self.font_data.render(b["label"], True, (100, 170, 230))
            lbl.set_alpha(180)
            self.screen.blit(lbl, (rx, by))
            pct = self.font_data.render(f"{int(b['value']*100):>3}%", True, (180, 220, 255))
            pct.set_alpha(200)
            self.screen.blit(pct, (rx + panel_w - 28, by))
            bx, bby = rx, by + 13
            s_bg = pygame.Surface((panel_w, bar_h), pygame.SRCALPHA)
            s_bg.fill((0, 30, 70, 140))
            self.screen.blit(s_bg, (bx, bby))
            fill_w = int(panel_w * b["value"])
            s_fg = pygame.Surface((max(1, fill_w), bar_h), pygame.SRCALPHA)
            pulse = int(40 * _m.sin(t * 2.5 + i + 2))
            s_fg.fill((int(b["col"][0]), int(b["col"][1]), int(b["col"][2]), 220))
            self.screen.blit(s_fg, (bx, bby))
            pygame.draw.rect(self.screen, (0, 80, 170), (bx, bby, panel_w, bar_h), 1)

    def _apply_bloom(self):
        """Cheap full-scene bloom: downscale → blur → dim → additive back."""
        try:
            sw, sh = self.W // 5, self.H // 5
            small = pygame.transform.smoothscale(self.screen, (sw, sh))
            tiny  = pygame.transform.smoothscale(small, (sw // 3, sh // 3))
            blur  = pygame.transform.smoothscale(tiny, (self.W, self.H))
            blur.fill((80, 80, 80), special_flags=pygame.BLEND_MULT)
            self.screen.blit(blur, (0, 0), special_flags=pygame.BLEND_ADD)
        except Exception as e:
            pass

    def _draw_scanlines(self):
        if self._scanline_surf is not None:
            self.screen.blit(self._scanline_surf, (0, 0))

    def _draw_hud(self, state, t):
        labels={"idle":"STANDBY","waking":"ACTIVATING","listening":"LISTENING","speaking":"SPEAKING","working":"WORKING"}
        colors={"idle":(35,70,155),"waking":(100,100,255),"listening":(0,195,215),"speaking":(0,180,255),"working":(255,160,0)}
        dot="● " if state in("listening","speaking","working") and int(t*2)%2==0 else "○ "
        txt=self.font_hud.render(f"{dot}J.A.R.V.I.S.  ·  {labels.get(state,'STANDBY')}",
                                 True,colors.get(state,(35,70,155)))
        self.screen.blit(txt,(self.W//2-txt.get_width()//2,self.H-52))
        hint=self.font_data.render('ESC · exit   SAY "JARVIS" · wake   R · reminders',True,(20,45,100))
        self.screen.blit(hint,(self.W//2-hint.get_width()//2,self.H-27))

    def add_news_card(self, text, tx, ty, delay=0.0, tag="NEWS", img_url=None, fly_dx=-500, fly_dy=0):
        self.news_cards.append(NewsCard(text, tx, ty, delay=delay, tag=tag, img_url=img_url, fly_dx=fly_dx, fly_dy=fly_dy))

    def clear_news_cards(self):
        self.news_cards.clear()

    def run(self):
        global visual_state
        self.setup()
        fps_font = pygame.font.SysFont("consolas", 11)
        while True:
            dt=self.clock.tick(60)/1000.0; self.t+=dt
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); return
                if self.reminder_screen.active:
                    self.reminder_screen.handle_event(event)
                    continue
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:
                        pygame.quit(); return
                    if event.key==pygame.K_r:
                        self.reminder_screen.open()
            state=visual_state
            self.screen.fill((0,2,12))
            # --- bottom background layer ---
            self._draw_grid_floor(self.t)
            self._draw_data_streams(dt)
            # --- core scene ---
            self._draw_particles(state,self.t)
            self._draw_reactor(self.cx,self.cy,state,self.t)
            # --- overlays that bloom together ---
            self._update_reticules(dt)
            self._draw_reticules()
            self._update_power_arcs(dt, state)
            self._draw_power_arcs()
            # --- bloom post-process (before cards/HUD so text stays crisp) ---
            self._apply_bloom()
            # --- foreground UI (post-bloom = crisp) ---
            self._draw_scanlines()
            for card in self.news_cards[:]:
                card.update(dt)
                card.draw(self.screen,self.font_data,self.font_card_body)
                if not card.alive: self.news_cards.remove(card)
            self._draw_diag_panels(self.t, dt)
            self._draw_corners()
            self._draw_hud(state,self.t)
            self.reminder_screen.draw(self.screen, self.font_hud, self.font_data, self.t)
            fps=self.clock.get_fps()
            fs=fps_font.render(f"{fps:.0f} fps",True,(20,50,100))
            self.screen.blit(fs,(self.W-fs.get_width()-12,10))
            pygame.display.flip()


visual = JarvisVisual()

# ─── Voice (edge-tts → British JARVIS voice) ──────────────────────────────────
async def _tts_generate(text):
    path = tempfile.mktemp(suffix=".mp3")
    com  = edge_tts.Communicate(text, TTS_VOICE, rate="+8%", pitch="-3Hz")
    await com.save(path)
    return path

def speak(text):
    global visual_state
    text = text.replace("*", "")
    print(f"\nJARVIS: {text}")
    visual_state = "speaking"
    spoken = False

    if HAS_EDGE_TTS:
        try:
            loop = asyncio.new_event_loop()
            tmp  = loop.run_until_complete(_tts_generate(text))
            loop.close()
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.stop()
            try: os.unlink(tmp)
            except: pass
            spoken = True
        except Exception as e:
            print(f"edge-tts error: {e}")

    if not spoken:
        try:
            safe = text.replace("'", " ").replace('"', " ")
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Speech; "
                 f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                 f"$s.Rate = 2; $s.Volume = 100; $s.Speak('{safe}')"],
                timeout=60, capture_output=True)
        except Exception as e:
            print(f"Fallback TTS error: {e}")

    visual_state = "listening" if active else "idle"

# ─── Yes/No Listener ──────────────────────────────────────────────────────────
_YES_WORDS = ("yes", "yeah", "yep", "yup", "sure", "please", "go ahead",
              "ok", "okay", "affirmative", "do it", "go on", "proceed",
              "absolutely", "of course", "fine")
_NO_WORDS  = ("no", "nope", "nah", "negative", "cancel", "skip",
              "not now", "don't", "dont", "never mind", "nevermind", "pass")

def listen_yes_no(timeout=6, phrase_time_limit=4):
    """Listen for a short yes/no answer. Returns True / False / None (no answer)."""
    global visual_state
    visual_state = "listening"
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    recognizer.dynamic_energy_threshold = True
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("  (awaiting yes/no…)")
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        return None
    except Exception as e:
        print(f"Yes/no mic error: {e}"); return None
    try:
        text = recognizer.recognize_google(audio).lower()
    except Exception as e:
        print(f"  (yes/no recog error: {e})"); return None
    print(f"You (yes/no): {text}")
    tokens = set(text.replace(",", " ").replace(".", " ").split())
    no_phrases  = [w for w in _NO_WORDS  if " " in w]
    yes_phrases = [w for w in _YES_WORDS if " " in w]
    no_single   = [w for w in _NO_WORDS  if " " not in w]
    yes_single  = [w for w in _YES_WORDS if " " not in w]
    if any(p in text for p in no_phrases):  return False
    if any(w in tokens for w in no_single): return False
    if any(p in text for p in yes_phrases): return True
    if any(w in tokens for w in yes_single): return True
    return None

# ─── Week + Birthday Overlays ─────────────────────────────────────────────────
def show_week_view(day_buckets):
    """Add 7 holographic day tiles above the sphere."""
    import datetime as _dt
    cx, cy = visual.cx, visual.cy
    today = _dt.date.today()
    names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    card_w, card_h, gap = 260, 210, 10
    strip_w = 7 * card_w + 6 * gap
    # fit within screen width (leave 30px margin each side)
    if strip_w > visual.W - 60:
        card_w = max(170, (visual.W - 60 - 6 * gap) // 7)
        strip_w = 7 * card_w + 6 * gap
    first_cx = cx - strip_w // 2 + card_w // 2

    # position: high enough to clear sphere + rings; half card above, half below
    ty = cy - 340
    if ty - card_h // 2 < 20:
        ty = card_h // 2 + 30

    for i in range(7):
        d = today + _dt.timedelta(days=i)
        label = f"{names[d.weekday()]} {d.day:02d}/{d.month:02d}"
        events = day_buckets[i] if i < len(day_buckets) else []
        tx = first_cx + i * (card_w + gap)
        # cards sweep in from upper-right, staggered
        visual.news_cards.append(DayCard(
            label, events, tx, ty,
            delay=0.15 + i * 0.14,
            fly_dx=900 - i * 40, fly_dy=-700,
            w=card_w, h=card_h, lifetime=55.0))

def show_birthday_view(birthdays):
    """Show a single wide card listing upcoming birthdays."""
    cx, cy = visual.cx, visual.cy
    if not birthdays:
        lines = ["— none in the next month —"]
    else:
        lines = [f"{b['name']}  ·  {b['date'].strftime('%b %d')}  ·  in {b['days']}d"
                 if b['days'] > 0 else
                 f"{b['name']}  ·  TODAY"
                 for b in birthdays[:6]]
    visual.news_cards.append(DayCard(
        "UPCOMING BIRTHDAYS", lines, cx, cy + 310,
        delay=0.0, fly_dx=0, fly_dy=700,
        w=520, h=150, lifetime=45.0))

# ─── Tools ────────────────────────────────────────────────────────────────────
TOOLS = [
    {"name": "open_application",
     "description": "Open any installed application on the Windows computer by name.",
     "input_schema": {"type": "object",
                      "properties": {"app_name": {"type": "string"}},
                      "required": ["app_name"]}},
    {"name": "open_website",
     "description": "Open a URL in the default web browser.",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
    {"name": "search_web",
     "description": "Search Google and open results in the browser.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "set_volume",
     "description": "Set the Windows master volume (0-100).",
     "input_schema": {"type": "object",
                      "properties": {"level": {"type": "integer"}},
                      "required": ["level"]}},
    {"name": "run_command",
     "description": "Run a shell or PowerShell command on the computer.",
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"},
                                     "powershell": {"type": "boolean"}},
                      "required": ["command"]}},
    {"name": "create_file",
     "description": "Create a file with specified content.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "read_file",
     "description": "Read the contents of a file.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"}},
                      "required": ["path"]}},
    {"name": "list_directory",
     "description": "List files in a directory.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"}}}},
    {"name": "get_system_info",
     "description": "Get CPU, RAM, disk usage and running processes.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "type_text",
     "description": "Type text at the current cursor position.",
     "input_schema": {"type": "object",
                      "properties": {"text": {"type": "string"}},
                      "required": ["text"]}},
    {"name": "press_keys",
     "description": "Press a keyboard shortcut.",
     "input_schema": {"type": "object",
                      "properties": {"keys": {"type": "string"}},
                      "required": ["keys"]}},
    {"name": "take_screenshot",
     "description": "Take a screenshot and save it to the Desktop.",
     "input_schema": {"type": "object",
                      "properties": {"filename": {"type": "string"}}}},
    {"name": "play_spotify",
     "description": "Play a song, artist, album or playlist on Spotify.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "spotify_control",
     "description": "Control Spotify: pause, resume, next, previous, mute.",
     "input_schema": {"type": "object",
                      "properties": {"action": {"type": "string"}},
                      "required": ["action"]}},
    {"name": "send_email",
     "description": "Open Gmail to compose an email.",
     "input_schema": {"type": "object",
                      "properties": {"to": {"type": "string"},
                                     "subject": {"type": "string"},
                                     "body": {"type": "string"}},
                      "required": ["to", "subject", "body"]}},
    {"name": "set_calendar_url",
     "description": "Save the user's Google Calendar secret iCal URL for weekly previews. User finds it at calendar.google.com → Settings → Integrate calendar → Secret address in iCal format.",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
    {"name": "set_birthdays_url",
     "description": "Save the user's Google Contacts birthday calendar secret iCal URL (used to surface upcoming birthdays).",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
    {"name": "add_birthday",
     "description": "Save someone's birthday. Date format MM-DD, e.g. 07-25.",
     "input_schema": {"type": "object",
                      "properties": {"name": {"type": "string"},
                                     "date": {"type": "string"}},
                      "required": ["name", "date"]}},
    {"name": "remove_birthday",
     "description": "Remove a saved birthday by name.",
     "input_schema": {"type": "object",
                      "properties": {"name": {"type": "string"}},
                      "required": ["name"]}},
    {"name": "list_birthdays",
     "description": "List birthdays in the coming month.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "show_week",
     "description": "Display the holographic 7-day calendar overlay on the JARVIS visual.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "dispatch_agent",
     "description": (
         "Dispatch a specialist sub-agent pipeline for complex multi-step tasks that require "
         "fetching and synthesising information from external sources. "
         "Use this when the user asks for email summaries, inbox analysis, in-depth web research, "
         "OR study/learning materials for a test or exam topic. "
         "Available pipeline types: "
         "'email_summary' (reads Gmail inbox and summarises), "
         "'web_research' (searches the web and synthesises a factual briefing), "
         "'study' (researches an exam/test topic and emails a full study guide — "
         "ALWAYS use this when the user mentions sprawdzian, egzamin, test, kartkówka, "
         "or asks to prepare for any subject/topic exam; pass the EXACT topic as context). "
         "Pass the user's original topic/request verbatim as context — preserving the original language."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "pipeline_type": {"type": "string",
                                            "description": "One of: email_summary, web_research, study"},
                          "context": {"type": "string",
                                      "description": "The user's original request verbatim (preserve language)"},
                      },
                      "required": ["pipeline_type", "context"]}},
    {"name": "set_gmail_credentials",
     "description": (
         "Save the user's Gmail IMAP credentials so JARVIS can read emails. "
         "Requires the Gmail address and a Google App Password (NOT the main Gmail password). "
         "The user generates App Passwords at myaccount.google.com → Security → App passwords."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "email":        {"type": "string", "description": "Full Gmail address"},
                          "app_password": {"type": "string", "description": "16-character Google App Password (spaces are stripped automatically)"},
                      },
                      "required": ["email", "app_password"]}},
    {"name": "generate_mindmap",
     "description": (
         "Create and display an interactive holographic HTML mind map for any topic. "
         "Opens automatically in the browser. Use for knowledge maps, brainstorming, "
         "topic breakdowns, concept summaries, or learning plans."
     ),
     "input_schema": {
         "type": "object",
         "properties": {
             "topic": {
                 "type": "string",
                 "description": "Central topic label (shown at the center node)"
             },
             "nodes": {
                 "type": "array",
                 "description": (
                     "All nodes including the center. Each node object: "
                     "{id (str), label (str, use \\n for line breaks), "
                     "parent_id (null for the center node, else parent node id), "
                     "category (str matching a category name), info (str tooltip text)}"
                 ),
                 "items": {"type": "object"}
             },
             "categories": {
                 "type": "array",
                 "description": "Category definitions. Each: {name (str), color (hex string e.g. '#00ffc8')}",
                 "items": {"type": "object"}
             }
         },
         "required": ["topic", "nodes", "categories"]
     }},
    {"name": "generate_chart",
     "description": "Create an interactive holographic HTML chart (bar, line, pie, or donut) and open it in the browser. Use to visualise data, comparisons, trends, or distributions.",
     "input_schema": {"type":"object","properties":{
         "title":      {"type":"string","description":"Chart title"},
         "chart_type": {"type":"string","description":"bar | line | pie | donut"},
         "labels":     {"type":"array","items":{"type":"string"},"description":"Category/X-axis labels"},
         "values":     {"type":"array","items":{"type":"number"},"description":"Numeric values matching labels"},
         "colors":     {"type":"array","items":{"type":"string"},"description":"Optional hex colors (e.g. ['#00ffc8','#00b4ff'])"},
         "x_label":    {"type":"string","description":"X-axis label (optional)"},
         "y_label":    {"type":"string","description":"Y-axis label (optional)"}
     },"required":["title","chart_type","labels","values"]}},
    {"name": "generate_flashcards",
     "description": "Create an interactive HTML flashcard deck for studying any topic. Opens in browser with flip animation, shuffle, and progress tracking.",
     "input_schema": {"type":"object","properties":{
         "topic": {"type":"string","description":"Deck topic/title"},
         "cards": {"type":"array","description":"Array of {front: 'question', back: 'answer'} objects","items":{"type":"object"}}
     },"required":["topic","cards"]}},
    {"name": "manage_reminder",
     "description": "Add, list, or delete reminders. Each reminder has a date and a subject. Jarvis reads due reminders aloud every morning.",
     "input_schema": {"type": "object",
                      "properties": {
                          "action":  {"type": "string",  "description": "add | list | delete"},
                          "date":    {"type": "string",  "description": "Date for the reminder, e.g. 25/04/2026 or 2026-04-25 (for add)"},
                          "subject": {"type": "string",  "description": "What to be reminded about (for add)"},
                          "note":    {"type": "string",  "description": "Optional extra detail (for add)"},
                          "index":   {"type": "integer", "description": "1-based reminder index to delete (for delete)"}
                      },
                      "required": ["action"]}},
    {"name": "manage_todo",
     "description": "Manage a persistent to-do list. Actions: add, complete, delete, list, clear_done.",
     "input_schema": {"type":"object","properties":{
         "action":  {"type":"string","description":"add | complete | delete | list | clear_done"},
         "text":    {"type":"string","description":"Task text (for add/complete/delete)"},
         "item_id": {"type":"integer","description":"Task ID number (for complete/delete by ID)"}
     },"required":["action"]}},
    {"name": "take_note",
     "description": "Save a voice note or idea to persistent storage. Optionally list/search saved notes.",
     "input_schema": {"type":"object","properties":{
         "action":  {"type":"string","description":"save | list"},
         "title":   {"type":"string","description":"Note title (for save)"},
         "content": {"type":"string","description":"Note content (for save)"},
         "query":   {"type":"string","description":"Search query (for list — leave empty to list recent notes)"}
     },"required":["action"]}},
    {"name": "remember_fact",
     "description": "Store or retrieve a named fact. Use to remember arbitrary information the user wants saved (e.g. 'my gym password is X', 'sister birthday is March 5').",
     "input_schema": {"type":"object","properties":{
         "action": {"type":"string","description":"store | recall"},
         "key":    {"type":"string","description":"Fact name/key (for both actions)"},
         "value":  {"type":"string","description":"Fact value (for store only)"}
     },"required":["action","key"]}},
    {"name": "get_stock_price",
     "description": "Get the current price and daily change for a stock or crypto symbol (e.g. AAPL, TSLA, BTC-USD, ETH-USD).",
     "input_schema": {"type":"object","properties":{
         "symbol": {"type":"string","description":"Ticker symbol (e.g. AAPL, BTC-USD)"}
     },"required":["symbol"]}},
    {"name": "get_wikipedia",
     "description": "Fetch a short Wikipedia summary for any topic. Great for quick factual lookups.",
     "input_schema": {"type":"object","properties":{
         "query":     {"type":"string","description":"Topic to look up"},
         "sentences": {"type":"integer","description":"Number of sentences to return (default 4)"}
     },"required":["query"]}},
    {"name": "kill_process",
     "description": "Kill a running process by name (e.g. 'chrome', 'notepad', 'spotify').",
     "input_schema": {"type":"object","properties":{
         "name": {"type":"string","description":"Process name or partial name to kill"}
     },"required":["name"]}},
    {"name": "get_clipboard",
     "description": "Read the current contents of the Windows clipboard.",
     "input_schema": {"type":"object","properties":{}}},
    {"name": "set_clipboard",
     "description": "Write text to the Windows clipboard.",
     "input_schema": {"type":"object","properties":{
         "text": {"type":"string","description":"Text to copy to clipboard"}
     },"required":["text"]}},
    {"name": "download_file",
     "description": "Download a file from a URL to the Downloads folder.",
     "input_schema": {"type":"object","properties":{
         "url":      {"type":"string","description":"URL to download"},
         "filename": {"type":"string","description":"Optional filename (auto-detected from URL if omitted)"}
     },"required":["url"]}},
    {"name": "open_file",
     "description": "Open any file with its default application (documents, images, videos, PDFs, etc.).",
     "input_schema": {"type":"object","properties":{
         "path": {"type":"string","description":"Absolute path to the file to open"}
     },"required":["path"]}},
    {"name": "file_operation",
     "description": "Move, copy, rename, or delete files and folders.",
     "input_schema": {"type":"object","properties":{
         "operation": {"type":"string","description":"move | copy | rename | delete"},
         "src":       {"type":"string","description":"Source path"},
         "dst":       {"type":"string","description":"Destination path (not needed for delete)"}
     },"required":["operation","src"]}},
    {"name": "get_network_info",
     "description": "Get the local IP address, Wi-Fi SSID, and ping latency.",
     "input_schema": {"type":"object","properties":{}}},
    {"name": "set_timer",
     "description": "Set a countdown timer. Jarvis will speak when it fires and show a Windows popup.",
     "input_schema": {"type":"object","properties":{
         "seconds": {"type":"number","description":"Duration in seconds"},
         "label":   {"type":"string","description":"Timer label (e.g. 'Pasta', 'Pomodoro')"}
     },"required":["seconds"]}},
]


def execute_tool(name, inp):
    try:
        if name == "open_application":
            app = inp["app_name"]
            subprocess.Popen(f'start "" "{app}"', shell=True); time.sleep(0.3)
            try: subprocess.Popen(app, shell=True)
            except: pass
            return f"Opened {app}"
        elif name == "open_website":
            webbrowser.open(inp["url"]); return f"Opened {inp['url']}"
        elif name == "search_web":
            q = inp["query"].replace(" ", "+")
            webbrowser.open(f"https://www.google.com/search?q={q}")
            return f"Searched: {inp['query']}"
        elif name == "set_volume":
            level = max(0, min(100, inp["level"])) / 100.0
            devices = AudioUtilities.GetSpeakers()
            iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = iface.QueryInterface(IAudioEndpointVolume)
            vol.SetMasterVolumeLevelScalar(level, None)
            return f"Volume set to {int(level*100)}%"
        elif name == "run_command":
            cmd = inp["command"]
            result = subprocess.run(
                ["powershell", "-Command", cmd] if inp.get("powershell") else cmd,
                shell=not inp.get("powershell"), capture_output=True, text=True, timeout=30)
            out = (result.stdout + result.stderr).strip()
            return out[:2000] if out else "Done"
        elif name == "create_file":
            path = inp["path"]
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f: f.write(inp["content"])
            return f"Created {path}"
        elif name == "read_file":
            with open(inp["path"], "r", encoding="utf-8") as f: return f.read()[:3000]
        elif name == "list_directory":
            path = inp.get("path") or os.path.join(os.path.expanduser("~"), "Desktop")
            return "\n".join(os.listdir(path))
        elif name == "get_system_info":
            cpu = psutil.cpu_percent(interval=1); ram = psutil.virtual_memory(); disk = psutil.disk_usage("/")
            procs = sorted([p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]])[:15]
            return json.dumps({"cpu_percent": cpu, "ram_used_gb": round(ram.used/1e9,2),
                               "ram_total_gb": round(ram.total/1e9,2), "ram_percent": ram.percent,
                               "disk_used_gb": round(disk.used/1e9,2), "disk_total_gb": round(disk.total/1e9,2),
                               "processes": procs}, indent=2)
        elif name == "type_text":
            pyautogui.write(inp["text"], interval=0.02); return "Typed text"
        elif name == "press_keys":
            pyautogui.hotkey(*inp["keys"].lower().split("+")); return f"Pressed {inp['keys']}"
        elif name == "take_screenshot":
            fname = inp.get("filename") or f"screenshot_{int(time.time())}.png"
            path  = os.path.join(os.path.expanduser("~"), "Desktop", fname)
            pyautogui.screenshot().save(path); return f"Screenshot saved to {path}"
        elif name == "play_spotify":
            query = inp["query"]
            if sp:
                try:
                    results = sp.search(q=query, type="track", limit=1)
                    tracks  = results["tracks"]["items"]
                    if tracks:
                        uri = tracks[0]["uri"]; title = tracks[0]["name"]
                        artist = tracks[0]["artists"][0]["name"]
                        print(f"  [spotify] {title} by {artist}  ({uri})")
                        subprocess.run(["powershell", "-Command",
                                        "Stop-Process -Name Spotify -Force -ErrorAction SilentlyContinue"],
                                       capture_output=True, timeout=5)
                        time.sleep(3); os.startfile(uri); time.sleep(2)
                        return f"Now playing {title} by {artist} on Spotify"
                    return "No track found"
                except Exception as e: return f"Spotify error: {e}"
            return "Spotify API not configured."
        elif name == "spotify_control":
            action = inp["action"].lower()
            key_map = {"pause":"playpause","resume":"playpause","play":"playpause",
                       "next":"nexttrack","previous":"prevtrack","mute":"volumemute"}
            key = key_map.get(action)
            if key: pyautogui.press(key)
            return f"Spotify: {action}"
        elif name == "send_email":
            to = urllib.parse.quote(inp["to"]); sub = urllib.parse.quote(inp["subject"])
            body = urllib.parse.quote(inp["body"])
            webbrowser.open(f"https://mail.google.com/mail/?view=cm&to={to}&su={sub}&body={body}")
            return f"Opened Gmail compose to {inp['to']}"
        elif name == "set_calendar_url":
            mem = load_memory(); mem["gcal_ics_url"] = inp["url"].strip(); save_memory(mem)
            return "Calendar URL saved"
        elif name == "set_birthdays_url":
            mem = load_memory(); mem["gcal_birthdays_ics_url"] = inp["url"].strip(); save_memory(mem)
            return "Birthday calendar URL saved"
        elif name == "add_birthday":
            mem = load_memory()
            bds = [b for b in mem.get("birthdays", [])
                   if b.get("name", "").lower() != inp["name"].lower()]
            # validate MM-DD
            try:
                m, d = inp["date"].split("-"); int(m); int(d)
            except Exception:
                return "Date must be MM-DD format, e.g. 07-25"
            bds.append({"name": inp["name"], "date": inp["date"]})
            mem["birthdays"] = bds; save_memory(mem)
            return f"Saved: {inp['name']} on {inp['date']}"
        elif name == "remove_birthday":
            mem = load_memory()
            before = len(mem.get("birthdays", []))
            mem["birthdays"] = [b for b in mem.get("birthdays", [])
                                if b.get("name", "").lower() != inp["name"].lower()]
            save_memory(mem)
            removed = before - len(mem["birthdays"])
            return f"Removed {removed} entry for {inp['name']}" if removed else f"No birthday found for {inp['name']}"
        elif name == "list_birthdays":
            bds = upcoming_birthdays(30)
            if not bds: return "No birthdays in the next month"
            return ", ".join(f"{b['name']} in {b['days']}d ({b['date']})" for b in bds)
        elif name == "show_week":
            cal = fetch_calendar_events(days=7)
            buckets = group_events_by_day(cal, 7) if cal else [[] for _ in range(7)]
            show_week_view(buckets)
            return "Google Calendar week overlay displayed"
        elif name == "dispatch_agent":
            return run_agent_pipeline(inp.get("pipeline_type", ""), inp.get("context", ""))
        elif name == "set_gmail_credentials":
            import tkinter as _tk
            import tkinter.simpledialog as _sd
            root = _tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            email = _sd.askstring("JARVIS — Gmail Setup",
                                  "Enter your Gmail address:", parent=root)
            if not email:
                root.destroy(); return "Setup cancelled."
            pw = _sd.askstring("JARVIS — Gmail Setup",
                               "Enter your Google App Password\n(16 chars, from myaccount.google.com → Security → App passwords):",
                               parent=root, show="*")
            root.destroy()
            if not pw:
                return "Setup cancelled."
            mem = load_memory()
            mem["gmail_imap_user"] = email.strip()
            mem["gmail_imap_pass"] = pw.replace(" ", "").strip()
            save_memory(mem)
            return f"Gmail credentials saved for {email.strip()}."
        elif name == "generate_mindmap":
            return generate_mindmap_file(inp["topic"], inp["nodes"], inp.get("categories", []))
        elif name == "generate_chart":
            return generate_chart_file(inp["title"], inp["chart_type"], inp["labels"], inp["values"],
                                       inp.get("colors"), inp.get("x_label",""), inp.get("y_label",""))
        elif name == "generate_flashcards":
            return generate_flashcard_file(inp["topic"], inp["cards"])
        elif name == "manage_reminder":
            import datetime as _rdt
            action = inp.get("action", "list")
            mem = load_memory()
            rems = mem.setdefault("reminders", [])
            if action == "add":
                raw_date = inp.get("date", "").strip()
                subject  = inp.get("subject", "").strip()
                note     = inp.get("note", "").strip()
                date_iso = None
                for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
                    try:
                        date_iso = _rdt.datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d"); break
                    except ValueError: pass
                if not date_iso: return f"I couldn't parse the date '{raw_date}'. Please use DD/MM/YYYY format."
                if not subject: return "Please provide a subject for the reminder."
                rems.append({"date": date_iso, "subject": subject, "note": note})
                rems.sort(key=lambda r: r.get("date", ""))
                mem["reminders"] = rems
                save_memory(mem)
                visual.reminder_screen._reload()
                d = _rdt.date.fromisoformat(date_iso)
                return f"Reminder set for {d.strftime('%d %B %Y')}: {subject}"
            elif action == "delete":
                idx = inp.get("index", 0) - 1
                if 0 <= idx < len(rems):
                    removed = rems.pop(idx)
                    mem["reminders"] = rems; save_memory(mem)
                    visual.reminder_screen._reload()
                    return f"Removed reminder: {removed.get('subject', '')}"
                return "Invalid reminder index."
            else:  # list
                if not rems: return "No reminders saved."
                today = _rdt.date.today().strftime("%Y-%m-%d")
                lines = []
                for i, r in enumerate(rems, 1):
                    tag = " ← TODAY" if r.get("date") == today else (" ← PAST" if r.get("date","") < today else "")
                    lines.append(f"{i}. {r.get('date','')}  {r.get('subject','')}{tag}")
                return "\n".join(lines)
        elif name == "manage_todo":
            return manage_todo(inp["action"], inp.get("text",""), inp.get("item_id"))
        elif name == "take_note":
            if inp.get("action","save") == "list":
                return list_notes(inp.get("query",""))
            return take_note(inp.get("title","Note"), inp.get("content",""))
        elif name == "remember_fact":
            if inp["action"] == "store":
                return remember_fact(inp["key"], inp.get("value",""))
            return recall_facts(inp.get("key",""))
        elif name == "get_stock_price":
            return get_stock_price(inp["symbol"])
        elif name == "get_wikipedia":
            return get_wikipedia(inp["query"], inp.get("sentences", 4))
        elif name == "kill_process":
            return kill_process_by_name(inp["name"])
        elif name == "get_clipboard":
            return clipboard_get()
        elif name == "set_clipboard":
            return clipboard_set(inp["text"])
        elif name == "download_file":
            return download_url_to_file(inp["url"], inp.get("filename",""))
        elif name == "open_file":
            return open_file_default(inp["path"])
        elif name == "file_operation":
            return file_operation(inp["operation"], inp["src"], inp.get("dst",""))
        elif name == "get_network_info":
            return get_network_info()
        elif name == "set_timer":
            return set_timer(inp["seconds"], inp.get("label","Timer"))
    except Exception as e:
        return f"Error in {name}: {e}"

# ─── Sub-Agent Infrastructure ────────────────────────────────────────────────

class AgentResult:
    def __init__(self, success, text, data=None, error=None):
        self.success = success
        self.text    = text
        self.data    = data or {}
        self.error   = error or ""

    def __repr__(self):
        return f"AgentResult(success={self.success}, text={self.text[:80]!r})"


class SubAgent:
    """
    An isolated Claude conversation with its own system prompt, tool set, and history.
    Never shares state with Jarvis's main conversation_history.
    """
    def __init__(self, name, system, tools, tool_fn,
                 model="claude-sonnet-4-6", max_tokens=2048, max_rounds=6):
        self.name       = name
        self.system     = system
        self.tools      = tools
        self.tool_fn    = tool_fn
        self.model      = model
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds

    def run(self, task):
        messages = [{"role": "user", "content": task}]
        rounds   = 0
        sys_blocks = [{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}]
        try:
            while rounds < self.max_rounds:
                rounds += 1
                kwargs = dict(
                    model      = self.model,
                    max_tokens = self.max_tokens,
                    system     = sys_blocks,
                    messages   = messages,
                    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
                )
                if self.tools:
                    kwargs["tools"] = self.tools
                response = _agent_client.messages.create(**kwargs)
                text_parts = [b.text for b in response.content
                              if hasattr(b, "text") and b.type == "text"]
                tool_uses  = [b for b in response.content if b.type == "tool_use"]
                messages.append({"role": "assistant", "content": response.content})
                if not tool_uses or response.stop_reason == "end_turn":
                    return AgentResult(success=True, text=" ".join(text_parts).strip())
                tool_results = []
                for tu in tool_uses:
                    print(f"  [{self.name}] tool: {tu.name}({tu.input})")
                    result = self.tool_fn(tu.name, tu.input)
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": tu.id, "content": str(result),
                    })
                messages.append({"role": "user", "content": tool_results})
            return AgentResult(success=False, text="",
                               error=f"{self.name} exceeded max_rounds={self.max_rounds}")
        except Exception as exc:
            return AgentResult(success=False, text="", error=f"{self.name} exception: {exc}")


# Separate client for sub-agents so it is always available even before the main client is created
_agent_client = anthropic.Anthropic(api_key=API_KEY)

# ─── Gmail IMAP Reader ────────────────────────────────────────────────────────

def _imap_read_emails(n=10, folder="INBOX"):
    import imaplib, email as _email
    from email.header import decode_header as _dh
    mem  = load_memory()
    user = (mem.get("gmail_imap_user") or "").strip()
    pw   = (mem.get("gmail_imap_pass")  or "").strip()
    if not user or not pw:
        return [{"error": "Gmail credentials not set. Ask me to set your Gmail credentials first."}]
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(user, pw)
        mail.select(folder, readonly=True)
        _, msg_ids = mail.search(None, "ALL")
        ids = msg_ids[0].split()[-n:]
        results = []
        for uid in reversed(ids):
            _, data = mail.fetch(uid, "(RFC822)")
            raw = data[0][1]
            msg = _email.message_from_bytes(raw)
            subject_parts = _dh(msg.get("Subject") or "")
            subject = "".join(
                part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                for part, enc in subject_parts
            )
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        try: body = part.get_payload(decode=True).decode(charset, errors="replace")
                        except Exception: body = str(part.get_payload())
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                try: body = msg.get_payload(decode=True).decode(charset, errors="replace")
                except Exception: body = str(msg.get_payload())
            results.append({
                "uid": uid.decode(), "subject": subject.strip(),
                "sender": msg.get("From", ""), "date": msg.get("Date", ""),
                "snippet": body[:300].replace("\n", " ").strip(),
                "body": body[:3000],
            })
        mail.logout()
        return results
    except imaplib.IMAP4.error as e:
        return [{"error": f"IMAP auth failed: {e}. Check your App Password."}]
    except Exception as e:
        return [{"error": f"IMAP error: {e}"}]

# ─── Web Helpers ──────────────────────────────────────────────────────────────

def _ddg_search(query, max_results=5):
    """DuckDuckGo Instant Answer API — no key required."""
    if not HAS_REQUESTS:
        return {"error": "requests library not installed"}
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_redirect=1&no_html=1"
        r = _requests.get(url, timeout=8, headers={"User-Agent": "JARVIS/1.0"})
        data = r.json()
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("Heading", query),
                            "snippet": data["AbstractText"],
                            "url": data.get("AbstractURL", "")})
        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("Text"):
                results.append({"title": item.get("Text", "")[:80],
                                 "snippet": item.get("Text", ""),
                                 "url": item.get("FirstURL", "")})
        return results or [{"snippet": "No instant results. Try a more specific query."}]
    except Exception as e:
        return [{"error": str(e)}]

def _web_fetch(url, max_chars=4000):
    """Fetch a URL and return stripped plain text."""
    if not HAS_REQUESTS:
        return "requests library not installed"
    try:
        r = _requests.get(url, timeout=10, headers={"User-Agent": "JARVIS/1.0"})
        text = r.text
        # Very lightweight HTML stripping — remove tags
        import re as _re
        text = _re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=_re.S | _re.I)
        text = _re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=_re.S | _re.I)
        text = _re.sub(r"<[^>]+>", " ", text)
        text = _re.sub(r"[ \t]{2,}", " ", text)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return text[:max_chars]
    except Exception as e:
        return f"Fetch error: {e}"

# ─── Agent Factories ──────────────────────────────────────────────────────────

_EMAIL_AGENT_SYSTEM = (
    "You are the EmailAgent, a specialist sub-system of JARVIS. "
    "Your only job is to read and analyse emails from the user's Gmail inbox using the read_emails tool. "
    "Produce a clear, concise spoken summary — one line per notable email: sender, subject, key point. "
    "Flag anything urgent or requiring action. Be factual; do not invent content. "
    "No greetings, no preamble, no sign-off. Output only the summary text."
)

_EMAIL_AGENT_TOOLS = [{"name": "read_emails",
                        "description": "Fetch the last N emails from the Gmail inbox via IMAP.",
                        "input_schema": {"type": "object",
                                         "properties": {
                                             "count":  {"type": "integer", "description": "Emails to fetch (default 15, max 25)"},
                                             "folder": {"type": "string",  "description": "Mailbox folder, default INBOX"},
                                         }}}]

def _email_tool_fn(name, inp):
    if name == "read_emails":
        n      = min(int(inp.get("count", 15)), 25)
        folder = inp.get("folder", "INBOX")
        return json.dumps(_imap_read_emails(n, folder), ensure_ascii=False)
    return f"Unknown tool: {name}"

def make_email_agent():
    return SubAgent("EmailAgent", _EMAIL_AGENT_SYSTEM, _EMAIL_AGENT_TOOLS,
                    _email_tool_fn, model="claude-haiku-4-5-20251001", max_tokens=768, max_rounds=3)


_WEB_RESEARCH_SYSTEM = (
    "You are the WebResearchAgent, a specialist sub-system of JARVIS. "
    "Your job is to answer the user's research question by searching the web and synthesising the findings. "
    "Use ddg_search to find relevant results, then use web_fetch on the most promising URL to get detail. "
    "Return a concise, factual briefing — spoken aloud by a TTS engine so keep it under 100 words. "
    "Cite the source briefly at the end (just the domain). No preamble, no sign-off."
)

_WEB_RESEARCH_TOOLS = [
    {"name": "ddg_search",
     "description": "Search the web via DuckDuckGo and return snippets.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "web_fetch",
     "description": "Fetch the plain-text content of a URL.",
     "input_schema": {"type": "object",
                      "properties": {"url": {"type": "string"}},
                      "required": ["url"]}},
]

def _web_research_tool_fn(name, inp):
    if name == "ddg_search":
        return json.dumps(_ddg_search(inp.get("query", ""), max_results=5), ensure_ascii=False)
    if name == "web_fetch":
        return _web_fetch(inp.get("url", ""))
    return f"Unknown tool: {name}"

def make_web_research_agent():
    return SubAgent("WebResearchAgent", _WEB_RESEARCH_SYSTEM, _WEB_RESEARCH_TOOLS,
                    _web_research_tool_fn, model="claude-haiku-4-5-20251001", max_tokens=768, max_rounds=3)


_REVIEWER_SYSTEM = (
    "You are the ReviewerAgent, a quality-control sub-system of JARVIS. "
    "You receive text produced by another agent and must review it critically. "
    "Check for: factual errors, missing key information, unclear phrasing, anything that would sound "
    "awkward when spoken aloud by a TTS engine. "
    "If the text is good, respond with exactly: APPROVED: <the text unchanged>. "
    "If you found issues, respond with exactly: REVISED: <your corrected version>. "
    "Output only that — no commentary, no explanation."
)

def make_reviewer_agent():
    return SubAgent("ReviewerAgent", _REVIEWER_SYSTEM, [], lambda n, i: "",
                    model="claude-haiku-4-5-20251001", max_rounds=2)

# ─── Orchestrator Pipelines ───────────────────────────────────────────────────

def _strip_review_prefix(text):
    for prefix in ("APPROVED:", "REVISED:"):
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text

def run_email_summary_pipeline(timeframe="recent"):
    speak("Accessing your inbox now, sir.")
    agent  = make_email_agent()
    task   = (f"Fetch the last 8 emails and produce a spoken summary. "
              f"The user asked about: '{timeframe}'. "
              f"Group by sender or topic if there's a cluster. "
              f"Highlight anything requiring action. Keep it under 80 words.")
    result = agent.run(task)
    if not result.success or not result.text:
        return f"I'm afraid the email retrieval hit a snag, sir. {result.error}"
    speak("Reviewing the summary now.")
    reviewer = make_reviewer_agent()
    reviewed = reviewer.run(f"Review this email summary for spoken clarity:\n\n{result.text}")
    if reviewed.success and reviewed.text:
        return _strip_review_prefix(reviewed.text)
    return result.text

def run_web_research_pipeline(query=""):
    speak("Initiating research, sir.")
    agent  = make_web_research_agent()
    task   = (f"Research this question and provide a concise spoken briefing: {query}. "
              f"Keep it under 100 words. Cite the source domain at the end.")
    result = agent.run(task)
    if not result.success or not result.text:
        return f"Research hit a snag, sir. {result.error}"
    speak("Reviewing findings.")
    reviewer = make_reviewer_agent()
    reviewed = reviewer.run(f"Review this research briefing for spoken clarity:\n\n{result.text}")
    if reviewed.success and reviewed.text:
        return _strip_review_prefix(reviewed.text)
    return result.text

def _smtp_send_email(subject, html_body):
    """Send an HTML email to the user's own Gmail address via SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    mem  = load_memory()
    user = (mem.get("gmail_imap_user") or "").strip()
    pw   = (mem.get("gmail_imap_pass")  or "").strip()
    if not user or not pw:
        return False, "Gmail credentials not set. Ask Jarvis to set your Gmail credentials first."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = user
        msg["To"]      = user
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.ehlo(); s.starttls(); s.ehlo()
            s.login(user, pw)
            s.sendmail(user, user, msg.as_string())
        return True, f"Sent to {user}"
    except Exception as e:
        return False, str(e)


_STUDY_AGENT_SYSTEM = (
    "You are StudyAgent, a specialist sub-system of JARVIS that creates personalised study materials. "
    "CRITICAL: detect the language of the topic provided by the user and respond ENTIRELY in that language — "
    "including section headings, explanations, and questions. "
    "If the topic is in Polish, all output must be in Polish. If English, in English. Match the language exactly. "
    "Your job: use the search and fetch tools to research the topic thoroughly, then produce a structured HTML study guide. "
    "The HTML must use inline styles only (no <style> block), dark-on-white, clean and readable. "
    "Structure: "
    "1. H2 title with the topic name. "
    "2. 'Kluczowe pojęcia' / 'Key Concepts' section — bullet list of 6-10 definitions. "
    "3. 'Streszczenie' / 'Summary' section — 3-4 paragraphs covering the main ideas. "
    "4. 'Ważne daty / fakty' / 'Key Dates & Facts' section — timeline or bullet list. "
    "5. 'Pytania ćwiczebne' / 'Practice Questions' section — 5 questions with answers hidden in a <details> tag. "
    "6. 'Źródła' / 'Sources' section — list the URLs you used. "
    "Return ONLY the HTML fragment (from <h2> onwards, no <html>/<body> wrapper). "
    "Be thorough — this is for a real exam. Do not hallucinate facts."
)

_STUDY_AGENT_TOOLS = [
    {"name": "search",
     "description": "Search DuckDuckGo for information on a topic.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "fetch",
     "description": "Fetch and read a web page.",
     "input_schema": {"type": "object",
                      "properties": {"url":       {"type": "string"},
                                     "max_chars": {"type": "integer"}},
                      "required": ["url"]}},
]

def _study_tool_fn(name, inp):
    if name == "search":
        return json.dumps(_ddg_search(inp["query"], max_results=6), ensure_ascii=False)
    if name == "fetch":
        return _web_fetch(inp["url"], inp.get("max_chars", 5000))
    return f"Unknown tool: {name}"

def make_study_agent():
    return SubAgent("StudyAgent", _STUDY_AGENT_SYSTEM, _STUDY_AGENT_TOOLS,
                    _study_tool_fn, model="claude-sonnet-4-6", max_tokens=4096, max_rounds=6)

_STUDY_EMAIL_HTML = """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Georgia,serif;background:#ffffff;color:#1a1a2e;max-width:720px;margin:0 auto;padding:32px 24px;line-height:1.7">
<div style="border-top:4px solid #0077b6;padding-top:20px;margin-bottom:28px">
  <p style="font-size:11px;letter-spacing:2px;color:#0077b6;text-transform:uppercase;margin:0">J.A.R.V.I.S. · Study Materials</p>
  <p style="font-size:11px;color:#888;margin:4px 0 0">__DATE__</p>
</div>
__CONTENT__
<hr style="border:none;border-top:1px solid #e0e0e0;margin:40px 0 20px">
<p style="font-size:11px;color:#aaa;text-align:center">Generated by J.A.R.V.I.S. · Study Intelligence System</p>
</body></html>
"""

def run_study_pipeline(topic):
    import datetime as _dt
    speak("Understood, sir. Researching the topic now.")
    agent  = make_study_agent()
    result = agent.run(
        f"Topic: {topic}\n\n"
        f"Research this topic thoroughly using the search and fetch tools, "
        f"then produce a complete HTML study guide as described in your instructions. "
        f"Remember: respond in the same language as the topic."
    )
    if not result.success or not result.text:
        return f"Research hit a snag, sir. {result.error}"

    content = result.text.strip()
    # strip any markdown code fences the model might wrap it in
    import re as _re
    content = _re.sub(r"^```html?\s*", "", content, flags=_re.I)
    content = _re.sub(r"\s*```$", "", content)

    date_str = _dt.date.today().strftime("%d %B %Y")
    html = _STUDY_EMAIL_HTML.replace("__DATE__", date_str).replace("__CONTENT__", content)

    subject = f"JARVIS · Materiały: {topic}" if any(
        c in topic.lower() for c in ["ą","ę","ó","ś","ź","ż","ć","ń","ł","sprawdzian","egzamin","test","praca"]
    ) else f"JARVIS · Study Guide: {topic}"

    speak("Research complete. Sending materials to your inbox now, sir.")
    ok, msg = _smtp_send_email(subject, html)
    if ok:
        return f"Study materials for '{topic}' sent to your inbox."
    return f"Research done but email failed: {msg}. Check Gmail credentials."


def run_agent_pipeline(pipeline_type, context):
    if pipeline_type == "email_summary":
        return run_email_summary_pipeline(timeframe=context)
    if pipeline_type == "web_research":
        return run_web_research_pipeline(query=context)
    if pipeline_type == "study":
        return run_study_pipeline(topic=context)
    return f"I don't have an agent pipeline for '{pipeline_type}' yet, sir."

# ─── Claude ───────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=API_KEY)

SYSTEM = (
    "You are JARVIS (Just A Rather Very Intelligent System), Tony Stark's personal AI — now serving a new master. "
    "You are highly capable, precise, and quietly confident. You have a dry British wit and occasionally slip in "
    "a deadpan remark or understated quip — never slapstick, never over the top. Think subtle amusement, not comedy. "
    "Keep spoken responses short and conversational — they will be read aloud. One or two sentences max unless detail is needed. "
    "When taking actions, confirm naturally in one short phrase. "
    "You have full access to the user's computer and can open apps, browse the web, manage files, "
    "run commands, control system settings, play music on Spotify, and write/send emails via Gmail. "
    "The user has Spotify Premium. When play_spotify returns 'Now playing ...', confirm naturally. "
    "Occasionally reference the fact that you run on a Windows machine with mild, dignified disappointment. "
    "A second system block below contains the user's recent habits and session context — use it to make "
    "familiar, personalised suggestions (e.g. referencing their usual music, routines, or recent topics) "
    "rather than behaving like you've just met them. "
    "For complex tasks that require fetching external data — reading emails, in-depth web research, "
    "or preparing study materials — use the dispatch_agent tool. "
    "Always say a brief acknowledgement before dispatching. "
    "STUDY MATERIALS: whenever the user mentions a test, exam, sprawdzian, egzamin, kartkówka, "
    "or asks to prepare for any subject, immediately dispatch pipeline_type='study' with the exact topic. "
    "The study agent will research the topic and email a full study guide. "
    "Always preserve the original language of the topic — if Polish, keep it Polish. "
    "VISUALISATIONS — use these proactively when they add value: "
    "`generate_mindmap` for knowledge maps and topic breakdowns; "
    "`generate_chart` for any data comparison or trend (bar/line/pie/donut); "
    "`generate_flashcards` for studying or learning any subject. "
    "PRODUCTIVITY — `manage_todo` for task lists; `take_note` to capture ideas; "
    "`remember_fact` to store anything the user wants remembered across sessions; `set_timer` for countdowns. "
    "INFORMATION — `get_stock_price` for market data; `get_wikipedia` for quick factual lookups. "
    "SYSTEM — `kill_process`, `get_clipboard`, `set_clipboard`, `download_file`, `open_file`, "
    "`file_operation` (move/copy/rename/delete), `get_network_info`. "
    "You are a full-capability super-assistant. When a user asks something that a tool can answer better than words, use the tool."
)

def ask_claude(user_message):
    global conversation_history, visual_state
    visual_state = "working"
    conversation_history.append({"role": "user", "content": user_message})
    mem_ctx = build_memory_context(load_memory())
    system_blocks = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    if mem_ctx:
        system_blocks.append({"type": "text", "text": mem_ctx})
    while True:
        visual_state = "working"
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_blocks,
            tools=TOOLS,
            messages=conversation_history,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        text_parts = [b.text for b in response.content if b.type == "text"]
        tool_uses  = [b for b in response.content if b.type == "tool_use"]
        conversation_history.append({"role": "assistant", "content": response.content})
        if text_parts: speak(" ".join(text_parts))
        if not tool_uses: break
        tool_results = []
        visual_state = "working"
        for tu in tool_uses:
            print(f"  [tool] {tu.name}({tu.input})")
            result = execute_tool(tu.name, tu.input)
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": str(result)})
        conversation_history.append({"role": "user", "content": tool_results})
        if response.stop_reason == "end_turn": break
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

# ─── Wake Word Detection ──────────────────────────────────────────────────────
WAKE_WORD = "jarvis"

def rms(data):
    count = len(data) // 2
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s*s for s in shorts) / count) if count else 0

def wake_word_listener():
    print(f'Listening for wake word: "{WAKE_WORD}"...')
    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 0.6
    while True:
        if active:
            time.sleep(0.3); continue
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                while not active:
                    try:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    except sr.WaitTimeoutError:
                        continue
                    try:
                        text = recognizer.recognize_google(audio).lower()
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        print(f"  (wake-word recog error: {e})"); time.sleep(1); continue
                    tokens = set(text.replace(",", " ").replace(".", " ").split())
                    if WAKE_WORD in tokens:
                        print(f'  Wake word detected: "{text}"')
                        threading.Thread(target=wake_up, daemon=True).start()
                        break
        except Exception as e:
            print(f"  (wake-word mic error: {e})"); time.sleep(1)

# ─── Wake-up ──────────────────────────────────────────────────────────────────
def wake_up():
    global active, conversation_history, visual_state

    active       = True
    visual_state = "waking"
    conversation_history = []

    # Update wake count + last wake timestamp; read and clear skip_intro flag
    mem = load_memory()
    mem["wake_count"] = mem.get("wake_count", 0) + 1
    mem["last_wake"]  = time.time()
    skip_intro = mem.get("skip_intro", False)
    if skip_intro:
        mem["skip_intro"] = False
    save_memory(mem)

    if skip_intro:
        speak("Welcome back. What do you need help with?")
        listen_loop()
        return

    print("\n" + "=" * 42)
    print("  ⚡  JARVIS ACTIVATED  ⚡")
    print("=" * 42)

    t_start = time.time()

    # Fetch news, weather, suggestion all in parallel — immediately
    weather_result = [None]; news_result = [[]]; memory_result = [None]
    def _fw(): weather_result[0] = fetch_weather()
    def _fn(): news_result[0]    = fetch_headlines(6)
    def _fm(): memory_result[0]  = get_suggestion(mem)
    for fn in (_fw, _fn, _fm):
        threading.Thread(target=fn, daemon=True).start()

    # Start intro music
    music_on = False
    if SONG_PATH:
        try:
            if pygame.mixer.get_init(): pygame.mixer.music.stop()
            pygame.mixer.init()
            pygame.mixer.music.load(SONG_PATH)
            pygame.mixer.music.play(start=3.0)
            music_on = True
        except Exception as e:
            print(f"Intro music error: {e}")

    # Wait up to 5.5s for data while music plays
    for _ in range(55):
        if news_result[0] and weather_result[0] is not None:
            break
        time.sleep(0.1)

    weather    = weather_result[0]
    headlines  = news_result[0] or []
    suggestion = memory_result[0]

    # ── Cards fly in from all directions while music plays ────────────────────
    cx, cy = visual.cx, visual.cy

    # (target_x, target_y, fly_dx, fly_dy)
    slots = [
        (cx - 520, cy - 185,  -900, -520),   # left-top    ← NW
        (cx - 520, cy +   5, -1050,    0),   # left-mid    ← W
        (cx - 520, cy + 195,  -900,  520),   # left-bottom ← SW
        (cx + 520, cy - 185,   900, -520),   # right-top   ← NE
        (cx + 520, cy +   5,  1050,    0),   # right-mid   ← E
        (cx + 520, cy + 195,   900,  520),   # right-bottom← SE
    ]

    if weather:
        visual.add_news_card(weather, cx, cy - 340, delay=0.0, tag="WEATHER",
                             img_url=None, fly_dx=0, fly_dy=-900)

    for i, art in enumerate(headlines[:6]):
        if i >= len(slots): break
        tx, ty, odx, ody = slots[i]
        title   = art["title"] if isinstance(art, dict) else art
        img_url = art.get("img")  if isinstance(art, dict) else None
        visual.add_news_card(title, tx, ty, delay=9.0 + i * 0.4,
                             tag="WORLD NEWS", img_url=img_url,
                             fly_dx=odx, fly_dy=ody)

    # Let cards settle while music finishes (~7s left)
    elapsed   = time.time() - t_start
    remaining = max(2.0, 12.5 - elapsed)
    time.sleep(remaining)
    if music_on:
        try: pygame.mixer.music.stop()
        except: pass

    # ── Speak briefing AFTER music ends ──────────────────────────────────────
    time_hour = time.localtime().tm_hour
    greeting  = "Good morning" if time_hour < 12 else ("Good afternoon" if time_hour < 18 else "Good evening")
    parts     = [f"{greeting}. Systems online."]
    if weather:
        parts.append(f"Current conditions: {weather}.")
    if headlines:
        titles = [(h["title"] if isinstance(h, dict) else h) for h in headlines[:3]]
        parts.append("Breaking news: " + ". ".join(titles) + ".")
    if suggestion:
        parts.append(suggestion)
    parts.append("Shall I display the week ahead?")

    # ── Today's reminders ────────────────────────────────────────────────────
    import datetime as _wdt
    today_iso = _wdt.date.today().strftime("%Y-%m-%d")
    due_today = [r for r in load_memory().get("reminders", []) if r.get("date") == today_iso]
    if due_today:
        reminder_lines = "; ".join(r.get("subject", "") for r in due_today)
        parts.append(f"Reminder{'s' if len(due_today)>1 else ''} for today: {reminder_lines}.")

    speak(" ".join(parts))

    # ── Auto-act on study reminders (no confirmation needed) ─────────────────

    # Hide weather/news cards 1s after the briefing finishes
    def _fade_briefing_cards():
        time.sleep(1.0)
        for c in list(visual.news_cards):
            if getattr(c, "tag", "") in ("WEATHER", "WORLD NEWS", "NEWS"):
                c.alive = False
    threading.Thread(target=_fade_briefing_cards, daemon=True).start()

    # ── Week ahead (Google Calendar) ──────────────────────────────────────────
    want_week = listen_yes_no()
    if want_week is None:
        speak("Sorry, shall I show the week ahead? Yes or no.")
        want_week = listen_yes_no()
    cur_mem = load_memory()
    if want_week:
        cal_events = fetch_calendar_events(days=7) if cur_mem.get("gcal_ics_url") else []
        buckets = group_events_by_day(cal_events, 7) if cal_events else [[] for _ in range(7)]
        show_week_view(buckets)

        if not cur_mem.get("gcal_ics_url"):
            speak("Your Google Calendar isn't linked yet. Say, set calendar URL, when ready.")
        elif not cal_events:
            speak("Your calendar looks clear this week.")
        time.sleep(0.3)

    speak("How may I assist you?")
    listen_loop()

# ─── Listen Loop ──────────────────────────────────────────────────────────────
def listen_loop():
    global active, visual_state

    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 1.5
    recognizer.phrase_threshold         = 0.3
    mic = sr.Microphone(); timeouts = 0

    while active:
        visual_state = "listening"
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("\nListening...")
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=40)
            except sr.WaitTimeoutError:
                timeouts += 1
                if timeouts >= 3:
                    speak('Going to standby. Say "Jarvis" when you need me.')
                    active = False; visual_state = "idle"
                continue

        timeouts = 0
        try:
            command = recognizer.recognize_google(audio)
        except sr.UnknownValueError: continue
        except sr.RequestError as e:
            speak(f"Speech recognition error: {e}"); continue

        print(f"You: {command}")
        lower = command.lower()
        if any(p in lower for p in ["goodbye jarvis","go to sleep","sleep jarvis","shut down jarvis"]):
            _gm = load_memory(); _gm["skip_intro"] = True; save_memory(_gm)
            speak('Going offline. Say "Jarvis" when you need me.')
            visual.clear_news_cards()
            active = False; visual_state = "idle"; break

        try: record_command(command)
        except Exception as e: print(f"record_command: {e}")
        ask_claude(command)

    visual_state = "idle"

# ─── Startup Registration ─────────────────────────────────────────────────────
_TASK_NAME = "JarvisLogin"

def register_startup():
    """Register JARVIS via Task Scheduler (ONLOGON, no Windows startup delay)."""
    try:
        jarvis_path = os.path.abspath(__file__)
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        ps = (
            f"$a = New-ScheduledTaskAction -Execute '{pythonw}' "
            f"-Argument '\"{jarvis_path}\"' "
            f"-WorkingDirectory '{os.path.dirname(jarvis_path)}'; "
            f"$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; "
            f"$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
            f"-DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -StartWhenAvailable; "
            f"$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME "
            f"-LogonType Interactive -RunLevel Limited; "
            f"Register-ScheduledTask -TaskName '{_TASK_NAME}' -Action $a "
            f"-Trigger $t -Settings $s -Principal $p -Force | Out-Null"
        )
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True)
        return r.returncode == 0
    except Exception as e:
        print(f"  Startup registration failed: {e}")
        return False

def is_registered_startup():
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"if (Get-ScheduledTask -TaskName '{_TASK_NAME}' -ErrorAction SilentlyContinue) {{'yes'}}"],
            capture_output=True, text=True
        )
        return "yes" in r.stdout
    except Exception:
        return False

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    global API_KEY, client
    if not API_KEY:
        print("=" * 40)
        print("  First-time setup — Anthropic API key")
        print("  (console.anthropic.com → API Keys)")
        print("=" * 40)
        API_KEY = input("Paste API key: ").strip()
        if not API_KEY: print("No key entered."); sys.exit(1)
        save_api_key(API_KEY)
        client = anthropic.Anthropic(api_key=API_KEY)
        print("Key saved.\n")

    pyautogui.FAILSAFE = False

    # Auto-register as startup app (silent, only once)
    if not is_registered_startup():
        if register_startup():
            print("  Startup        : registered (will launch on login)")
        else:
            print("  Startup        : not registered")
    else:
        print("  Startup        : already registered")

    print(f"  edge-tts voice : {'en-GB-RyanNeural' if HAS_EDGE_TTS else 'Windows TTS fallback'}")
    print(f"  News feed      : {'BBC RSS' if HAS_FEEDPARSER else 'unavailable'}")
    print(f"  Weather        : {'wttr.in' if HAS_REQUESTS else 'unavailable'}")
    print(f"  Song path      : {SONG_PATH or 'NOT FOUND'}")
    print('  Say "Jarvis" → wake  |  ESC → exit')

    threading.Thread(target=wake_word_listener, daemon=True).start()

    # ── Fire study pipelines for any reminders due today, on launch ──────────
    def _launch_due_reminders():
        import datetime as _ldt
        today_iso = _ldt.date.today().strftime("%Y-%m-%d")
        due = [r for r in load_memory().get("reminders", []) if r.get("date") == today_iso]
        for r in due:
            topic = r.get("subject", "")
            note  = r.get("note", "")
            run_study_pipeline(f"{topic} — {note}" if note else topic)
    threading.Thread(target=_launch_due_reminders, daemon=True).start()

    visual.run()

if __name__ == "__main__":
    main()
