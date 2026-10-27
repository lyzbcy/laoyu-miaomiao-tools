// Local assembly only. Imports below execute the byte-verified upstream components unchanged.
import React from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame} from 'remotion';
import {PageCam} from '@approved-shotcraft/assets/lib/PageCam';
import {Caption} from '@approved-shotcraft/assets/lib/Caption';
import {DigitRoll} from '@approved-shotcraft/assets/lib/DigitRoll';
import {BeforeAfterSliderScrub} from '@approved-shotcraft/demos/data/before-after-slider-scrub/BeforeAfterSliderScrub';
import {BeatStepListThemeCycle} from '@approved-shotcraft/demos/rhythm/beat-step-list-theme-cycle/BeatStepListThemeCycle';

const Mark=()=> <div style={{position:'absolute',top:24,left:42,zIndex:100,fontFamily:'Microsoft YaHei',fontSize:25,padding:'9px 18px',borderRadius:8,background:'#071726e8',color:'#fff'}}>原版组件合成验收 · 非产品实测</div>;
const LargeCaption=({text}:{text:string})=><div style={{position:'absolute',inset:0,transform:'scale(2.6)',transformOrigin:'center bottom',pointerEvents:'none'}}><Caption text={text} duration={180} bottom={28}/></div>;
function Camera(){return <AbsoluteFill><PageCam src="synthetic-ui.png" pageH={1080} keys={[
  {frame:0,cx:960,cy:540,zoom:1,rotX:0,rotY:0,rotZ:0},
  {frame:28,cx:960,cy:540,zoom:1,rotX:0,rotY:0,rotZ:0},
  {frame:70,cx:1360,cy:630,zoom:1.65,rotX:5,rotY:-4,rotZ:-1},
  {frame:120,cx:1360,cy:630,zoom:1.65,rotX:5,rotY:-4,rotZ:-1},
  {frame:165,cx:960,cy:540,zoom:1,rotX:0,rotY:0,rotZ:0},
  {frame:180,cx:960,cy:540,zoom:1,rotX:0,rotY:0,rotZ:0}
]}><div style={{position:'absolute',left:1120,top:510,width:510,height:200,border:'5px solid #bb6834',borderRadius:18,boxSizing:'border-box'}}/></PageCam><LargeCaption text="原版 PageCam：定位、推进、回到上下文"/><Mark/></AbsoluteFill>}
function Comparison(){return <AbsoluteFill><BeforeAfterSliderScrub/><Mark/></AbsoluteFill>}
function Steps(){return <AbsoluteFill><BeatStepListThemeCycle/><div style={{position:'absolute',right:62,top:110,padding:14,background:'#051225dd',borderRadius:15}}><DigitRoll value="03" delay={15} fontSize={66} color="#fff"/></div><Mark/></AbsoluteFill>}
function Root(){return <><Composition id="UpstreamComparison" component={Comparison} width={1920} height={1080} fps={30} durationInFrames={180}/><Composition id="UpstreamCamera" component={Camera} width={1920} height={1080} fps={30} durationInFrames={180}/><Composition id="UpstreamSteps" component={Steps} width={1920} height={1080} fps={30} durationInFrames={180}/></>}
registerRoot(Root);
