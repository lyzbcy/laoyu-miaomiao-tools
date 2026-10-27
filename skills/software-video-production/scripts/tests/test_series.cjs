const test=require('node:test'),assert=require('node:assert/strict');
const {seriesDay,validateSeries,validateRecap}=require('../../assets/remotion-software/series-model.cjs');
const shot=()=>({recipe:'previous_episode',synthetic:true,previous:{title:'合成上一期',snapshotAt:'2026-10-27T10:00:00Z',metrics:{views:{value:12000,display:'1.2万'}}}});
test('calendar day is inclusive and does not restart on a version or skipped episode',()=>{
 assert.equal(seriesDay('2026-10-19','2026-10-19'),1);assert.equal(seriesDay('2026-10-19','2026-10-27'),9);assert.equal(seriesDay('2026-10-19','2027-01-01'),75);
});
test('invalid dates and a pre-epoch episode cannot produce a badge',()=>{for(const [a,b] of [['2026-02-30','2026-03-01'],['2026-10-19','2026-10-18'],['19/10/2026','2026-10-27']])assert.throws(()=>seriesDay(a,b));});
test('series stays opt-in, position is explicit, unsupported legacy styles fail',()=>{
 assert.doesNotThrow(()=>validateSeries({}));assert.throws(()=>validateSeries({visualStyle:'unknown'}));assert.throws(()=>validateSeries({recipe:'before_after',visualStyle:'fluent'}));
 const s={series:{enabled:true,position:'upper-center',timezone:'Asia/Shanghai',epochDate:'2026-10-19',episodeDate:'2026-10-27'}};assert.doesNotThrow(()=>validateSeries(s));s.series.position='random';assert.throws(()=>validateSeries(s));
});
test('zero is real data and missing metrics stay absent',()=>{const s=shot();s.previous.metrics={followers:{value:0,display:'0'}};assert.equal(validateRecap(s),true);assert.equal(s.previous.metrics.views,undefined);});
test('rounded displays stay truthful; contradictory numbers are rejected',()=>{const s=shot();assert.equal(validateRecap(s),true);s.previous.metrics.views.value=12001;assert.throws(()=>validateRecap(s),/disagree/);});
test('real recap requires a matched work, timezone and approved cover',()=>{
 const s=shot();s.synthetic=false;assert.throws(()=>validateRecap(s));s.previous.itemId='100';s.previous.sourceUrl='https://creator.douyin.com/creator-micro/work-management/work-detail/100';s.previous.approved=true;s.image='data:image/png;base64,AA==';s.privacyApproved=true;assert.equal(validateRecap(s),true);
 s.previous.sourceUrl+='1';assert.throws(()=>validateRecap(s),/matched/);s.previous.sourceUrl=s.previous.sourceUrl.slice(0,-1);s.previous.snapshotAt='2026-10-27T10:00:00';assert.throws(()=>validateRecap(s),/timezone/);
});
