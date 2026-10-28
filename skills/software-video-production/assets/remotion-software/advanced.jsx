// Original adaptations of documented motion mechanisms. Sources: docs/advanced-cases.md.
import React from 'react';
import {AbsoluteFill,Img,useCurrentFrame,useVideoConfig} from 'remotion';
import {stateAt,windowFor} from './advanced-model.cjs';
const clamp=v=>Math.max(0,Math.min(1,v));
const ease=v=>{const t=clamp(v);return t*t*(3-2*t);};
function Screen({image,label='原创合成界面',accent='#79b8ff'}){
  return <div style={{width:'100%',height:'100%',borderRadius:20,overflow:'hidden',background:'#182234',border:'1px solid #ffffff30',boxShadow:'0 28px 75px #0007',position:'relative'}}>
    {image?<Img src={image} style={{width:'100%',height:'100%',objectFit:'contain'}}/>:<div style={{padding:28,color:'#edf4ff'}}><div style={{fontSize:24,marginBottom:30}}>{label}</div><div style={{height:10,width:'35%',background:accent,borderRadius:8,marginBottom:36}}/>{[80,60,92].map((w,i)=><div key={i} style={{height:54,marginBottom:20,borderRadius:12,background:'#273952',display:'flex',alignItems:'center',padding:15}}><div style={{width:w+'%',height:9,background:'#647c99',borderRadius:8}}/></div>)}<div style={{height:62,borderRadius:12,background:accent,color:'#101827',fontSize:22,display:'grid',placeItems:'center'}}>示意状态 · 非操作证据</div></div>}
  </div>;
}
function Stage({shot,children}){
 const {width}=useVideoConfig();const dark=shot.visualStyle==='expressive',accent=shot.accent||(dark?'#79b8ff':'#2868d9');
 return <AbsoluteFill style={{'--stage-bg':dark?'#080e1a':shot.visualStyle==='fluent'?'#edf3fc':'#f7f8fb','--stage-ink':dark?'#f4f7ff':'#111a2d','--stage-muted':dark?'#b1c0d8':'#526078','--stage-accent':accent,overflow:'hidden',background:'var(--stage-bg)',fontFamily:'Microsoft YaHei, sans-serif',color:'var(--stage-ink)'}}><div style={{width:720,height:1280,transform:`scale(${width/720})`,transformOrigin:'top left',position:'absolute',background:`radial-gradient(ellipse at 50% 50%,${accent}16,transparent 65%)`}}>
 <div style={{position:'absolute',left:54,right:54,top:shot.series?150:72,fontSize:22,color:'var(--stage-muted)'}}>{shot.synthetic===false?(shot.contentLabel||'已脱敏界面展示'):'原创合成示例 · 非产品实测'}</div>
 <div style={{position:'absolute',left:54,right:54,top:shot.series?205:145,fontSize:44,fontWeight:700,lineHeight:1.3,overflowWrap:'anywhere'}}>{shot.title}</div>
 {children}<div style={{position:'absolute',left:54,right:54,bottom:100,color:'var(--stage-muted)',fontSize:25,lineHeight:1.45}}>{shot.recipe==='focus_pull'&&!shot.image?'':shot.subtitle||''}</div></div></AbsoluteFill>;
}
function Hero({shot}){
 const frame=useCurrentFrame(),{fps}=useVideoConfig(),s=stateAt(shot,frame,fps);
 return <Stage shot={shot}><div style={{position:'absolute',left:62,top:350,width:596,height:580,perspective:1400}}><div style={{width:'100%',height:'100%',transform:`translateY(${(1-s.p)*80}px) rotateX(${s.rotateX}deg) rotateY(${s.rotateY}deg) scale(${.88+.12*s.p})`,transformStyle:'preserve-3d'}}><Screen image={shot.image} accent={shot.accent}/></div></div></Stage>;
}
function Stack({shot}){
 const frame=useCurrentFrame(),{fps}=useVideoConfig(),{p}=stateAt(shot,frame,fps),images=shot.images;
 return <Stage shot={shot}><div style={{position:'absolute',left:60,top:360,width:600,height:590,perspective:1600}}>{[...images.keys()].reverse().map(i=><div key={i} style={{position:'absolute',inset:0,zIndex:images.length-i,opacity:i===0?1:1-p,transform:`translateX(${i*(1-p)*52}px) translateY(${-i*(1-p)*45}px) translateZ(${-i*70}px) rotateY(${(1-p)*-12}deg) scale(${i===0?.88+.12*p:1})`}}><Screen image={images[i]} label={shot.labels?.[i]} accent={shot.accent}/></div>)}</div></Stage>;
}
function Kinetic({shot}){
 const f=useCurrentFrame(),{fps}=useVideoConfig(),{start,end}=windowFor(shot,fps),n=shot.words.length;
 return <Stage shot={shot}><div style={{position:'absolute',left:54,right:54,top:425,display:'grid',gap:18}}>{shot.words.map((word,i)=>{const delay=start+i*(end-start)*.45/Math.max(1,n-1),p=ease((f-delay)/((end-start)*.55));return <div key={i} style={{overflow:'hidden',padding:'4px 0'}}><div style={{fontSize:word.length>5?62:86,fontWeight:800,lineHeight:1.25,letterSpacing:-2,color:i===n-1?'var(--stage-accent)':'var(--stage-ink)',transform:`translateY(${(1-p)*125}%)`}}>{word}</div></div>;})}</div></Stage>;
}
function Whip({shot}){
 const f=useCurrentFrame(),{fps}=useVideoConfig(),s=stateAt(shot,f,fps);
 return <Stage shot={shot}><div style={{position:'absolute',left:0,right:0,top:350,height:620,overflow:'hidden'}}>{[shot.beforeImage,shot.afterImage].map((image,i)=><div key={i} style={{position:'absolute',inset:0,transform:`translateX(${(i-s.p)*100}%)`,background:'var(--stage-bg)'}}><div style={{position:'absolute',left:54,right:54,top:15,bottom:15,filter:`blur(${s.blur}px)`}}><Screen image={image} label={i?'下一视图 · 合成示意':'当前视图 · 合成示意'} accent={shot.accent}/></div></div>)}</div><div style={{position:'absolute',left:54,right:54,top:1000,fontSize:25,color:'var(--stage-muted)'}}>{shot.bridge}</div></Stage>;
}
function Focus({shot}){
 const f=useCurrentFrame(),{fps}=useVideoConfig(),s=stateAt(shot,f,fps);
 return <Stage shot={shot}><div style={{position:'absolute',left:60,right:60,top:360,height:580,filter:`blur(${s.blur}px)`,transform:`scale(${s.scale})`}}>{shot.image?<Screen image={shot.image}/>:<div style={{height:'100%',display:'grid',placeItems:'center',fontSize:68,fontWeight:800,textAlign:'center',color:'var(--stage-accent)',padding:25,overflowWrap:'anywhere'}}>{shot.subtitle||shot.title}</div>}</div></Stage>;
}
function Orbit({shot}){
 const f=useCurrentFrame(),{fps}=useVideoConfig(),{p}=stateAt(shot,f,fps);
 // An explicit three-card arc converges on the front card. No autonomous looping.
 const angle=-62+62*p;
 return <Stage shot={shot}><div style={{position:'absolute',left:0,right:0,top:365,height:600,perspective:1300}}><div style={{position:'absolute',left:70,top:35,width:580,height:540,transformStyle:'preserve-3d'}}>{[2,1,0].map(i=>{const theta=(angle+(i===1?-72:i===2?72:0))*Math.PI/180;const x=Math.sin(theta)*170*(1-p),z=(Math.cos(theta)-1)*330;return <div key={i} style={{position:'absolute',inset:0,transform:`translateX(${x}px) translateZ(${z}px) rotateY(${-theta*180/Math.PI}deg) scale(${i===0?.73+.27*p:.73})`,backfaceVisibility:'hidden',opacity:i===0?1:1-p}}><Screen image={shot.images[i]} label={shot.labels?.[i]} accent={shot.accent}/></div>;})}</div></div></Stage>;
}
export const advancedMapping={hero_dolly:Hero,depth_stack:Stack,kinetic_mask:Kinetic,whip_bridge:Whip,focus_pull:Focus,orbit_gallery:Orbit};
