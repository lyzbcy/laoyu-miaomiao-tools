// Self-authored software shot components. No shotcraft source or branded media copied.
import React from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';
import {motionMapping} from './motion.jsx';
import {SeriesBadge,PreviousEpisode} from './series.jsx';
import {advancedMapping} from './advanced.jsx';

const color = {bg:'#091321', panel:'#16253a', line:'#30435b', ink:'#f5f8fc', muted:'#9eafc4', mint:'#65edc2', amber:'#ffcc75'};
const clamp = {extrapolateLeft:'clamp', extrapolateRight:'clamp'};
const Cursor = ({x,y,pressed=false}) => <div style={{position:'absolute',left:x,top:y,filter:'drop-shadow(0 3px 4px #0007)',transform:`scale(${pressed ? .88 : 1})`}}><svg width="42" height="48" viewBox="0 0 42 48"><path d="M3 3L33 26L20 29L15 43Z" fill="white" stroke="#101e30" strokeWidth="3"/></svg></div>;
const Badge = ({text,tone=color.mint}) => <div style={{color:tone,fontSize:24,fontWeight:650,letterSpacing:2}}>{text}</div>;

function UI({done=false,step=0,image=null}) {
  if (image) return <img src={image} style={{width:'100%',height:'100%',objectFit:'contain'}}/>;
  return <div style={{height:'100%',background:color.panel,borderRadius:22,overflow:'hidden',border:`2px solid ${color.line}`}}>
    <div style={{height:65,display:'flex',alignItems:'center',gap:10,padding:'0 24px',borderBottom:`1px solid ${color.line}`}}><i style={{width:10,height:10,borderRadius:9,background:color.mint}}/><span style={{fontSize:22,color:color.muted}}>示例工作台 · 原创合成界面</span></div>
    <div style={{padding:30}}><div style={{fontSize:28,fontWeight:700,marginBottom:24}}>项目文件</div>
      {[0,1,2].map((n)=><div key={n} style={{height:77,display:'flex',alignItems:'center',gap:16,marginBottom:16,padding:'0 18px',borderRadius:15,background:done||n<step?'#214a47':'#22334b',border:`1px solid ${done||n<step?'#487e6e':color.line}`}}>
        <div style={{width:30,height:30,borderRadius:9,background:done||n<step?color.mint:'#53647a',color:'#12352b',fontSize:24,textAlign:'center',lineHeight:'30px'}}>{done||n<step?'✓':''}</div>
        <div style={{fontSize:25}}>{done||n<step?['文档已归档','图片已归档','视频已归档'][n]:['文档_待整理','图片_待整理','视频_待整理'][n]}</div>
      </div>)}
      <div style={{marginTop:34,borderRadius:15,padding:'20px 24px',background:done?color.mint:'#4868e9',color:done?'#113a30':'white',fontSize:26,fontWeight:700,textAlign:'center'}}>{done?'整理结果已显示':'整理当前文件'}</div>
    </div>
  </div>;
}

function Frame({shot,children,caption}) {
  const {width,height}=useVideoConfig(); const f=useCurrentFrame();
  return <AbsoluteFill style={{background:color.bg,color:color.ink,fontFamily:'Microsoft YaHei, sans-serif',overflow:'hidden'}}>
    <div style={{position:'absolute',width:720,height:1280,transform:`scale(${width/720})`,transformOrigin:'top left'}}>
      <div style={{position:'absolute',left:54,top:shot.series?115:62,right:54,display:'flex',justifyContent:'space-between'}}><Badge text={shot.synthetic===false?(shot.contentLabel||'已脱敏界面演示'):'合成测试 · 非产品实测'}/><span style={{fontSize:23,color:color.muted}}>SOFTWARE SHOTS</span></div>
      <div style={{position:'absolute',top:shot.series?180:135,left:54,right:54,fontSize:52,fontWeight:800,lineHeight:1.25}}>{shot.title}</div>
      {children}
      <div style={{position:'absolute',left:54,right:54,bottom:106,fontSize:25,lineHeight:1.5,color:color.muted}}>{caption}</div>
      <div style={{position:'absolute',left:54,right:54,bottom:64,height:3,background:color.line}}><div style={{height:'100%',width:`${Math.min(100,f/(shot.frames-1)*100)}%`,background:color.mint}}/></div>
    </div>
  </AbsoluteFill>;
}

export function BeforeAfter({shot}) {
  const f=useCurrentFrame(),{fps}=useVideoConfig();
  const reveal=interpolate(f,[fps*.8,fps*2.1],[0,1],clamp);
  const x=interpolate(f,[fps*.15,fps*.7],[480,340],clamp);
  return <Frame shot={shot} caption={shot.note||'同一对象 → 触发操作 → 对照真实结果'}>
    <div style={{position:'absolute',left:54,top:290,width:612,height:650,boxShadow:'0 30px 90px #0007'}}>
      <UI image={shot.beforeImage}/><div style={{position:'absolute',inset:0,clipPath:`inset(0 ${(1-reveal)*100}% 0 0)`}}><UI done image={shot.afterImage}/></div>
      <div style={{position:'absolute',left:reveal*612-2,top:0,bottom:0,width:4,background:color.mint,opacity:reveal>0&&reveal<1?1:0}}/>
      <div style={{position:'absolute',top:-48,left:0,fontSize:25,color:reveal>.95?color.mint:color.amber}}>{reveal>.95?'后态：查看结果':'前态：定位问题'}</div>
      {f<fps*1.3&&<Cursor x={x} y={465} pressed={f>fps*.7}/>}
    </div>
    <div style={{position:'absolute',left:54,right:54,top:982,fontSize:35,color:color.mint,opacity:reveal}}>{shot.result||'变化落在同一区域，才能看清对比'}</div>
  </Frame>;
}

export function DetailZoom({shot}) {
  const f=useCurrentFrame(),{fps}=useVideoConfig();
  const phase=interpolate(f,[fps*.7,fps*1.5,fps*2.8,fps*3.7],[0,1,1,0],clamp);
  const scale=1+phase*.36;
  return <Frame shot={shot} caption={shot.note||'先交代位置，再读局部，最后回到上下文'}>
    <div style={{position:'absolute',left:54,top:290,width:612,height:650,overflow:'hidden',borderRadius:22,boxShadow:'0 30px 90px #0007'}}>
      <div style={{width:'100%',height:'100%',transform:`translateY(${-phase*105}px) scale(${scale})`,transformOrigin:'50% 60%'}}><UI done image={shot.image}/></div>
      <div style={{position:'absolute',left:27,right:27,top:phase?405:435,height:128,border:`3px solid ${color.mint}`,borderRadius:16,boxShadow:'0 0 0 1000px #0002',opacity:interpolate(f,[5,18],[0,1],clamp)}}/>
      <Cursor x={470-phase*50} y={490-phase*80}/>
    </div>
    <div style={{position:'absolute',left:54,top:985,fontSize:35,color:color.mint}}>{shot.result||'字号可读，操作关系也保留'}</div>
  </Frame>;
}

export function StepProgression({shot}) {
  const f=useCurrentFrame(),{fps}=useVideoConfig();
  const step=Math.min(3,Math.max(0,Math.floor((f-fps*.3)/(shot.frames/3)) + 1));
  const pulse=spring({frame:Math.max(0,f-Math.max(0,step-1)*Math.floor(shot.frames/3)),fps,config:{damping:18,stiffness:160}});
  return <Frame shot={shot} caption={shot.note||'每一步保留动作、反馈和下一步的因果'}>
    <div style={{position:'absolute',left:54,top:280,width:612,height:650,boxShadow:'0 30px 90px #0007'}}><UI step={step} done={step===3} image={shot.image}/><Cursor x={470} y={130+Math.min(2,Math.max(0,step-1))*93} pressed={pulse<.95}/></div>
    <div style={{position:'absolute',left:54,top:980,right:54,display:'flex',gap:16}}>{['选择对象','执行操作','确认结果'].map((name,i)=><div key={name} style={{flex:1,fontSize:25,borderRadius:15,padding:'16px 8px',textAlign:'center',background:i<step?'#245c4d':color.panel,color:i<step?color.mint:color.muted,transform:i===step-1?`scale(${.96+pulse*.04})`:'none'}}>{i+1} {name}</div>)}</div>
  </Frame>;
}

const mapping={before_after:BeforeAfter,detail_zoom:DetailZoom,step_progression:StepProgression,previous_episode:PreviousEpisode,...motionMapping,...advancedMapping};
function ShotRoot({shot}) { const Component=mapping[shot.recipe]; return <><Component shot={shot}/><SeriesBadge shot={shot}/></>; }
const defaultShot={recipe:'before_after',title:'先看前后，再讲原因',frames:120};
function Root(){return <><Composition id="SoftwareShot" component={ShotRoot} width={720} height={1280} fps={30} durationInFrames={120} defaultProps={{shot:defaultShot,width:720,height:1280,fps:30}} calculateMetadata={({props})=>({durationInFrames:props.shot.frames,width:props.width,height:props.height,fps:props.fps})}/><Composition id="SeriesBadge" component={SeriesBadge} width={720} height={1280} fps={30} durationInFrames={1} defaultProps={{shot:defaultShot,width:720,height:1280,fps:30}} calculateMetadata={({props})=>({width:props.width,height:props.height,fps:props.fps})}/></>;}
registerRoot(Root);
