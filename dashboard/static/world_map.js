/* Mark-LVII World Map: resilient browser boot, MapLibre-only overlay renderer.
 * Map data is provided by authorized, individually attributed sources; no invented tracking.
 */
(() => {
 'use strict';
 const status = document.getElementById('status');
 const ids = ['planes','sats','ships','trails','seamarks','traffic'];
 const elements = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
 const notes = [];
 const counts = {planes:'plane-count',sats:'sat-count',ships:'ship-count'};
 const iconOf = {planes:'✈',sats:'✧',ships:'⛴'};
 const safe = value => String(value ?? '—').slice(0, 110);
 let map, GL, busy = false, movedTimer, vesselTimer, darkMode = true, mapTilerActive = false;
 document.documentElement.classList.add('godseye-dark');
 let shipPositions = [], pointMarkers = {planes:[],sats:[],ships:[]};
 const debug = (message, detail) => {console.warn('[JARVIS World Map]', message, detail || '');};
 function note(message) {
   notes.push(message); if (notes.length > 7) notes.shift();
   status.textContent = notes.join('\n');
 }
 function fail(message, detail) {
   debug(message, detail);
   status.textContent = 'Map startup problem: ' + message + '\nCheck browser Console (F12) and internet access. Then press Ctrl+Shift+R.';
 }
 function count(key, value) {document.getElementById(counts[key]).textContent = String(value);}
 const delay = ms => new Promise((_, reject) => setTimeout(() => reject(new Error('Loading timed out')), ms));
 async function tryImport(url) {
   return Promise.race([import(url), delay(12000)]);
 }
 async function loadRenderer() {
   // Avoid all-or-nothing static imports. A blocked CDN should never leave "Starting map..." forever.
   const sources = [
     'https://unpkg.com/maplibre-gl@6.3.0/dist/maplibre-gl.mjs',
     'https://cdn.jsdelivr.net/npm/maplibre-gl@6.3.0/dist/maplibre-gl.mjs'
   ];
   for (const url of sources) {
     try {
       const loaded = await tryImport(url);
       if (typeof loaded.Map === 'function' && typeof loaded.Marker === 'function') return loaded;
       debug('MapLibre API missing from ' + url);
     } catch (error) {debug('Unable to load ' + url, error);}
   }
   throw new Error('Map renderer could not load from either CDN (unpkg or jsDelivr).');
 }
 async function getJSON(url) {
   const response = await fetch(url, {cache:'no-store', signal:AbortSignal.timeout(17000)});
   const body = await response.json();
   if (!response.ok || body.ok === false) throw new Error(safe(body.error || `HTTP ${response.status}`));
   return body;
 }
 function bboxQuery() {
   const b = map.getBounds();
   const south = Math.max(-89.9, b.getSouth()), north = Math.min(89.9, b.getNorth());
   const west = Math.max(-180, b.getWest()), east = Math.min(180, b.getEast());
   if (south >= north || west >= east) return null;
   return new URLSearchParams({south:south.toFixed(4),west:west.toFixed(4),north:north.toFixed(4),east:east.toFixed(4)}).toString();
 }
 function detailedEnough() {
   if (map.getZoom() < 6) return false;
   const b=map.getBounds();
   return (b.getNorth()-b.getSouth()) <= 25 && (b.getEast()-b.getWest()) <= 40 && !!bboxQuery();
 }
 function clearMarkers(kind) {for(const m of pointMarkers[kind]) m.remove(); pointMarkers[kind]=[];}
 function renderPoints(kind, items, details) {
   clearMarkers(kind);
   if(!elements[kind].checked) return;
   for(const p of (items || [])) {
     if(!Number.isFinite(p.lat) || !Number.isFinite(p.lon)) continue;
     const node = document.createElement('span');
     node.className = 'marker ' + ({planes:'plane',sats:'sat',ships:'ship'}[kind]);
     node.textContent = iconOf[kind];
     node.title = safe(p.label);
     const wrapper = document.createElement('div');
     const label = document.createElement('b'); label.textContent = safe(p.label);
     wrapper.appendChild(label);
     for (const line of details(p)) {
       if (!line) continue;
       const el=document.createElement('div');el.textContent=safe(line);wrapper.appendChild(el);
     }
     const marker = new GL.Marker({element:node, anchor:'center'})
       .setLngLat([p.lon,p.lat]).setPopup(new GL.Popup({offset:14}).setDOMContent(wrapper)).addTo(map);
     pointMarkers[kind].push(marker);
   }
 }
 function setMapLayer(id, show) {
   if (!map || !map.getLayer(id)) return;
   map.setLayoutProperty(id,'visibility',show ? 'visible' : 'none');
 }
 function ensureRasters() {
   if (!map.getSource('seamarks')) {
     map.addSource('seamarks',{type:'raster',tiles:['https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png'],tileSize:256});
     map.addLayer({id:'seamarks',type:'raster',source:'seamarks',paint:{'raster-opacity':0.75},layout:{visibility:'none'}});
   }
   if (!map.getSource('traffic')) {
     map.addSource('traffic',{type:'raster',tiles:[location.origin+'/api/traffic/{z}/{x}/{y}.png'],tileSize:256});
     map.addLayer({id:'traffic',type:'raster',source:'traffic',paint:{'raster-opacity':0.8},layout:{visibility:'none'}});
   }
   if(!map.getSource('trails')) {
     map.addSource('trails',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
     map.addLayer({id:'trails',type:'line',source:'trails',paint:{'line-color':'#4ceba8','line-width':2,'line-dasharray':[2,3]},layout:{visibility:'none'}});
   }
 }
 function updateTrails(items) {
   shipPositions=items || [];
   if(!map.getSource('trails')) return;
   const features = elements.trails.checked && elements.ships.checked ? shipPositions.flatMap(p=>{
     if(!Array.isArray(p.trail) || p.trail.length < 2) return [];
     // AIS server provides [lat,lon] for each historical observation.
     const coords=p.trail.filter(x=>Array.isArray(x)&&x.length===2&&x.every(Number.isFinite)).map(x=>[x[1],x[0]]);
     return coords.length>=2?[{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:coords}}]:[];
   }):[];
   map.getSource('trails').setData({type:'FeatureCollection',features});
   setMapLayer('trails',elements.trails.checked && elements.ships.checked);
 }
 async function refresh() {
   if(busy || !map || !map.isStyleLoaded()) return;
   busy=true;notes.length=0;note('Refreshing available layers…');
   try {
     const config=await getJSON('/api/status');
     if(elements.traffic.checked && !config.traffic) {
       elements.traffic.checked=false;
       note('Traffic requires your TomTom API key in local settings.');
     }
     if(elements.ships.checked && !config.ships){
       note('AIS requires your AISstream API key in local settings.');
     }
     setMapLayer('traffic',elements.traffic.checked && config.traffic);
     setMapLayer('seamarks',elements.seamarks.checked);
     const updates=[];
   if(elements.sats.checked) updates.push((async()=>{
       try {
         const d=await getJSON('/api/satellites');
         renderPoints('sats',d.items,()=>['Calculated orbit estimate, not live telemetry']);
         count('sats',d.items.length);note('Satellites: '+d.items.length+' estimated positions.');
       } catch(err){count('sats','—');note('Satellites: '+safe(err.message));}
     })());
     if(elements.planes.checked) updates.push((async()=>{
       if(!detailedEnough()) {clearMarkers('planes');count('planes','—');note('Aircraft: click Explore flights, or zoom to level 6+ over any region.');}
       else try {
         const d=await getJSON('/api/aircraft?'+bboxQuery());
         renderPoints('planes',d.items,p=>[p.country,p.altitude_m == null ? '' : 'Altitude '+p.altitude_m+' m',p.age_s == null ? '' : 'Age '+p.age_s+' s'].filter(Boolean));
         count('planes',d.items.length);note('Aircraft: '+d.items.length+' from '+safe(d.source)+'.'+(d.items.length ? '' : ' No positions reported in this region; feed coverage may be limited.'));
       } catch(err) {count('planes','—');note('Aircraft: '+safe(err.message));}
     })());
     if(elements.ships.checked) updates.push((async()=>{
       if(!config.ships){clearMarkers('ships');updateTrails([]);count('ships','—');}
       else if(!detailedEnough()) {clearMarkers('ships');updateTrails([]);count('ships','—');note('Vessels: zoom in to view regional AIS reports.');}
       else try {
         const d=await getJSON('/api/ships?'+bboxQuery());
         renderPoints('ships',d.items,p=>[p.speed_kn==null?'':'Speed: '+p.speed_kn+' kn',p.age_s==null?'':'Position age '+p.age_s+' s'].filter(Boolean));
         updateTrails(d.items);count('ships',d.items.length);note('Vessels: '+d.items.length+' recently reported. '+safe(d.status||'AIS feed may take time to report positions.'));
       }catch(err){count('ships','—');note('Vessels: '+safe(err.message));}
     })());
     await Promise.all(updates);
   } catch(err) {note('Dashboard: '+safe(err.message));}
   finally {busy=false;}
 }
 async function refreshVessels() {
   if(!map || busy || !elements.ships.checked || !detailedEnough()) return;
   try {
     const d=await getJSON('/api/ships?'+bboxQuery());
     renderPoints('ships',d.items,p=>[p.speed_kn==null?'':'Speed: '+p.speed_kn+' kn']);
     updateTrails(d.items);count('ships',d.items.length);
   }catch(err){debug('AIS refresh unavailable',err);}
 }
 function connectControls(){
   ids.forEach(id=>elements[id].addEventListener('change',()=>{
     if(id==='seamarks'||id==='traffic') setMapLayer(id,elements[id].checked);
     else if(id==='trails') updateTrails(shipPositions);
     else if(!elements[id].checked) {
       clearMarkers(id);if(id==='ships')updateTrails([]);
     }
     refresh();
   }));
   document.getElementById('refresh').addEventListener('click',refresh);
   document.getElementById('diagnose').addEventListener('click', async()=> {
     try {
       const info=await getJSON('/api/diagnostics');
       note('Keys configured (not necessarily connected): AIS '+(info.keys_configured.aisstream?'YES':'NO')+
         ', TomTom '+(info.keys_configured.tomtom?'YES':'NO')+', MapTiler '+(info.keys_configured.maptiler?'YES':'NO')+
         '. Official 3D globe installed: '+(info.upstream_3d_installed?'YES':'NO')+'.');
       if(!detailedEnough())note('Zoom in to level 6+ for regional aircraft and AIS requests.');
     } catch(e) {note('Diagnostics failed: '+safe(e.message));}
   });
   document.getElementById('open-3d').addEventListener('click', async()=> {
     try {
       const info=await getJSON('/api/diagnostics');
       if(!info.upstream_3d_installed){ note('To install 3D: run INSTALL_GODS_EYE_WINDOWS.ps1 in VS Code PowerShell, then run OPEN_3D_GODS_EYE_WINDOWS.bat.');return; }
       window.open('http://127.0.0.1:4173/','_blank','noopener,noreferrer');
       note('If 3D is offline, start OPEN_3D_GODS_EYE_WINDOWS.bat on your PC.');
     }catch(e){note('3D link: '+safe(e.message));}
   });
   document.getElementById('home').addEventListener('click',()=>map.flyTo({center:[20,19],zoom:2.5}));
   document.getElementById('map-provider').addEventListener('click',async()=> {
     try {
       if(!mapTilerActive){
         const response=await getJSON('/api/maptiler-style');
         map.setStyle(response.style);
         mapTilerActive=true;
         note('MapTiler style selected. Its browser key is visible to this browser; restrict it to your localhost origin.');
       } else {
         map.setStyle('https://tiles.openfreemap.org/styles/liberty');
         mapTilerActive=false;
         note('OpenFreeMap style selected.');
       }
       document.getElementById('map-provider').textContent=mapTilerActive?'🗺 OpenFreeMap style':'🗺 MapTiler style';
     }catch(e){note('Map style: '+safe(e.message));}
   });
   document.getElementById('map-theme').addEventListener('click',()=> {
     darkMode=!darkMode;
     const button=document.getElementById('map-theme');
     button.textContent=darkMode?'◐ Dark map: ON':'◑ Dark map: OFF';
     button.setAttribute('aria-pressed',String(darkMode));
     document.documentElement.classList.toggle('godseye-dark', darkMode);
     note('Map appearance switched. Map tiles remain on the verified Liberty style.');
   });
   document.getElementById('find-flights').addEventListener('click',()=> {
     // Default demonstration region only; users can pan anywhere.
     map.flyTo({center:[77.21,28.61],zoom:8,essential:true});
     note('Exploring a regional flight feed. Zoom or pan to any other region.');
   });
 }
 async function start(){
   status.textContent='Loading map renderer…';
   try { GL=await loadRenderer(); }
   catch(err){fail(err.message,err);return;}
   try {
     status.textContent='Connecting to OpenFreeMap…';
     map=new GL.Map({container:'map',style:'https://tiles.openfreemap.org/styles/liberty',center:[77.21,28.61],zoom:7,minZoom:1.5,renderWorldCopies:false,attributionControl:true});
     map.addControl(new GL.NavigationControl({showCompass:false}),'top-right');
     let started=false;
     const startupTimeout=setTimeout(()=>{
       if(!started)fail('Map tiles did not load. Open https://tiles.openfreemap.org/styles/liberty in this browser to check provider access. Check F12 Console.');
     },20000);
     map.on('style.load',()=>{
       if(started){try {ensureRasters();updateTrails(shipPositions);refresh();}
         catch(err){note('Style layer initialization: '+safe(err.message));}}
     });
     map.once('load',()=>{
       started=true;clearTimeout(startupTimeout);
       try {ensureRasters();connectControls();window.jarvisWorldMap=map;window.dispatchEvent(new CustomEvent('jarvis-map-ready',{detail:{map}}));note('Map ready. Loading regional feeds near Delhi. Pan to another region for more.');refresh();}
       catch(err){fail('Layer setup failed: '+safe(err.message),err);}
     });
     map.on('error',err=>{
       debug('Map tile/style issue',err.error || err);
       const failure = String((err.error && err.error.message) || 'network failure');
       if(started && /403|404|429|cors|network|failed to fetch/i.test(failure)) note('Base map network warning: '+safe(failure));
       if(!started) status.textContent='Loading map… the map provider may be unreachable. If this continues, check F12 Console.';
     });
     map.on('moveend',()=>{clearTimeout(movedTimer);movedTimer=setTimeout(refresh,700);});
     setInterval(refresh,90000);
     vesselTimer=setInterval(refreshVessels,12000);
   }catch(err){fail('Unable to create map: '+safe(err.message),err);}
 }
 start();
})();
