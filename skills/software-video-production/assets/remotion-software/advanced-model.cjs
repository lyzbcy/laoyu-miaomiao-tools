// Original frame-based motion models; no upstream template code is bundled.
const ADVANCED_RECIPES=new Set(['hero_dolly','depth_stack','kinetic_mask','whip_bridge','focus_pull','orbit_gallery']);
const bound=(v,a,b)=>Math.max(a,Math.min(b,v));
function windowFor(shot,fps){
  const start=shot.startFrame??Math.round(fps*.2);
  const end=shot.settleFrame??Math.round(fps*(shot.recipe==='whip_bridge'?.6:1.15));
  return {start,end};
}
function stateAt(shot,frame,fps){
  const {start,end}=windowFor(shot,fps),t=bound((frame-start)/(end-start),0,1),p=t*t*(3-2*t);
  return {p,pan:-p*100,blur:shot.recipe==='whip_bridge'?Math.sin(Math.PI*t)*12:(1-p)*(shot.reducedMotion?2:9),scale:shot.reducedMotion?1:1.06-.06*p,rotateX:(1-p)*12,rotateY:(1-p)*-19};
}
function validateAdvancedShot(shot,fps){
  if(!ADVANCED_RECIPES.has(shot.recipe))throw Error('unknown advanced recipe');
  const {start,end}=windowFor(shot,fps);
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>shot.frames-Math.ceil(fps*.5))throw Error('motion window must leave >=0.5s stable reading; extend duration for content');
  for(const key of ['title','subtitle','bridge'])if(shot[key]!==undefined&&(typeof shot[key]!=='string'||Array.from(shot[key]).length>60))throw Error('advanced copy must be short strings');
  if(shot.accent!==undefined&&!/^#[0-9a-fA-F]{6}$/.test(shot.accent))throw Error('accent must be six-digit hex');
  if(shot.visualStyle!==undefined&&!['cupertino','fluent','expressive'].includes(shot.visualStyle))throw Error('unknown advanced visualStyle');
  if(shot.reducedMotion!==undefined&&typeof shot.reducedMotion!=='boolean')throw Error('reducedMotion must be boolean');
  if(shot.reducedMotion&&shot.recipe!=='focus_pull')throw Error('reduced motion uses focus_pull');
  if(shot.recipe==='kinetic_mask'&&(!Array.isArray(shot.words)||shot.words.length<1||shot.words.length>3||shot.words.some(w=>typeof w!=='string'||!w.trim()||Array.from(w).length>8)))throw Error('words must contain 1..3 short semantic groups <=8 Unicode characters');
  if(['depth_stack','orbit_gallery'].includes(shot.recipe)&&(!Array.isArray(shot.images)||shot.images.length<(shot.recipe==='orbit_gallery'?3:2)||shot.images.length>3))throw Error('stack needs 2..3 images; orbit needs exactly 3');
  if(shot.labels!==undefined&&(!Array.isArray(shot.labels)||shot.labels.length!==(shot.images?.length??0)||shot.labels.some(s=>typeof s!=='string'||Array.from(s).length>12)))throw Error('labels must match images, each <=12 Unicode characters');
  if(shot.recipe==='whip_bridge'&&(typeof shot.bridge!=='string'||!shot.bridge.trim()))throw Error('whip_bridge needs semantic bridge');
  const images=[shot.image,shot.beforeImage,shot.afterImage,...(shot.images||[])].filter(v=>v!==undefined);
  for(const img of images)if(typeof img!=='string'||!/^data:image\/(png|jpeg);base64,/.test(img)||shot.privacyApproved!==true)throw Error('advanced images require approved raster-redacted PNG/JPEG data URIs');
  if(shot.synthetic===false){
    if(shot.recipe==='hero_dolly'&&!shot.image)throw Error('real hero requires image');
    if(shot.recipe==='whip_bridge'&&!(shot.beforeImage&&shot.afterImage))throw Error('real bridge requires two images');
    if(shot.recipe==='focus_pull'&&!shot.image&&shot.contentLabel!=='文字信息卡')throw Error('imageless real focus must be explicitly labelled 文字信息卡');
  }
}
module.exports={ADVANCED_RECIPES,stateAt,windowFor,validateAdvancedShot};
