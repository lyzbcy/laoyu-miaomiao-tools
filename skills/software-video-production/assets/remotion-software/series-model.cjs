// Calendar days use explicit local dates, not render-machine time or episode count.
const METRICS={views:'播放',likes:'点赞',favorites:'收藏',comments:'评论',followers:'新增关注'};
function calendarDate(s){
 if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s))throw Error('explicit YYYY-MM-DD date required');
 const t=Date.parse(s+'T00:00:00Z');if(!Number.isFinite(t)||new Date(t).toISOString().slice(0,10)!==s)throw Error('invalid calendar date');return t;
}
function seriesDay(epochDate,episodeDate){const n=(calendarDate(episodeDate)-calendarDate(epochDate))/86400000+1;if(n<1)throw Error('episode precedes epoch');return n;}
function validateSeries(shot){
 if(shot.visualStyle!==undefined&&!['expressive','fluent','cupertino'].includes(shot.visualStyle))throw Error('unknown visualStyle');
 if(['before_after','detail_zoom','step_progression'].includes(shot.recipe)&&shot.visualStyle&&shot.visualStyle!=='expressive')throw Error('legacy software shots do not support style variants');
 const s=shot.series;if(s===undefined)return;
 if(s.enabled!==true||s.position!=='upper-center'||s.timezone!=='Asia/Shanghai')throw Error('series requires enabled upper-center and explicit Asia/Shanghai dates');
 seriesDay(s.epochDate,s.episodeDate);
}
function validateRecap(shot){
 validateSeries(shot);const p=shot.previous;
 if(!p||typeof p.title!=='string'||!p.title.trim()||p.title.length>60)throw Error('previous title required, <=60 characters');
 if(typeof p.snapshotAt!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(p.snapshotAt)||!Number.isFinite(Date.parse(p.snapshotAt)))throw Error('snapshotAt must include timezone');
 const keys=Object.keys(p.metrics||{});if(!keys.length||keys.some(k=>!METRICS[k]))throw Error('supported per-work metrics required');
 for(const k of keys){
  const m=p.metrics[k];if(!m||!Number.isFinite(m.value)||m.value<0||typeof m.display!=='string'||!m.display.trim()||m.display.length>12)throw Error('metric needs nonnegative value and original short display');
  const match=m.display.match(/^(\d+(?:\.\d+)?)(万|亿)$/),integer=/^(?:\d+|\d{1,3}(?:,\d{3})+)$/.test(m.display);
  const value=match?Number(match[1])*(match[2]==='万'?10000:100000000):integer?Number(m.display.replaceAll(',','')):NaN;
  if(value!==m.value)throw Error('metric display and value disagree');
 }
 if(shot.synthetic!==true){
  if(!/^\d+$/.test(p.itemId||'')||typeof p.sourceUrl!=='string'||p.sourceUrl.split('?')[0]!=='https://creator.douyin.com/creator-micro/work-management/work-detail/'+p.itemId)throw Error('recap needs matched creator per-work source');
  if(p.approved!==true||shot.privacyApproved!==true||!/^data:image\/(png|jpeg);base64,/.test(shot.image||''))throw Error('recap requires approved local cover and reviewed source');
 }
 return true;
}
module.exports={METRICS,calendarDate,seriesDay,validateSeries,validateRecap};
