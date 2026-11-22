/* Optional, on-device webcam gesture navigation. Camera starts only after a click.
 * No frames are sent to the JARVIS backend. MediaPipe model/assets load from
 * Google's official model bucket and jsDelivr when first enabled.
 */
const toggle = document.getElementById('gesture-toggle');
const panel = document.getElementById('gesture-panel');
const video = document.getElementById('gesture-video');
const state = document.getElementById('gesture-state');
let map = null, detector = null, stream = null, enabled = false, frame = 0;
let lastFrameTime = -1, lastRun = 0, prevPalm = null, prevPinch = null;
let lastTwoDistance = null, lastAction = 0;

window.addEventListener('jarvis-map-ready', ev => {map = ev.detail.map;});
map=window.jarvisWorldMap||null;
const dist = (a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
const palm = hand => ({x:(hand[0].x+hand[5].x+hand[9].x+hand[13].x+hand[17].x)/5,
                       y:(hand[0].y+hand[5].y+hand[9].y+hand[13].y+hand[17].y)/5});
const extended = (h,tip,pip,mcp) => h[tip].y < h[pip].y - .012 && h[pip].y < h[mcp].y + .035;
const openPalm = h => [[8,6,5],[12,10,9],[16,14,13],[20,18,17]].filter(([t,p,m])=>extended(h,t,p,m)).length >= 3;
const closeHand = h => !openPalm(h) && dist(h[4],h[8])>.095;
function cameraStop() {
  enabled=false;
  if(frame) cancelAnimationFrame(frame);
  frame=0;
  stream?.getTracks().forEach(t=>t.stop());stream=null;
  video.srcObject=null;
  prevPalm=null;prevPinch=null;lastTwoDistance=null;
  detector?.close?.();detector=null;
  panel.hidden=true;toggle.setAttribute('aria-pressed','false');toggle.textContent='✋ Enable gestures';
  state.textContent='Camera off';
}
async function start() {
  if(enabled) return;
  enabled=true; panel.hidden=false;toggle.setAttribute('aria-pressed','true');toggle.textContent='■ Stop gestures';
  state.textContent='Requesting webcam permission…';
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('Webcam requires a localhost or secure browser context.');
    stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:360,frameRate:{ideal:20,max:30}},audio:false});
    if(!enabled){stream.getTracks().forEach(t=>t.stop());return;}
    video.srcObject=stream;await video.play();
    state.textContent='Loading MediaPipe hand model…';
    const {FilesetResolver,HandLandmarker}=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs');
    const files=await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm');
    detector=await HandLandmarker.createFromOptions(files,{
      baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},
      runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.6,minTrackingConfidence:.6});
    if(!enabled){cameraStop();return;}
    state.textContent='Ready — show an open palm to pan.';
    frame=requestAnimationFrame(loop);
  }catch(error){
    const msg=error?.name==='NotAllowedError'?'Camera permission denied':error?.message||'Gesture startup failed';
    cameraStop();panel.hidden=false;state.textContent='Gesture error: '+String(msg).slice(0,130);
  }
}
function loop(t) {
  if(!enabled)return;
  frame=requestAnimationFrame(loop);
  if(!map||!detector||video.readyState<2||video.currentTime===lastFrameTime||t-lastRun<90)return;
  lastRun=t;lastFrameTime=video.currentTime;
  let hands;
  try{hands=detector.detectForVideo(video,t).landmarks||[];}
  catch(error){state.textContent='Hand tracking failed: '+String(error?.message||error).slice(0,90);return;}
  if(!hands.length){prevPalm=null;prevPinch=null;lastTwoDistance=null;state.textContent='Show your hand to control the map.';return;}
  // Treat gestures as camera-local navigation; never send hand positions to the server.
  if(hands.length>=2){
    const a=palm(hands[0]),b=palm(hands[1]), d=dist(a,b);
    if(lastTwoDistance!==null && t-lastAction>160) {
      const delta=Math.max(-.35,Math.min(.35,(d-lastTwoDistance)*3));
      if(Math.abs(delta)>.025){map.zoomTo(Math.max(map.getMinZoom(),Math.min(map.getMaxZoom(),map.getZoom()+delta)),{duration:120});lastAction=t;}
    }
    lastTwoDistance=d;prevPalm=null;prevPinch=null;state.textContent='Two hands: change distance to zoom';return;
  }
  lastTwoDistance=null;
  const h=hands[0], p=palm(h), pinching=dist(h[4],h[8])<.07;
  if(pinching){
    if(prevPinch!==null && t-lastAction>150) {
      const delta=Math.max(-.23,Math.min(.23,(prevPinch.y-p.y)*4));
      if(Math.abs(delta)>.02){map.zoomTo(Math.max(map.getMinZoom(),Math.min(map.getMaxZoom(),map.getZoom()+delta)),{duration:130});lastAction=t;}
    }
    prevPinch=p;prevPalm=null;state.textContent='Pinch and move up/down: zoom';return;
  }
  prevPinch=null;
  if(openPalm(h)){
    if(prevPalm && t-lastAction>100){
      const dx=Math.max(-95,Math.min(95,(prevPalm.x-p.x)*900));
      const dy=Math.max(-95,Math.min(95,(p.y-prevPalm.y)*650));
      if(Math.hypot(dx,dy)>5){map.panBy([dx,dy],{duration:90});lastAction=t;}
    }
    prevPalm=p;state.textContent='Open palm: move your hand to pan';return;
  }
  prevPalm=null;state.textContent=closeHand(h)?'Fist: navigation paused':'Show an open palm or pinch';
}
toggle.addEventListener('click',()=> enabled?cameraStop():start());
window.addEventListener('pagehide',cameraStop);
