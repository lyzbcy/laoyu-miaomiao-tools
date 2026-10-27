// Original expressive components; reference mechanisms only, no template code copied.
import React from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig,interpolate,spring} from 'remotion';
import model from './motion-model.cjs';
const {progress,schedule,opacityAt,chartScale,graphPoints,fillInk}=model;
const tones=['#ffcc39','#29e6db','#ff70c6','#ad9bff','#baff5a','#ff9559'];
const palettes={dark:{bg:'#231142',panel:'#392053',ink:'#fff9f0',muted:'#d7cce7',line:'#7e5c97',shadow:'#11081f'},light:{bg:'#fff4d9',panel:'#fffef8',ink:'#2c1744',muted:'#655476',line:'#c2a8ce',shadow:'#2c1744'}};
const designStyles={
 fluent:{bg:'#edf3fa',panel:'#ffffffed',ink:'#172333',muted:'#526479',line:'#cbd9e7',shadow:'#1d3b5510',accent:'#005fb8',tones:['#005fb8','#008575','#8764b8','#c239b3','#107c10','#ca5010'],radius:12,boxShadow:'0 8px 26px #234b7015',motion:'ease',isLight:true,tilt:0},
 cupertino:{bg:'#f5f5f7',panel:'#fffffff2',ink:'#1d1d1f',muted:'#626268',line:'#dedee5',shadow:'#1818200a',accent:'#0066cc',tones:['#0066cc','#00857a','#a33483','#6454b4','#387b13','#ad5000'],radius:30,boxShadow:'0 16px 50px #1717200c',motion:'soft',isLight:true,tilt:0}
};
// Bright fills stay vivid; text on the cream theme is darkened for contrast.
function textTone(p,c){
 if(p!==palettes.light&&!p.isLight)return c;
 const rgb=c.slice(1).match(/../g).map(v=>parseInt(v,16));
 const lum=v=>{const x=v/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;};
 const L=v=>v.map(lum).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
 while((L([255,244,217])+.05)/(L(rgb)+.05)<4.5)for(let i=0;i<3;i++)rgb[i]=Math.floor(rgb[i]*.85);
 return '#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join('');
}
const label=(v)=>v.toLocaleString('en-US',{maximumFractionDigits:12});
function pop(frame,start,fps,finish){const duration=Math.min(Math.ceil(fps*.6),finish===undefined?Infinity:Math.max(1,Math.floor(finish-start)));return frame<start?0:spring({frame:frame-start,fps,durationInFrames:duration,config:{damping:13,stiffness:185,mass:.65}});}
function Ink({children,style={}}){return <div style={{fontWeight:900,lineHeight:1.16,overflowWrap:'anywhere',...style}}>{children}</div>;}
function Shell({shot,children}){
 const f=useCurrentFrame(),{fps,width}=useVideoConfig(),p=designStyles[shot.visualStyle]||palettes[shot.theme||'dark'];
 const styledPop=(frame,start,rate,finish)=>{if(!p.motion)return pop(frame,start,rate,finish);const duration=Math.min(Math.round(rate*(p.motion==='soft'?.65:.45)),finish===undefined?Infinity:Math.max(1,finish-start));if(p.motion==='ease'){const q=Math.min(1,Math.max(0,(frame-start)/duration));return 1-(1-q)**3;}return frame<start?0:spring({frame:frame-start,fps:rate,durationInFrames:duration,config:{damping:24,stiffness:150,mass:.8}});};
 const title=styledPop(f,0,fps),a=shot.accent||p.accent||tones[0];
 return <AbsoluteFill style={{background:p===designStyles.cupertino?'radial-gradient(ellipse at 80% 20%,#ffffff 0%,#f5f5f7 70%)':p===designStyles.fluent?'linear-gradient(145deg,#f4f8fd,#e5eef8)':p.bg,fontFamily:'Microsoft YaHei, sans-serif',overflow:'hidden'}}>
  <div style={{position:'absolute',width:720,height:1280,transform:`scale(${width/720})`,transformOrigin:'top left',color:p.ink,opacity:opacityAt(f,shot,fps)}}>
   <div style={{position:'absolute',width:430,height:430,borderRadius:'50%',background:a,opacity:p.motion?.035:.09,right:-240,top:240}}/>
   <div style={{position:'absolute',width:400,height:400,border:'3px solid '+a,opacity:p.motion?.045:.14,borderRadius:90,left:-280,top:780,transform:'rotate(18deg)'}}/>
   <div style={{position:'absolute',left:48,right:48,top:shot.series?110:54,display:'flex',alignItems:'center',gap:12}}><span style={{width:14,height:14,borderRadius:5,background:a}}/><div style={{fontSize:shot.series?16:21,letterSpacing:1.5,color:p.muted}}>{shot.synthetic===false?(shot.contentLabel||'资料图解 · 请核对来源'):'原创合成样片 · 非产品实测'}</div></div>
   <div style={{position:'absolute',left:48,right:48,top:shot.series?158:124,transform:`translateY(${(1-title)*22}px) rotate(${(1-title)*(p.tilt??-3)}deg)`,opacity:Math.min(1,title)}}><Ink style={{fontSize:shot.title.length>24?36:shot.title.length>16?45:53}}>{shot.title}</Ink></div>
   {children({p,a,f,fps,tones:p.tones||tones,pop:styledPop})}
   <div style={{position:'absolute',left:48,right:48,top:1142,color:p.muted,fontSize:22,lineHeight:1.45}}>{shot.note||'看清关系，再理解结论。'}</div>
  </div>
 </AbsoluteFill>;
}
function Card({children,p,style={}}){return <div style={{background:p.panel,border:`2px solid ${p.line}`,borderRadius:p.radius??24,padding:22,boxShadow:p.boxShadow||`7px 9px 0 ${p.shadow}`,boxSizing:'border-box',...style}}>{children}</div>;}

export function MetricCompare({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),max=chartScale(shot).max,n=shot.items.length,row=Math.min(155,730/n),stagger=Math.min(9,(end-start)/(n+1));
  return <div style={{position:'absolute',left:48,right:48,top:290}}>
   <div style={{fontSize:22,color:p.muted,marginBottom:24}}>共用尺度 0—{label(max)} {shot.unit}</div>
   {shot.items.map((item,i)=>{const reveal=progress(f,start+i*stagger,end-(n-1-i)*stagger*.3),b=pop(f,start+i*stagger,fps,end),c=tones[i%tones.length];return <div key={i} style={{height:row,transform:`translateX(${(1-b)*(p.tilt===0?0:-30)}px)`,opacity:Math.min(1,b)}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',gap:14,marginBottom:14}}><Ink style={{fontSize:30}}>{item.label}</Ink><Ink style={{fontSize:35,color:textTone(p,c)}}>{label(item.value)} <span style={{fontSize:21,color:p.muted}}>{shot.unit}</span></Ink></div>
    <div style={{width:'100%',height:37,border:`2px solid ${p.line}`,borderRadius:12,overflow:'hidden'}}><div style={{width:`${item.value/max*reveal*100}%`,height:'100%',background:c,borderRadius:9}}/></div>
   </div>;})}
   {shot.result&&<Ink style={{fontSize:34,marginTop:20,color:textTone(p,a),opacity:progress(f,end-Math.round(fps*.3),end)}}>{shot.result}</Ink>}
  </div>;
 }}</Shell>;
}

export function TrendTrace({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),drawEnd=Math.max(start+1,end-Math.ceil(fps*.6)),q=Math.max(0,Math.min(1,(f-start)/(drawEnd-start))),points=graphPoints(shot),W=535,H=430,X=45,Y=65;
  const coords=points.map(v=>({x:X+v.x*W,y:Y+v.y*H})),d=coords.map((v,i)=>`${i?'L':'M'}${v.x},${v.y}`).join(' '),max=chartScale(shot).max;
  const hi=shot.highlightIndex??points.length-1;
  return <>
   <Card p={p} style={{position:'absolute',left:40,right:40,top:310,padding:16}}>
    <svg width="620" height="620" viewBox="0 0 620 620">
     {[0,.5,1].map(t=><g key={t}><line x1={X} y1={Y+(1-t)*H} x2={X+W} y2={Y+(1-t)*H} stroke={p.line} strokeDasharray={t===0?'0':'4 8'}/><text x={X} y={Y+(1-t)*H-12} fill={p.muted} fontSize="19">{label(t*max)} {shot.unit}</text></g>)}
     <path d={d} pathLength="1" stroke={a} strokeWidth="7" fill="none" strokeDasharray="1" strokeDashoffset={1-q} strokeLinecap="round"/>
     {coords.map((v,i)=>{const t=points[i].x;const born=q>=t;const s=born?pop(f,start+t*(drawEnd-start),fps,end):0;return <g key={i}>
      <circle cx={v.x} cy={v.y} r={Math.max(0,Math.min(1.12,s))*(i===hi?11:7)} fill={tones[i%tones.length]} stroke={p.bg} strokeWidth="3" opacity={born?1:0}/>
      <text x={v.x} y={560+(i%2)*28} fill={p.muted} textAnchor={i===0?'start':i===coords.length-1?'end':'middle'} fontSize="19">{points[i].label}</text>
      {(born&&i===hi)&&<text x={v.x} y={v.y-24} textAnchor={i===coords.length-1?'end':'middle'} fill={p.ink} fontSize="27" fontWeight="800">{label(points[i].value)} {shot.unit}</text>}
     </g>;})}
    </svg>
   </Card>
   <div style={{position:'absolute',left:48,right:48,top:985,fontSize:22,color:p.muted}}>点为实际样本；连线仅辅助阅读</div>
   {shot.result&&<Ink style={{position:'absolute',left:48,right:48,top:1040,fontSize:33,color:textTone(p,a),opacity:progress(f,end-Math.round(fps*.2),end)}}>{shot.result}</Ink>}
  </>;
 }}</Shell>;
}

export function TargetGap({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),q=progress(f,start,end),max=chartScale(shot).max,x=shot.target/max*570,gap=shot.actual-shot.target;
  return <>
   <div style={{position:'absolute',left:48,right:48,top:335,display:'flex',gap:18}}>{[['实际',shot.actual,tones[1]],['目标',shot.target,tones[2]]].map(([name,v,c])=><Card p={p} key={name} style={{flex:1,transform:`rotate(${p.tilt===0?0:name==='实际'?-2:2}deg)`}}><div style={{fontSize:24,color:p.muted}}>{name}</div><Ink style={{fontSize:56,color:textTone(p,c),marginTop:18}}>{label(v)}<span style={{fontSize:22}}> {shot.unit}</span></Ink></Card>)}</div>
   <Card p={p} style={{position:'absolute',left:48,right:48,top:620,padding:'60px 25px'}}>
    <div style={{position:'relative',width:570,height:65,borderRadius:16,background:p.bg,border:`2px solid ${p.line}`}}><div style={{height:'100%',width:`${shot.actual/max*q*100}%`,borderRadius:14,background:a}}/><div style={{position:'absolute',left:x,top:-25,height:115,width:4,background:tones[2]}}/></div>
    <div style={{display:'flex',justifyContent:'space-between',marginTop:24,fontSize:21,color:p.muted}}><span>0</span><span>{label(max)} {shot.unit}</span></div>
   </Card>
   <Ink style={{position:'absolute',left:48,right:48,top:940,fontSize:43,color:textTone(p,a),opacity:progress(f,end-Math.round(fps*.2),end)}}>{gap===0?'刚好达到目标':gap>0?`高于目标 ${label(gap)} ${shot.unit}`:`距目标 ${label(-gap)} ${shot.unit}`}</Ink>
  </>;
 }}</Shell>;
}

export function EvidenceFocus({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),count=shot.items.length,row=Math.min(180,710/count),fi=shot.focusIndex??0;
  const focusStart=shot.focusStartFrame??end,focus=shot.reduceDistractions===true?progress(f,focusStart,Math.min(shot.frames-1,focusStart+Math.round(fps*.6))):0;
  const claimAt=shot.claimStartFrame??end;
  const afterCards=280+row*count,promptTop=afterCards+20,claimTop=shot.prompt?promptTop+42:afterCards+36;
  return <>
   <div style={{position:'absolute',left:48,right:48,top:280}}>{shot.items.map((item,i)=>{const b=pop(f,start+i*7,fps,end),chosen=i===fi;return <Card key={i} p={p} style={{height:row-16,marginBottom:16,padding:count===5?16:20,opacity:Math.min(1,b)*(chosen?1:1-focus*.84),transform:`translateX(${(1-b)*42+(chosen?0:focus*15)}px) rotate(${(1-b)*(p.tilt===0?0:(i%2?3:-3))}deg)`,borderColor:chosen&&focus>0?a:p.line}}><div style={{display:'flex',gap:14,alignItems:'center'}}><span style={{fontSize:26,fontWeight:900,color:textTone(p,tones[i%tones.length])}}>0{i+1}</span><Ink style={{fontSize:count===5?26:29}}>{item.label}</Ink></div><div style={{marginTop:8,fontSize:count===5?20:22,lineHeight:1.35,color:p.muted}}>{item.detail}</div></Card>;})}</div>
   {shot.prompt&&<div style={{position:'absolute',top:promptTop,left:48,right:48,fontSize:25,color:p.muted}}>{shot.prompt}</div>}
   {shot.result&&<Ink style={{position:'absolute',top:claimTop,left:48,right:48,fontSize:count>=4?32:39,color:textTone(p,a),opacity:progress(f,claimAt,Math.min(shot.frames-1,claimAt+Math.round(fps*.35)))}}>{shot.result}</Ink>}
  </>;
 }}</Shell>;
}

export function CausalFlow({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),count=shot.steps.length,h=Math.min(180,760/count),gap=(end-start)/count;
  return <div style={{position:'absolute',left:48,right:48,top:278}}>{shot.steps.map((step,i)=>{const b=pop(f,start+i*gap,fps,end),q=progress(f,start+i*gap,Math.min(end,start+(i+1)*gap));return <div key={i} style={{height:h,position:'relative',opacity:Math.min(1,b),transform:`translateY(${(1-b)*25}px)`}}>
   <div style={{position:'absolute',left:0,top:18,width:52,height:52,borderRadius:16,background:tones[i%tones.length],color:fillInk(tones[i%tones.length]),fontSize:28,fontWeight:900,textAlign:'center',lineHeight:'52px',transform:`rotate(${(1-b)*(p.tilt===0?0:-30)}deg)`}}>{i+1}</div>
   <Card p={p} style={{marginLeft:75,padding:count===5?12:18,height:h-36}}><Ink style={{fontSize:count===5?25:30}}>{step.label}</Ink><div style={{fontSize:count===5?20:22,lineHeight:1.35,color:p.muted,marginTop:8}}>{step.detail}</div></Card>
   {i<count-1&&<div style={{position:'absolute',left:24,top:76,height:(h-62)*q,width:4,background:tones[i%tones.length]}}/>}
  </div>;})}</div>;
 }}</Shell>;
}

export function TaskRouter({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),count=shot.routes.length,row=Math.min(195,740/count),total=row*count;
  return <>
   <svg style={{position:'absolute',left:0,top:290}} width="720" height="760">
    {shot.routes.map((route,i)=>{const q=progress(f,start+i*8,end-(count-1-i)*5);const y=75+i*row+row/2;return <path key={i} d={`M170,${75+total/2} C230,${75+total/2} 210,${y} 290,${y}`} pathLength="1" stroke={tones[i%tones.length]} strokeWidth="5" fill="none" strokeDasharray="1" strokeDashoffset={1-q}/>;})}
   </svg>
   <Card p={p} style={{position:'absolute',left:45,top:290+75+total/2-65,width:145,minHeight:130,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',borderColor:a,padding:12}}><Ink style={{fontSize:29}}>{shot.origin}</Ink></Card>
   <div style={{position:'absolute',left:290,right:45,top:365}}>{shot.routes.map((route,i)=>{const b=pop(f,start+i*8,fps,end);return <Card key={i} p={p} style={{height:row-20,marginBottom:20,padding:18,opacity:Math.min(1,b),transform:`translateX(${(1-b)*42}px)`,borderColor:tones[i%tones.length]}}><Ink style={{fontSize:route.label.length>12?25:30,color:textTone(p,tones[i%tones.length])}}>{route.label}</Ink><div style={{fontSize:22,marginTop:8,lineHeight:1.35,color:p.muted}}>{route.detail}</div></Card>;})}</div>
  </>;
 }}</Shell>;
}

export function ClaimReveal({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),b=pop(f,start,fps,end),q=progress(f,start,end);
  return <>
   <div style={{position:'absolute',left:48,right:48,top:360,transform:`rotate(${(1-b)*(p.tilt===0?0:-7)}deg) scale(${.92+.08*b})`,opacity:Math.min(1,b)}}>
    <div style={{display:'inline-block',padding:'10px 18px',borderRadius:12,background:tones[2],fontSize:24,fontWeight:900,color:fillInk(tones[2]),transform:p.tilt===0?'none':'rotate(-4deg)'}}>{shot.kicker||'重点在这里'}</div>
    <Ink style={{fontSize:shot.claim.length>44?40:shot.claim.length>28?49:64,marginTop:35,lineHeight:1.3}}>{shot.claim}</Ink>
    <div style={{height:12,background:a,borderRadius:8,marginTop:26,width:`${q*100}%`}}/>
   </div>
   {shot.support&&<div style={{position:'absolute',left:48,right:48,top:850,fontSize:30,lineHeight:1.55,color:p.muted,opacity:progress(f,end-Math.round(fps*.3),end)}}>{shot.support}</div>}
  </>;
 }}</Shell>;
}

export function SpotlightROI({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),q=progress(f,start,end),r=shot.roi,W=624,H=665,X=r.x*W,Y=r.y*H,RW=r.w*W,RH=r.h*H;
  return <>
   <div style={{position:'absolute',left:48,top:300,width:W,height:H,overflow:'hidden',borderRadius:24,border:`2px solid ${p.line}`}}>
    {shot.image?<img src={shot.image} style={{width:'100%',height:'100%',objectFit:'contain',background:p.panel}}/>:<div style={{background:p.panel,height:'100%',padding:28,boxSizing:'border-box'}}><div style={{fontSize:23,color:p.muted,marginBottom:35}}>原创合成界面</div>{['选择文件','执行操作','查看结果'].map((t,i)=><div key={t} style={{padding:28,marginBottom:22,border:`2px solid ${p.line}`,borderRadius:18,fontSize:30,background:i===1?(p.isLight?'#e2edff':'#7c54ae'):p.bg}}>{t}</div>)}</div>}
    <svg style={{position:'absolute',inset:0}} width={W} height={H}><defs><mask id="focus-hole"><rect width={W} height={H} fill="white"/><rect x={X} y={Y} width={RW} height={RH} rx="18" fill="black"/></mask></defs><rect width={W} height={H} fill="#12051e" opacity={q*.8} mask="url(#focus-hole)"/><rect x={X} y={Y} width={RW} height={RH} rx="18" fill="none" stroke={a} strokeWidth="5" opacity={q}/></svg>
   </div>
   {shot.result&&<Ink style={{position:'absolute',top:1010,left:48,right:48,fontSize:35,color:textTone(p,a),opacity:q}}>{shot.result}</Ink>}
  </>;
 }}</Shell>;
}

export function MatchTransition({shot}){
 return <Shell shot={shot}>{({p,a,f,fps,tones,pop})=>{
  const {start,end}=schedule(shot,fps),q=progress(f,start,end),b=pop(f,start,fps,end);
  return <>
   <Card p={p} style={{position:'absolute',left:48,right:48,top:330,minHeight:260,opacity:1-q,transform:`translateY(${-q*70}px)`}}><div style={{fontSize:23,color:p.muted}}>上一件事</div><Ink style={{fontSize:48,marginTop:28}}>{shot.from}</Ink></Card>
   <Card p={p} style={{position:'absolute',left:48,right:48,top:730,minHeight:260,opacity:q,transform:`translateY(${(1-q)*70}px)`}}><div style={{fontSize:23,color:p.muted}}>顺着它继续</div><Ink style={{fontSize:48,marginTop:28}}>{shot.to}</Ink></Card>
   <div style={{position:'absolute',left:120+q*70,top:510+q*70,width:440-q*140,minHeight:120,borderRadius:24,padding:20,boxSizing:'border-box',background:a,color:fillInk(a),textAlign:'center',boxShadow:`8px 10px 0 ${p.shadow}`,transform:`rotate(${(1-q)*-6}deg) scale(${.94+.06*b})`,display:'flex',alignItems:'center',justifyContent:'center'}}><Ink style={{fontSize:36}}>{shot.bridge}</Ink></div>
  </>;
 }}</Shell>;
}

export const motionMapping={metric_compare:MetricCompare,trend_trace:TrendTrace,target_gap:TargetGap,evidence_focus:EvidenceFocus,causal_flow:CausalFlow,task_router:TaskRouter,claim_reveal:ClaimReveal,spotlight_roi:SpotlightROI,match_transition:MatchTransition};
