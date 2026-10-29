"""Evidence-backed task list for a full production run; no media or network calls."""
from pathlib import Path
import argparse, hashlib, json

BASE=['requirements','hook','storyboard','motion_selection','representative_motion','audio','cover_design','media_qa','handoff_or_closeout']


def save(path,data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def plan(path,series=False,image_cover=False):
    path=Path(path)
    if path.exists():raise ValueError('Workflow exists; resume it instead of resetting evidence')
    steps=list(BASE)
    if series:steps.insert(2,'series_context')
    if image_cover:steps.insert(steps.index('media_qa'),'cover_generation')
    data={'schema':1,'series':series,'image_cover':image_cover,'steps':{name:{'status':'pending'} for name in steps}}
    save(path,data);return data


def record(path,step,evidence=None,blocked=None):
    path=Path(path);data=json.loads(path.read_text(encoding='utf8'))
    if step not in data['steps']:raise ValueError('Step not in the agreed workflow')
    if bool(evidence)==bool(blocked):raise ValueError('Supply one evidence file or a blocking reason')
    if blocked:data['steps'][step]={'status':'blocked','reason':blocked}
    else:
        evidence=Path(evidence).resolve()
        if not evidence.is_file():raise ValueError('Evidence file missing')
        data['steps'][step]={'status':'done','evidence':str(evidence),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}
    save(path,data);return data['steps'][step]


def audit(path):
    data=json.loads(Path(path).read_text(encoding='utf8'))
    steps=data.get('steps',{})
    required=set(BASE)
    if data.get('series'):required.add('series_context')
    if data.get('image_cover'):required.add('cover_generation')
    if data.get('schema')!=1 or not required.issubset(steps):raise ValueError('Incomplete workflow schema')
    remaining={}
    for name,item in steps.items():
        if item.get('status')!='done':remaining[name]=item.get('reason') or 'pending';continue
        evidence=Path(item.get('evidence',''))
        if not evidence.is_file():remaining[name]='evidence_missing'
        elif hashlib.sha256(evidence.read_bytes()).hexdigest()!=item.get('sha256'):remaining[name]='evidence_changed'
    return {'complete':not remaining,'remaining':remaining}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','record','audit']);parser.add_argument('workflow',type=Path)
    parser.add_argument('--series',action='store_true');parser.add_argument('--image-cover',action='store_true')
    parser.add_argument('--step');parser.add_argument('--evidence',type=Path);parser.add_argument('--blocked')
    args=parser.parse_args()
    try:
        if args.action=='init':result=plan(args.workflow,args.series,args.image_cover)
        elif args.action=='record':result=record(args.workflow,args.step,args.evidence,args.blocked)
        else:result=audit(args.workflow)
        print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
        if args.action=='audit' and not result['complete']:parser.exit(1)
    except (ValueError,OSError,KeyError) as error:parser.exit(2,str(error)+'\n')
