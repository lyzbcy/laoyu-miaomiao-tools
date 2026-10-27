#!/usr/bin/env python3
"""Synthetic acceptance invoking original shotcraft components and original video-use native EDL renderer."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image,ImageDraw,ImageFont
from edit_plan import build
from render_edl import run,probe,sha
from verify_upstream import verify
from upstream_native import invoke

HERE=Path(__file__).resolve().parent

def save(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def synthetic_ui(path):
    image=Image.new('RGB',(3840,2160),'#f3f5f8'); draw=ImageDraw.Draw(image)
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
    draw.rounded_rectangle((90,80,3750,2080),radius=45,fill='#ffffff',outline='#cfd7e0',width=5)
    draw.text((180,145),'生成的软件界面 · 非产品实测',font=font(78),fill='#15334a')
    draw.text((180,280),'本次只验证上游代码的相机与字幕组件',font=font(48),fill='#677a8c')
    for i,label in enumerate(['选择当前文件','执行整理操作','查看处理结果']):
        y=450+i*400
        draw.rounded_rectangle((190,y,3570,y+300),radius=30,fill=['#e9f1f7','#e6f3eb','#fff1df'][i])
        draw.text((270,y+80),f'{i+1:02}  {label}',font=font(74),fill='#183a51')
        draw.text((2400,y+95),'合成状态：就绪',font=font(52),fill='#27715d')
    image.save(path)

def produce(output,runtime,browser,shotcraft,video_use,fixture_project):
    output=Path(output).resolve()
    if output.exists(): raise FileExistsError('use a new upstream acceptance output directory')
    verified=[verify('video-shotcraft',shotcraft),verify('video-use',video_use)]
    fixture_path=Path(fixture_project).resolve(strict=True)
    fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    if any(s.get('privacy',{}).get('kind')!='synthetic' for s in fixture['sources']):
        raise ValueError('only generated fixture sources permitted in this acceptance entry')
    for source in fixture['sources']:
        if sha((fixture_path.parent/source['path']).resolve())!=source['sha256']:
            raise ValueError('fixture changed')
    output.mkdir(parents=True)
    public=output/'public';public.mkdir();synthetic_ui(public/'synthetic-ui.png')
    config={'runtime':str(Path(runtime).resolve()),'browserExecutable':str(Path(browser).resolve()),
            'shotcraftRoot':str(Path(shotcraft).resolve()),'output':str(output/'shots'),
            'publicDir':str(public),'synthetic':True}
    save(output/'shots-config.json',config)
    print('Calling original shotcraft components and original demo source...',flush=True)
    with (output/'remotion.log').open('w',encoding='utf-8') as log:
        subprocess.run(['node',str(HERE/'render_upstream_shots.cjs'),str(output/'shots-config.json')],check=True,stdout=log,stderr=subprocess.STDOUT)
    report=json.loads((output/'shots/upstream-render-report.json').read_text(encoding='utf-8'))
    concat=output/'shots-concat.txt'
    concat.write_text(''.join("file '"+Path(s['file']).as_posix().replace("'","'\\''")+"'\n" for s in report['shots']),encoding='utf-8')
    sequence=output/'sequence.mp4'
    run(['ffmpeg','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(sequence)])
    duration=float(probe(sequence)['format']['duration'])
    narration=fixture_path.parent/'narration.wav'
    source=output/'native-source.mkv'
    run(['ffmpeg','-v','error','-i',str(sequence),'-i',str(narration),'-map','0:v:0','-map','1:a:0','-af',f'apad,atrim=duration={duration}',
         '-c:v','copy','-c:a','pcm_s16le','-t',str(duration),str(source)])
    own=dict(fixture,sources=[dict(fixture['sources'][0],path=source.name,sha256=sha(source),duration_seconds=duration)])
    own.pop('bgm',None)
    edl=build(own)
    save(output/'source-project.json',own)
    edit=output/'edit';edit.mkdir();(edit/'transcripts').mkdir()
    sid=own['sources'][0]['id']
    transcript={'words':[dict(w,type='word') for w in own['words']]}
    save(edit/'transcripts'/f'{sid}.json',transcript)
    native={'sources':{sid:source.as_posix()},'ranges':[{'source':c['source'],'start':c['source_in'],'end':c['source_out'],'beat':'SYNTHETIC ACCEPTANCE'} for c in edl['clips']],
            'grade':None,'overlays':[],'total_duration_s':edl['duration_seconds']}
    save(edit/'edl.json',native)
    print('Calling original video-use render.py with native EDL and transcript schema...',flush=True)
    final=edit/'native-acceptance.mp4'
    calls=[invoke(video_use,'render',[str(edit/'edl.json'),'-o',str(final),'--draft','--build-subtitles','--fps','30'],output/'native-render.log')]
    run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'])
    info=probe(final);video=next(s for s in info['streams'] if s['codec_type']=='video')
    for i,cut in enumerate(edl['cut_reviews']):
        t=cut['time']
        calls.append(invoke(video_use,'timeline',[str(final),str(max(0,t-1.5)),str(min(float(info['format']['duration'])-.05,t+1.5)),
                     '--n-frames','6','-o',str(output/f'native-cut-{i+1}.png')],output/f'native-cut-{i+1}.log'))
    # Caption bounds are checked against actual output; subjective reading/listening stays separate.
    srt=(edit/'master.srt').read_text(encoding='utf-8')
    import re
    times=re.findall(r'(\d+):(\d+):(\d+),(\d+)',srt)
    seconds=[int(h)*3600+int(m)*60+int(s)+int(ms)/1000 for h,m,s,ms in times]
    if not seconds or min(seconds)<0 or max(seconds)>float(info['format']['duration'])+.05:
        raise ValueError('native caption bounds failed')
    result={'original_source_verification':verified,'shotcraft_actual_calls':report,'video_use_actual_calls':calls,
            'native_edl':str(edit/'edl.json'),'final':str(final),'dimensions':[video['width'],video['height']],
            'fps':video['avg_frame_rate'],'duration':float(info['format']['duration']),'expected_duration':edl['duration_seconds'],
            'duration_delta':float(info['format']['duration'])-edl['duration_seconds'],'full_decode_pass':True,
            'audio_present':any(s['codec_type']=='audio' for s in info['streams']),'subtitle_bounds_pass':True,
            'native_cut_views':len(edl['cut_reviews']),'mode':'upstream draft technical acceptance',
            'cloud_calls':0,'new_dependencies':[],'real_materials_read':False,'ear_listening':False,'real_aesthetic_gain':'unverified'}
    save(output/'acceptance.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('shotcraft_actual_calls','video_use_actual_calls')},ensure_ascii=False,indent=2),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('output','runtime','browser','shotcraft','video-use','fixture-project'): p.add_argument('--'+arg,required=True)
    a=p.parse_args();produce(a.output,a.runtime,a.browser,a.shotcraft,a.video_use,a.fixture_project)
