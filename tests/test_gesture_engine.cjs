const assert = require('node:assert/strict');
const {GestureEngine} = require('../integrations/jarvis_gesture_engine.js');
function hand(x=.5,y=.5,pinched=true){
 const h=Array.from({length:21},()=>({x,y}));
 h[0]={x,y};h[5]={x:x-.10,y};h[9]={x,y};h[13]={x:x+.05,y};h[17]={x:x+.10,y};
 h[4]={x:x-.015,y:y-.075};h[8]={x:x+(pinched?.015:.15),y:y-.075};return h;
}
const e=new GestureEngine();
assert.equal(e.step([hand(.5,.5,false)]).kind,'idle');
assert.equal(e.step([hand(.5,.5)]).kind,'pinch');
assert.equal(e.step([hand(.5,.46)]).dy<0,true,'move up');
assert.equal(e.step([hand(.5,.5)]).dy>0,true,'move down');
assert.equal(e.step([hand(.46,.5)]).dx>0,true,'mirror physical movement right');
assert.equal(e.step([hand(.5,.5)]).dx<0,true,'mirror physical movement left');
assert.equal(e.step([hand(.5,.5,false)]).kind,'idle');
assert.equal(e.step([hand(.5,.5)]).kind,'pinch','re-engage after release');
assert.equal(e.step([hand(.4,.5),hand(.6,.5)]).kind,'twohand');
assert.ok(e.step([hand(.35,.5),hand(.65,.5)]).zoom<0,'spread to zoom in');
assert.ok(e.step([hand(.4,.5),hand(.6,.5)]).zoom>0,'closer to zoom out');
assert.equal(e.step([]).kind,'none');
assert.equal(e.step([]).kind,'none');
assert.equal(e.step([hand(.5,.5)]).kind,'pinch');
console.log('Gesture geometry: 12 assertions passed');
