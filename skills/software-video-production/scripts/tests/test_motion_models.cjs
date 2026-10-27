const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const m=require('../../assets/remotion-software/motion-model.cjs');
const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/motion-shots.json'),'utf8'));
const shot=(name)=>structuredClone(fixtures.shots.find(x=>x.recipe===name));

test('all nine fixture recipes are valid and have time to settle',()=>{
 assert.equal(new Set(fixtures.shots.map(x=>x.recipe)).size,9);
 for(const s of fixtures.shots){assert.equal(m.validateMotionShot(s,30),true);assert.ok(m.schedule(s,30).end<s.frames-30);}
});
test('reveal clamps exactly and stays still after completion',()=>{
 assert.equal(m.progress(-5,10,40),0);assert.equal(m.progress(40,10,40),1);assert.equal(m.progress(400,10,40),1);
 const values=Array.from({length:100},(_,i)=>m.progress(i,10,40));
 for(let i=1;i<values.length;i++)assert.ok(values[i]>=values[i-1]);
 assert.throws(()=>m.progress(1,10,10));
});
test('one shared zero baseline preserves magnitude ratios',()=>{
 const s=shot('metric_compare');s.maxValue=100;const {min,max}=m.chartScale(s);
 assert.equal(min,0);assert.equal(max,100);assert.equal(s.items[0].value/max,.35);assert.equal(s.items[1].value/max,.65);
 s.maxValue=40;assert.throws(()=>m.validateMotionShot(s,30),/crop/);
});
test('actual zero values produce a defined chart scale',()=>{
 const s=shot('metric_compare');s.items.forEach(x=>x.value=0);assert.equal(m.chartScale(s).max,1);assert.equal(m.validateMotionShot(s,30),true);
});
test('irregular source x spacing survives geometry mapping',()=>{
 const s=shot('trend_trace'),p=m.graphPoints(s);assert.equal(p[1].x,1/7);assert.equal(p[3].x,4/7);assert.equal(p.at(-1).x,1);
 assert.equal(p[3].value,s.points[3].value);
});
test('unsorted or partially missing sample positions are rejected',()=>{
 const s=shot('trend_trace');s.points[2].x=s.points[1].x;assert.throws(()=>m.validateMotionShot(s,30),/increasing/);
 delete s.points[2].x;assert.throws(()=>m.validateMotionShot(s,30),/increasing/);
});
test('unsupported negative and non-finite measurements stop rendering',()=>{
 for(const v of [-1,NaN,Infinity]){const s=shot('metric_compare');s.items[0].value=v;assert.throws(()=>m.validateMotionShot(s,30));}
});
test('real data cannot silently inherit synthetic approval',()=>{
 const s=shot('metric_compare');s.synthetic=false;assert.throws(()=>m.validateMotionShot(s,30),/approved source/);
 s.dataEvidence={reference:'approved-source.json',approved:true};assert.equal(m.validateMotionShot(s,30),true);
});
test('default reduction is off and no automatic exit is inserted',()=>{
 const s=shot('claim_reveal');assert.equal(s.reduceDistractions,undefined);assert.equal(m.schedule(s,30).exit,null);
 assert.equal(m.opacityAt(s.frames-1,s,30),1);
});
test('a chosen exit occurs only after the held content has settled',()=>{
 const s=shot('claim_reveal');s.timing={exitStartFrame:100};assert.equal(m.validateMotionShot(s,30),true);
 assert.equal(m.opacityAt(99,s,30),1);assert.equal(m.opacityAt(119,s,30),0);
 s.timing.exitStartFrame=5;assert.throws(()=>m.validateMotionShot(s,30),/exit/);
});
test('focus and claim timing cannot be outside the real shot',()=>{
 const s=shot('evidence_focus');s.focusStartFrame=180;assert.throws(()=>m.validateMotionShot(s,30),/focus/);
 s.focusStartFrame=75;s.claimStartFrame=180;assert.throws(()=>m.validateMotionShot(s,30),/claim/);
});
test('spotlight cannot extend beyond the display and real images are required',()=>{
 const s=shot('spotlight_roi');s.roi.x=.8;assert.throws(()=>m.validateMotionShot(s,30),/ROI/);
 s.roi.x=.03;s.synthetic=false;assert.throws(()=>m.validateMotionShot(s,30),/redacted/);
});
