import React from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig} from 'remotion';
import model from './series-model.cjs';
const {METRICS,seriesDay,effectiveStyle}=model;
const looks={
 expressive:{bg:'#231142',ink:'#fff9f0',muted:'#d7cce7',accent:'#ffcc39',panel:'#392053',radius:22,border:'#775193',shadow:'7px 9px 0 #11081f'},
 fluent:{bg:'#edf3fa',ink:'#172333',muted:'#526479',accent:'#005fb8',panel:'#ffffffed',radius:12,border:'#d0dce8',shadow:'0 8px 24px #274c7015'},
 cupertino:{bg:'#f5f5f7',ink:'#1d1d1f',muted:'#626268',accent:'#0066cc',panel:'#ffffffed',radius:30,border:'#e1e1e6',shadow:'0 16px 50px #1717200c'}
};
export function SeriesBadge({shot}){
 const {width}=useVideoConfig();if(!shot.series)return null;
 const p=looks[effectiveStyle(shot)],day=seriesDay(shot.series.epochDate,shot.series.episodeDate);
 return <div style={{position:'absolute',top:0,left:0,width:720,height:1280,transform:`scale(${width/720})`,transformOrigin:'top left',pointerEvents:'none'}}>
  <div style={{position:'absolute',top:52,left:110,right:110,height:46,display:'flex',gap:9,justifyContent:'center',alignItems:'center',background:p.panel,border:`1px solid ${p.border}`,borderRadius:23,color:p.ink,fontFamily:'Microsoft YaHei,sans-serif',fontSize:23,fontWeight:650,boxShadow:p.shadow}}>
   <span style={{width:7,height:7,borderRadius:7,background:p.accent}}/><span>用AI剪视频的第 <strong style={{color:p.accent,fontSize:27}}>{day}</strong> 天</span>
  </div>
 </div>;
}
export function PreviousEpisode({shot}){
 const f=useCurrentFrame(),{fps,width}=useVideoConfig(),p=looks[effectiveStyle(shot)];
 const q=Math.min(1,Math.max(0,f/(fps*.6))),reveal=1-(1-q)**3,entries=Object.entries(shot.previous.metrics);
 const stamp=new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(shot.previous.snapshotAt));
 return <AbsoluteFill style={{background:p.bg,fontFamily:'Microsoft YaHei,sans-serif',overflow:'hidden'}}>
  <div style={{position:'absolute',width:720,height:1280,color:p.ink,transform:`scale(${width/720})`,transformOrigin:'top left'}}>
   <div style={{position:'absolute',top:168,left:48,right:48,opacity:reveal,transform:`translateY(${(1-reveal)*24}px)`}}>
    <div style={{color:p.accent,fontSize:23,fontWeight:650,letterSpacing:2}}>每一期，让工作流长一点</div>
    <div style={{fontSize:58,fontWeight:800,marginTop:18}}>上期数据</div>
    <div style={{display:'flex',gap:25,alignItems:'center',marginTop:32}}>
     <div style={{width:195,height:260,flexShrink:0,borderRadius:p.radius,overflow:'hidden',boxShadow:p.shadow,background:p.panel,border:`1px solid ${p.border}`}}>
      {shot.image?<img src={shot.image} style={{width:'100%',height:'100%',objectFit:'contain'}}/>:<div style={{padding:20,fontSize:30,lineHeight:1.5}}>原创合成封面<br/>上一期</div>}
     </div>
     <div style={{fontSize:31,fontWeight:650,lineHeight:1.45,overflowWrap:'anywhere'}}>{shot.previous.title}</div>
    </div>
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,marginTop:32}}>
     {entries.map(([k,m],i)=>{const r=Math.min(1,Math.max(0,(f-i*3)/(fps*.55)));return <div key={k} style={{padding:'18px 23px',borderRadius:p.radius,background:p.panel,border:`1px solid ${p.border}`,opacity:r,transform:`translateY(${(1-r)*12}px)`,boxShadow:p.shadow,gridColumn:i===0?'1 / -1':'auto'}}><div style={{fontSize:23,color:p.muted}}>{METRICS[k]}</div><div style={{fontSize:i===0?57:39,fontWeight:750,color:i===0?p.accent:p.ink,marginTop:6,lineHeight:1.1}}>{m.display}</div></div>;})}
    </div>
    <div style={{fontSize:21,color:p.muted,marginTop:24,lineHeight:1.5}}>抖音创作者平台 · 累计数据<br/>采集于 {stamp}（北京时间）{shot.synthetic===true?' · 合成测试数据':''}</div>
   </div>
  </div>
 </AbsoluteFill>;
}
