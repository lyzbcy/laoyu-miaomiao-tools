#!/usr/bin/env node
// Calls the user's already-installed Remotion. Never runs npm/npx or downloads a browser.
const fs=require('node:fs');
const path=require('node:path');
const {createRequire}=require('node:module');
const {MOTION_RECIPES,validateMotionShot}=require('../assets/remotion-software/motion-model.cjs');

async function main(){
  const configPath=path.resolve(process.argv[2]||'');
  const config=JSON.parse(fs.readFileSync(configPath,'utf8').replace(/^\uFEFF/,''));
  const runtime=path.resolve(config.runtime), browserExecutable=path.resolve(config.browserExecutable);
  if(!fs.existsSync(browserExecutable)||!fs.existsSync(path.join(runtime,'node_modules/remotion/package.json')))throw Error('existing runtime and browser paths required; no download fallback');
  const requireRuntime=createRequire(path.join(runtime,'package.json'));
  const {bundle}=requireRuntime('@remotion/bundler');
  const {selectComposition,renderMedia}=requireRuntime('@remotion/renderer');
  const version=requireRuntime('remotion/package.json').version;
  if(!Number.isInteger(config.fps)||config.fps<12||config.fps>60)throw Error('fps must be 12..60');
  if(!Number.isInteger(config.width)||config.width%2||config.width<360||!Number.isInteger(config.height)||config.height%2||config.width/config.height!==9/16)throw Error('current shots require even 9:16 dimensions >=360px wide');
  if(!Array.isArray(config.shots)||!config.shots.length)throw Error('shots required');
  const kinds=new Set(['before_after','detail_zoom','step_progression',...MOTION_RECIPES]);
  const ids=new Set();
  for(const shot of config.shots){
    if(!/^[a-zA-Z0-9_-]+$/.test(shot.id)||ids.has(shot.id)||!kinds.has(shot.recipe)||!Number.isInteger(shot.frames)||shot.frames<config.fps*2)throw Error('invalid shot id/recipe/duration');
    ids.add(shot.id);
    if(MOTION_RECIPES.has(shot.recipe))validateMotionShot(shot,config.fps);
    if(!MOTION_RECIPES.has(shot.recipe)&&shot.synthetic===false && (shot.recipe==='before_after' ? !(shot.beforeImage&&shot.afterImage) : !shot.image))throw Error('non-synthetic shots require explicit redacted images; generated UI cannot masquerade as real product evidence');
    for(const key of ['image','beforeImage','afterImage']){
      if(shot[key] && (!/^data:image\/(png|jpeg);base64,/.test(shot[key])||shot.privacyApproved!==true))throw Error('only explicitly approved, pre-raster-redacted local image data URIs accepted');
    }
  }
  const output=path.resolve(config.output);
  if(fs.existsSync(output))throw Error('use a new render output directory');
  fs.mkdirSync(output,{recursive:true});
  const nodeModules=path.join(runtime,'node_modules');
  const entry=path.join(__dirname,'../assets/remotion-software/entry.jsx');
  const serveUrl=await bundle({entryPoint:entry,rootDir:runtime,outDir:path.join(output,'bundle'),enableCaching:false,
    webpackOverride:(c)=>({...c,resolve:{...c.resolve,modules:[nodeModules,...(c.resolve?.modules||[])],alias:{...(c.resolve?.alias||{}),react:path.join(nodeModules,'react'),'react-dom':path.join(nodeModules,'react-dom'),remotion:path.join(nodeModules,'remotion')}}})});
  const reports=[];
  for(const shot of config.shots){
    const inputProps={shot,width:config.width,height:config.height,fps:config.fps};
    const options={serveUrl,browserExecutable,chromeMode:'chrome-for-testing',chromiumOptions:{headless:true},inputProps,logLevel:'error'};
    const composition=await selectComposition({...options,id:'SoftwareShot'});
    const outputLocation=path.join(output,shot.id+'.mp4');
    await renderMedia({...options,composition,codec:'h264',pixelFormat:'yuv420p',outputLocation,concurrency:1,crf:18,overwrite:false,isProduction:false,
      onBrowserDownload:()=>{throw Error('browser downloads prohibited; specify installed executable');}});
    reports.push({id:shot.id,recipe:shot.recipe,file:outputLocation,frames:shot.frames,width:composition.width,height:composition.height,fps:composition.fps});
    process.stdout.write(JSON.stringify({rendered:shot.id,file:outputLocation})+'\n');
  }
  fs.writeFileSync(path.join(output,'render-report.json'),JSON.stringify({engine:'Remotion',version,implementation:'self-authored components; not upstream shotcraft',browserExecutable,shots:reports},null,2));
}
main().catch(e=>{process.stderr.write(String(e.stack||e)+'\n');process.exitCode=1;});
