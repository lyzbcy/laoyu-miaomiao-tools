#!/usr/bin/env python3
"""Run the approved original video-use functions, with local Windows path/font compatibility only."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from verify_upstream import verify


def worker(root,kind,arguments):
    verified=verify('video-use',root)
    helper=Path(root)/'helpers'/('render.py' if kind=='render' else 'timeline_view.py')
    sys.path.insert(0,str(helper.parent))
    spec=importlib.util.spec_from_file_location('approved_video_use_'+kind,helper)
    original=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    if sys.platform=='win32':
        concrete=type(Path())
        class ForwardPath(concrete):
            def __str__(self): return super().__str__().replace('\\','/')
        original.Path=ForwardPath
        if kind=='timeline':
            original.FONT_CANDIDATES=['C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/arial.ttf']+original.FONT_CANDIDATES
    sys.argv=[str(helper)]+arguments
    original.main()


def invoke(root,kind,arguments,log):
    verified=verify('video-use',root)
    command=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker',kind,'--root',str(root),'--',*arguments]
    with Path(log).open('w',encoding='utf-8') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'original upstream {kind} failed; see {log}')
    return dict(verified,helper=kind,command=command,returncode=result.returncode,
                compatibility='Windows path strings to forward slash; installed font candidates; original source bytes unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',choices=['render','timeline'],required=True)
    parser.add_argument('--root',required=True)
    args,rest=parser.parse_known_args()
    if rest and rest[0]=='--': rest=rest[1:]
    worker(args.root,args.worker,rest)
