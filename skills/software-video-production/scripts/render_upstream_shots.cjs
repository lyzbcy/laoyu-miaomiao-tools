#!/usr/bin/env node
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {createRequire}=require('node:module');
async function main(){
 const c=JSON.parse(fs.readFileSync(path.resolve(process.argv[2]),'utf8'));
 if(c.synthetic!==true)throw Error('this acceptance entry accepts generated assets only');
 const root=path.resolve(c.shotcraftRoot),p=JSON.parse(fs.readFileSync(path.join(__dirname,'../assets/upstream-pins.json'),'utf8'))['video-shotcraft'];
 for(const [relative,expected] of Object.entries(p.installed_files)){
   const file=path.resolve(root,relative);if(!file.startsWith(root+path.sep)||fs.lstatSync(file).isSymbolicLink())throw Error('upstream path escape');
   if(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==expected)throw Error('upstream source changed: '+relative);
 }
 const runtime=path.resolve(c.runtime),browserExecutable=path.resolve(c.browserExecutable),out=path.resolve(c.output);
 if(!fs.existsSync(browserExecutable)||fs.existsSync(out))throw Error('existing browser and new output directory required');
 fs.mkdirSync(out,{recursive:true});
 const req=createRequire(path.join(runtime,'package.json')),{bundle}=req('@remotion/bundler'),{selectComposition,renderMedia}=req('@remotion/renderer');
 const modules=path.join(runtime,'node_modules');
 const serveUrl=await bundle({entryPoint:path.join(__dirname,'../assets/upstream-entry.tsx'),rootDir:runtime,publicDir:path.resolve(c.publicDir),outDir:path.join(out,'bundle'),enableCaching:false,webpackOverride:(x)=>({...x,resolve:{...x.resolve,modules:[modules,...(x.resolve?.modules||[])],alias:{...(x.resolve?.alias||{}),'@approved-shotcraft':root,react:path.join(modules,'react'),'react-dom':path.join(modules,'react-dom'),remotion:path.join(modules,'remotion')}}})});
 const reports=[];
 for(const id of ['UpstreamComparison','UpstreamCamera','UpstreamSteps']){
   const options={serveUrl,browserExecutable,chromeMode:'chrome-for-testing',chromiumOptions:{headless:true},logLevel:'error'};
   const composition=await selectComposition({...options,id});const file=path.join(out,id+'.mp4');
   await renderMedia({...options,composition,codec:'h264',outputLocation:file,pixelFormat:'yuv420p',concurrency:1,scale:2/3,crf:18,overwrite:false,isProduction:false});
   reports.push({id,file,frames:composition.durationInFrames,width:1280,height:720,fps:30,original_components:id==='UpstreamCamera'?['PageCam','Caption']:id==='UpstreamSteps'?['BeatStepListThemeCycle','DigitRoll']:['BeforeAfterSliderScrub']});
   process.stdout.write(JSON.stringify({rendered:id,file})+'\n');
 }
 fs.writeFileSync(path.join(out,'upstream-render-report.json'),JSON.stringify({upstream:p.repo,commit:p.commit,original_source_hashes_verified:true,remotion:req('remotion/package.json').version,shots:reports},null,2));
}
main().catch(e=>{process.stderr.write(String(e.stack||e)+'\n');process.exitCode=1;});
