// Original data and timing helpers. No third-party template source copied.
const DATA_RECIPES=new Set(['metric_compare','trend_trace','target_gap']);
const MOTION_RECIPES=new Set([...DATA_RECIPES,'evidence_focus','causal_flow','task_router','claim_reveal','spotlight_roi','match_transition']);
const finite=(v)=>typeof v==='number'&&Number.isFinite(v);
function fillInk(hex){
 if(!/^#[a-f\d]{6}$/i.test(hex))throw Error('fill must be a six-digit hex color');
 const rgb=hex.slice(1).match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 const luminance=rgb.reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
 return luminance>.179?'#000000':'#ffffff';
}
function progress(frame,start,end){
  if(!finite(frame)||!finite(start)||!finite(end)||end<=start)throw Error('motion range must have finite, increasing endpoints');
  const x=Math.max(0,Math.min(1,(frame-start)/(end-start)));
  return x*x*(3-2*x);
}
function schedule(shot,fps){
  const count=shot.items?.length||shot.points?.length||shot.steps?.length||shot.routes?.length||1;
  const start=shot.timing?.startFrame??Math.round(fps*.2);
  const end=shot.timing?.settleFrame??Math.min(shot.frames-1,Math.round(fps*(1.15+Math.min(count,6)*.18)));
  const exit=shot.timing?.exitStartFrame??null;
  return {start,end,exit,count};
}
function opacityAt(frame,shot,fps){
  const {exit}=schedule(shot,fps);
  return exit===null?1:1-progress(frame,exit,shot.frames-1);
}
function chartScale(shot){
  const values=shot.recipe==='trend_trace'?shot.points.map(p=>p.value):shot.recipe==='target_gap'?[shot.actual,shot.target]:shot.items.map(p=>p.value);
  const raw=Math.max(...values)*1.15||1,step=10**Math.floor(Math.log10(raw));
  return {min:0,max:shot.maxValue??Math.ceil(raw/step)*step};
}
function graphPoints(shot){
  const {min,max}=chartScale(shot), n=shot.points.length;
  const left=shot.points[0].x??0,right=shot.points[n-1].x??(n-1);
  return shot.points.map((p,i)=>({label:p.label,value:p.value,x:((p.x??i)-left)/(right-left),y:1-(p.value-min)/(max-min)}));
}
function requireText(value,label,max=100){if(typeof value!=='string'||!value.trim()||value.length>max)throw Error(label+' must be nonempty text <= '+max+' characters');}
function rows(value,label,min,max){if(!Array.isArray(value)||value.length<min||value.length>max)throw Error(label+' count must be '+min+'..'+max);}
function validateMotionShot(shot,fps){
  if(!MOTION_RECIPES.has(shot.recipe))throw Error('unknown motion recipe');
  requireText(shot.title,'title',48);
  if(!Number.isInteger(shot.frames)||shot.frames<fps*2)throw Error('motion shot must have at least two seconds');
  if(shot.theme!==undefined&&!['dark','light'].includes(shot.theme))throw Error('theme must be dark or light');
  if(shot.accent!==undefined&&!/^#[a-f\d]{6}$/i.test(shot.accent))throw Error('accent must be a six-digit hex color');
  const {start,end,exit}=schedule(shot,fps);
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>=shot.frames)throw Error('motion must settle within the shot');
  if(exit!==null&&(!Number.isInteger(exit)||exit<end||exit>=shot.frames-1))throw Error('exit must follow settled state and leave a transition interval');
  if(DATA_RECIPES.has(shot.recipe)){
    requireText(shot.unit,'unit',12);
    if(shot.synthetic===false&&(shot.dataEvidence?.approved!==true||!shot.dataEvidence?.reference))throw Error('real data requires an approved source reference; approval does not verify factual accuracy');
    if(shot.recipe==='metric_compare'){
      rows(shot.items,'comparison items',2,6);
      shot.items.forEach(p=>{requireText(p.label,'item label',18);if(!finite(p.value)||p.value<0)throw Error('comparison values must be finite and nonnegative');});
    }else if(shot.recipe==='trend_trace'){
      rows(shot.points,'trend points',3,12);
      shot.points.forEach(p=>{requireText(p.label,'point label',12);if(!finite(p.value)||p.value<0)throw Error('trend values must be finite and nonnegative');});
      const hasX=shot.points.map(p=>p.x!==undefined);
      if(hasX.some(Boolean)&&(!hasX.every(Boolean)||shot.points.some((p,i)=>!finite(p.x)||(i&&p.x<=shot.points[i-1].x))))throw Error('provide increasing x values for every sample or omit x for ordinal spacing');
      if(shot.highlightIndex!==undefined&&(!Number.isInteger(shot.highlightIndex)||shot.highlightIndex<0||shot.highlightIndex>=shot.points.length))throw Error('highlightIndex is outside sample points');
    }else if(!finite(shot.actual)||!finite(shot.target)||shot.actual<0||shot.target<0)throw Error('target and actual must be finite and nonnegative');
    const max=shot.recipe==='metric_compare'?Math.max(...shot.items.map(p=>p.value)):shot.recipe==='trend_trace'?Math.max(...shot.points.map(p=>p.value)):Math.max(shot.actual,shot.target);
    if(shot.maxValue!==undefined&&(!finite(shot.maxValue)||shot.maxValue<=0||shot.maxValue<max))throw Error('maxValue cannot crop data or reverse the scale');
  }
  if(shot.recipe==='evidence_focus'){
    rows(shot.items,'evidence items',2,5);shot.items.forEach(p=>{requireText(p.label,'evidence label',18);requireText(p.detail,'evidence detail',shot.items.length===5?40:48);});
    if(shot.focusIndex!==undefined&&(!Number.isInteger(shot.focusIndex)||shot.focusIndex<0||shot.focusIndex>=shot.items.length))throw Error('focusIndex is outside items');
    if(shot.focusStartFrame!==undefined&&(!Number.isInteger(shot.focusStartFrame)||shot.focusStartFrame<end||shot.focusStartFrame>=shot.frames-1))throw Error('focus must follow evidence reveal');
    if(shot.reduceDistractions!==undefined&&typeof shot.reduceDistractions!=='boolean')throw Error('reduceDistractions must be boolean');
    if(shot.claimStartFrame!==undefined&&(!Number.isInteger(shot.claimStartFrame)||shot.claimStartFrame<end||shot.claimStartFrame>=shot.frames-1))throw Error('claim must follow reveal and leave a readable arrival interval');
    if(shot.prompt!==undefined)requireText(shot.prompt,'continuing question',48);
  }
  if(shot.recipe==='causal_flow'){
    rows(shot.steps,'flow steps',2,5);shot.steps.forEach(p=>{requireText(p.label,'flow label',18);requireText(p.detail,'flow detail',40);});
  }
  if(shot.recipe==='task_router'){
    requireText(shot.origin,'route origin',24);rows(shot.routes,'routes',2,4);shot.routes.forEach(p=>{requireText(p.label,'route label',18);requireText(p.detail,'route detail',42);});
  }
  if(shot.recipe==='claim_reveal'){
    requireText(shot.claim,'claim',70);if(shot.support!==undefined)requireText(shot.support,'support',100);
  }
  if(shot.recipe==='spotlight_roi'){
    const r=shot.roi; if(!r||!['x','y','w','h'].every(k=>finite(r[k]))||r.x<0||r.y<0||r.w<=0||r.h<=0||r.x+r.w>1||r.y+r.h>1)throw Error('ROI must stay within normalized source bounds');
    if(shot.synthetic===false&&!shot.image)throw Error('real spotlight requires a pre-redacted source image');
  }
  if(shot.recipe==='match_transition'){
    requireText(shot.from,'transition origin',28);requireText(shot.to,'transition destination',28);requireText(shot.bridge,'shared transition object',18);
  }
  return true;
}
module.exports={DATA_RECIPES,MOTION_RECIPES,fillInk,progress,schedule,opacityAt,chartScale,graphPoints,validateMotionShot};
