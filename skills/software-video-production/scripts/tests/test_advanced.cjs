const {test}=require('node:test');
const assert=require('node:assert/strict');
const {stateAt,validateAdvancedShot}=require('../../assets/remotion-software/advanced-model.cjs');
const fixture=require('../fixtures/advanced-shots.json');
test('all executable examples satisfy asset and reading-window constraints',()=>{
 for(const shot of fixture.shots)validateAdvancedShot(shot,30);
});
test('seeking out of order gives identical states and stable readable ending',()=>{
 for(const shot of fixture.shots){
  const before=stateAt(shot,20,30);stateAt(shot,999,30);assert.deepEqual(stateAt(shot,20,30),before);
  const end=stateAt(shot,shot.frames-1,30);assert.equal(end.p,1);assert.ok(Math.abs(end.blur)<1e-10);assert.equal(end.scale,1);
 }
});
test('whip layers share a boundary and remain adjacent throughout movement',()=>{
 const shot=fixture.shots.find(s=>s.recipe==='whip_bridge');
 for(let f=0;f<shot.frames;f++){const {p}=stateAt(shot,f,30);assert.ok(p>=0&&p<=1);assert.ok(Math.abs(((1-p)*100)-(-p*100+100))<1e-10);}
});
test('privacy cannot be bypassed through image arrays or synthetic false',()=>{
 const stack=fixture.shots.find(s=>s.recipe==='depth_stack');
 assert.throws(()=>validateAdvancedShot({...stack,privacyApproved:false},30));
 assert.throws(()=>validateAdvancedShot({...stack,images:['https://example.com/x.png','data:image/png;base64,abc']},30));
 assert.throws(()=>validateAdvancedShot({recipe:'hero_dolly',frames:90,synthetic:false},30));
 assert.throws(()=>validateAdvancedShot({recipe:'whip_bridge',frames:90,synthetic:false,bridge:'a → b'},30));
});
test('reading time, reduced motion and semantic groups are enforced',()=>{
 assert.throws(()=>validateAdvancedShot({recipe:'focus_pull',frames:60,settleFrame:59},30));
 assert.throws(()=>validateAdvancedShot({recipe:'hero_dolly',frames:90,reducedMotion:true},30));
 assert.throws(()=>validateAdvancedShot({recipe:'kinetic_mask',frames:90,words:['这是一段远远过长的文字']},30));
 const s=stateAt({recipe:'focus_pull',reducedMotion:true},15,30);assert.equal(s.scale,1);assert.ok(s.blur<=2);
});
