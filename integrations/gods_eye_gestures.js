/* JARVIS opt-in gesture navigation for the OFFICIAL God's Eye View app.
 * Injected into its index.html, loaded from Vite /public. This does not need a
 * private API key or send video frames to the backend. Tracking runs in browser.
 * Input targets the app's WebGL canvas using ordinary mouse/wheel events; since
 * the upstream renderer evolves, mouse-event gesture support is best-effort.
 */
(() => {
  'use strict';
  if (window.__jarvisGestureOverlayLoaded) return;
  window.__jarvisGestureOverlayLoaded = true;
  const style = document.createElement('style');
  style.textContent = `
    #jarvis-gesture-toggle {position:fixed;right:16px;bottom:74px;z-index:2147483000;
      background:#0c2437;color:#80e6ff;border:1px solid #4ccce5;border-radius:9px;
      padding:10px 14px;font:600 13px system-ui,sans-serif;cursor:pointer;
      box-shadow:0 3px 16px #0009}
    #jarvis-gesture-panel{position:fixed;right:16px;bottom:122px;z-index:2147483000;
      width:min(300px,calc(100vw - 32px));padding:10px;background:#081521ed;
      border:1px solid #3daacb;border-radius:10px;color:#d4eefa;
      font:12px/1.55 system-ui,sans-serif;box-shadow:0 4px 22px #0009}
    #jarvis-gesture-panel[hidden]{display:none!important}
    #jarvis-gesture-video{width:100%;aspect-ratio:16/9;object-fit:cover;
      background:#000;border-radius:6px;transform:scaleX(-1)}
    #jarvis-gesture-status{margin:6px 0;min-height:18px;overflow-wrap:anywhere}
    #jarvis-gesture-hint{color:#8aaec5;font-size:11px}
  `;
  document.head.appendChild(style);
  const button = document.createElement('button');
  button.id = 'jarvis-gesture-toggle';
  button.textContent = '✋ JARVIS HANDS';
  button.setAttribute('aria-pressed', 'false');
  button.type = 'button';
  const panel = document.createElement('section');
  panel.id = 'jarvis-gesture-panel';
  panel.hidden = true;
  panel.innerHTML = `<strong>JARVIS · 3D HAND NAVIGATION</strong>
    <video id="jarvis-gesture-video" autoplay playsinline muted></video>
    <p id="jarvis-gesture-status" role="status">Camera off</p>
    <div id="jarvis-gesture-hint">🤏 Pinch + move up/down/left/right: move globe<br>
      👐 Two hands: zoom in/out<br>
      Works on your device; stop to release the camera.</div>`;
  document.body.append(panel, button);
  const video = panel.querySelector('#jarvis-gesture-video');
  const status = panel.querySelector('#jarvis-gesture-status');
  if (!window.JarvisGestureEngine?.GestureEngine) {
    status.textContent='Gesture engine missing. Run FIX_GESTURES_WINDOWS.ps1, restart the app, then Ctrl+Shift+R.';
    panel.hidden=false;
    button.addEventListener('click',()=>{panel.hidden=!panel.hidden;});
    return;
  }
  const gestureEngine = new window.JarvisGestureEngine.GestureEngine();
  let enabled=false, stream=null, detector=null, raf=0, lastFrame=-1, lastRun=0;
  let activeDrag=false, dragButton=0, pointerX=0, pointerY=0;
  let target=null;
  const camera = () => window.__jarvisGodsEyeCamera || null;
  const clamp=(value,min,max)=>Math.min(max,Math.max(min,value));
  function moveCamera(dx,dy){
    const cam=camera();
    if (!cam || typeof cam.pose!=='function' || typeof cam.setView!=='function') return false;
    try {
      const p=cam.pose();
      if (![p.lon,p.lat,p.height,p.heading,p.pitch,p.roll].every(Number.isFinite)) return false;
      const metresPerPixel=clamp(p.height/650, 0.6, 120000);
      const lat=clamp(p.lat - dy*metresPerPixel/111320,-85,85);
      const lon=p.lon + dx*metresPerPixel/(111320*Math.max(0.12,Math.cos(p.lat*Math.PI/180)));
      cam.setView({destination:{lon:((lon+540)%360+360)%360-180,lat,height:p.height},
        orientation:{heading:p.heading,pitch:p.pitch,roll:p.roll}});
      return true;
    }catch(error){setStatus('3D camera move failed: '+String(error.message||error).slice(0,80));return false;}
  }
  function zoomCamera(delta){
    const cam=camera();
    if (!cam || typeof cam.pose!=='function' || typeof cam.setView!=='function') return false;
    try {
      const p=cam.pose();
      if (![p.lon,p.lat,p.height,p.heading,p.pitch,p.roll].every(Number.isFinite)) return false;
      const height=clamp(p.height*Math.exp(clamp(delta,-120,120)/650),30,60000000);
      cam.setView({destination:{lon:p.lon,lat:p.lat,height},orientation:{heading:p.heading,pitch:p.pitch,roll:p.roll}});
      return true;
    }catch(error){setStatus('3D camera zoom failed: '+String(error.message||error).slice(0,80));return false;}
  }
  const setStatus = t => {status.textContent = t;};
  // The official app may create new canvases when the renderer changes.
  function getCanvas() {
    const candidates = [...document.querySelectorAll('canvas')].filter(el=>{
      const r=el.getBoundingClientRect();
      return r.width>=250 && r.height>=200 && getComputedStyle(el).visibility!=='hidden';
    });
    candidates.sort((a,b)=>{const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();
      return rb.width*rb.height-ra.width*ra.height;});
    return candidates[0]||null;
  }
  function dispatch(type, btn, x, y) {
    target=getCanvas(); if(!target)return false;
    const data={bubbles:true,cancelable:true,view:window,clientX:x,clientY:y,
                button:btn,buttons:type==='mouseup'?0:btn===1?4:1};
    // Cesium uses mouse events for ScreenSpaceEventHandler on the WebGL canvas.
    target.dispatchEvent(new MouseEvent(type,data));
    return true;
  }
  function endDrag() {
    if(activeDrag) dispatch('mouseup',dragButton,pointerX,pointerY);
    activeDrag=false;
  }
  function drag(dx,dy,btn=0) {
    if(moveCamera(dx,dy)){endDrag();return;}
    const canvas=getCanvas();if(!canvas){setStatus('Waiting for the 3D globe to render…');return;}
    const r=canvas.getBoundingClientRect();
    if(!activeDrag || dragButton!==btn){endDrag();pointerX=r.left+r.width/2;
      pointerY=r.top+r.height/2;dragButton=btn;
      dispatch('mousedown',btn,pointerX,pointerY);activeDrag=true;}
    pointerX=Math.max(r.left+20,Math.min(r.right-20,pointerX+dx));
    pointerY=Math.max(r.top+20,Math.min(r.bottom-20,pointerY+dy));
    dispatch('mousemove',btn,pointerX,pointerY);
  }
  function zoom(delta) {
    endDrag();
    if(zoomCamera(delta)) return;
    target=getCanvas();if(!target)return;
    const r=target.getBoundingClientRect();
    target.dispatchEvent(new WheelEvent('wheel',{
      bubbles:true,cancelable:true,deltaMode:0,deltaY:Math.max(-220,Math.min(220,delta)),
      clientX:r.left+r.width/2,clientY:r.top+r.height/2,view:window}));
  }
  function stop() {
    enabled=false;cancelAnimationFrame(raf);raf=0;endDrag();
    stream?.getTracks().forEach(t=>t.stop());stream=null;
    detector?.close?.();detector=null;video.srcObject=null;
    gestureEngine.reset();lastFrame=-1;
    button.textContent='✋ JARVIS HANDS';button.setAttribute('aria-pressed','false');
    panel.hidden=true;
  }
  async function start() {
    if(enabled)return;
    enabled=true;panel.hidden=false;
    button.textContent='■ STOP HANDS';button.setAttribute('aria-pressed','true');
    setStatus('Requesting webcam access…');
    try {
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('Use localhost or HTTPS to enable the webcam');
      stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:360,frameRate:{ideal:20}},audio:false});
      if(!enabled){stream.getTracks().forEach(t=>t.stop());return;}
      video.srcObject=stream;await video.play();
      setStatus('Loading MediaPipe…');
      // Use locally installed MediaPipe assets first. No primary CDN dependency.
      // A separate unpkg fallback handles partial/older installations.
      let visionModule, wasm;
      try {
        visionModule = await import('/jarvis_mediapipe/vision_bundle.mjs');
        wasm = await visionModule.FilesetResolver.forVisionTasks('/jarvis_mediapipe/wasm');
      } catch (localError) {
        setStatus('Local MediaPipe unavailable; trying fallback…');
        try {
          visionModule = await import('https://unpkg.com/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs');
          wasm = await visionModule.FilesetResolver.forVisionTasks('https://unpkg.com/@mediapipe/tasks-vision@0.10.21/wasm');
        } catch (fallbackError) {
          throw new Error('MediaPipe could not load. Run FIX_GESTURES_WINDOWS.ps1 in VS Code, restart the map, then Ctrl+Shift+R. Details: ' + String(localError?.message || localError));
        }
      }
      // The model is downloaded during setup. Fall back to the official model URL.
      const modelPath='/jarvis_mediapipe/hand_landmarker.task';
      let localModel=false;
      try { const response=await fetch(modelPath,{method:'HEAD'}); localModel=response.ok && (response.headers.get('content-type') || '').indexOf('text/html')<0; }
      catch (_) { /* remote official model fallback */ }
      detector=await visionModule.HandLandmarker.createFromOptions(wasm,{
        baseOptions:{modelAssetPath:localModel?modelPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},
        runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minTrackingConfidence:.65});
      if(!enabled){stop();return;}
      setStatus('Camera ready. Pinch thumb + index finger, then move. Use both hands to zoom.');
      raf=requestAnimationFrame(loop);
    }catch(error){
      const message=error?.name==='NotAllowedError'?'Camera permission denied':String(error?.message||error);
      stop();panel.hidden=false;setStatus('Gesture setup failed: '+message.slice(0,280));
    }
  }
  function loop(timestamp) {
    if(!enabled)return;
    raf=requestAnimationFrame(loop);
    if(!detector||video.readyState<2||video.currentTime===lastFrame||timestamp-lastRun<65)return;
    lastRun=timestamp;lastFrame=video.currentTime;
    let hands=[];
    try { hands=detector.detectForVideo(video,timestamp).landmarks||[]; }
    catch(error){setStatus('Hand recognition error: '+String(error.message||error).slice(0,100));return;}
    const gesture=gestureEngine.step(hands);
    if(gesture.kind==='none'){
      endDrag();setStatus('No hands detected. Improve lighting and show your hands fully.');return;
    }
    if(gesture.kind==='twohand'){
      endDrag();
      if(gesture.zoom) zoom(gesture.zoom);
      setStatus(camera()?'👐 Two hands — 3D camera zoom active':'👐 Two hands detected; waiting for 3D camera…');
      return;
    }
    if(gesture.kind==='idle'){
      endDrag();
      setStatus('One hand detected. Touch thumb and index fingertip to pinch.');
      return;
    }
    if(gesture.dx||gesture.dy){
      drag(gesture.dx,gesture.dy,0);
      setStatus(camera()?'🤏 Pinch — 3D camera moving':'🤏 Pinch detected; waiting for 3D camera…');
    }else{
      setStatus(camera()?'🤏 Pinch detected. Move your hand.':'🤏 Pinch detected; waiting for 3D camera…');
    }
  }
  window.__jarvisGestureDebug = {moveCamera,zoomCamera,camera};
  button.addEventListener('click',()=>enabled?stop():start());
  window.addEventListener('pagehide',stop);
})();
