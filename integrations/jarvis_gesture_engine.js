/* Pure gesture state machine used by the JARVIS 3D globe overlay.
 * No webcam/network access here; this is separately unit-testable with synthetic landmarks.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.JarvisGestureEngine = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function () {
  'use strict';
  const distance = (a,b) => Math.hypot(a.x-b.x,a.y-b.y);
  const midpoint = (a,b) => ({x:(a.x+b.x)/2,y:(a.y+b.y)/2});
  const palm = h => ({x:(h[0].x+h[5].x+h[9].x+h[13].x+h[17].x)/5,
                      y:(h[0].y+h[5].y+h[9].y+h[13].y+h[17].y)/5});
  const valid = h => Array.isArray(h) && h.length>=21 && [0,4,5,8,9,13,17].every(i => Number.isFinite(h[i]?.x) && Number.isFinite(h[i]?.y));
  const clamp = (n,lo,hi) => Math.min(hi,Math.max(lo,n));

  class GestureEngine {
    constructor(){ this.reset(); }
    reset(){ this.kind='idle'; this.anchor=null; this.lastDistance=null; this.smoothedX=0;this.smoothedY=0;this.invalidFrames=0; }
    step(rawHands){
      const hands=(rawHands||[]).filter(valid);
      if(!hands.length){this.invalidFrames++;if(this.invalidFrames>=2)this.reset();return {kind:'none'};}
      this.invalidFrames=0;
      if(hands.length>=2){
        const d=distance(palm(hands[0]),palm(hands[1]));
        if(this.kind!=='twohand'){
          this.kind='twohand';this.lastDistance=d;this.anchor=null;return {kind:'twohand',zoom:0};
        }
        const movement=d-this.lastDistance;
        this.lastDistance=d;
        // Moving hands further apart zooms in (negative wheel delta).
        return {kind:'twohand',zoom:Math.abs(movement)>0.004?clamp(-movement*1050,-110,110):0};
      }
      const h=hands[0];
      // Scale-invariant pinch detection: fingertips relative to palm breadth.
      // Hysteresis prevents an unstable classification near the threshold.
      const width=Math.max(0.015,distance(h[5],h[17]));
      const ratio=distance(h[4],h[8])/width;
      const pinching=ratio<(this.kind==='pinch'?0.62:0.45);
      if(!pinching){
        this.kind='idle';this.anchor=null;this.lastDistance=null;
        this.smoothedX=0;this.smoothedY=0;
        return {kind:'idle',ratio};
      }
      const pos=midpoint(h[4],h[8]);
      if(this.kind!=='pinch'||!this.anchor){
        this.kind='pinch';this.anchor=pos;this.smoothedX=0;this.smoothedY=0;
        return {kind:'pinch',dx:0,dy:0,ratio};
      }
      const rawX=clamp(-(pos.x-this.anchor.x)*1100,-60,60);
      const rawY=clamp((pos.y-this.anchor.y)*900,-60,60);
      this.anchor=pos;
      // Smooth landmarks while preserving a predictable drag direction.
      this.smoothedX=0.5*rawX+0.5*this.smoothedX;
      this.smoothedY=0.5*rawY+0.5*this.smoothedY;
      const dx=Math.abs(this.smoothedX)>=2?this.smoothedX:0;
      const dy=Math.abs(this.smoothedY)>=2?this.smoothedY:0;
      return {kind:'pinch',dx,dy,ratio};
    }
  }
  return {GestureEngine,distance,palm,valid};
});
