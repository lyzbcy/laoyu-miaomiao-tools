"""Persistent closeout gates. Records evidence; never posts, deletes, or wakes tasks."""
from pathlib import Path
import argparse, hashlib, json, re
from urllib.parse import urlparse

STATES={
    'delivery':{'pending','confirmed'},
    'experience_review':{'pending','valuable','not_valuable'},
    'contribution':{'pending','awaiting_consent','approved','submitted','declined','not_needed'},
    'archive':{'pending','verified'},
    'cleanup':{'pending','awaiting_consent','approved','cleaned','retained'},
    'contribution_cleanup':{'pending','cleaned','not_created'},
}
TERMINAL={
    'delivery':{'confirmed'},'experience_review':{'valuable','not_valuable'},
    'contribution':{'submitted','declined','not_needed'},'archive':{'verified'},
    'cleanup':{'cleaned','retained'},'contribution_cleanup':{'cleaned','not_created'},
}


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,data):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    temporary.replace(path)


def plan(path):
    path=Path(path)
    if path.exists():raise ValueError('Closeout ledger exists; resume instead of resetting it')
    data={'schema':1,'tasks':{name:{'status':'pending'} for name in STATES},'history':[]}
    save(path,data);return data


def proof(path):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('Evidence file missing')
    return {'path':str(path),'sha256':digest(path)}


def proof_valid(item):
    path=Path(item.get('path',''))
    return path.is_file() and digest(path)==item.get('sha256')


def validate_special(task,status,evidence):
    if task=='archive' and status=='verified':
        files=load(evidence).get('files',[])
        if not files or not all(proof_valid(item) for item in files):
            raise ValueError('Archive index must verify actual preserved files and hashes')
    if task in ('cleanup','contribution_cleanup') and status=='cleaned':
        deleted=load(evidence).get('deleted',[])
        if not deleted or any(Path(path).exists() for path in deleted):
            raise ValueError('Cleanup receipt must list paths that are actually absent')


def record(path,task,status,evidence,reason='',url=None):
    data=load(path)
    if task not in STATES or status not in STATES[task] or status=='pending':
        raise ValueError('Invalid closeout task/state')
    item={'status':status,'evidence':proof(evidence),'reason':reason}
    old=data['tasks'][task]
    if task=='contribution':
        if status=='approved':item['authorization']=item['evidence']
        elif status=='submitted':
            authorization=old.get('authorization',{})
            parsed=urlparse(url or '')
            if not proof_valid(authorization):raise ValueError('PR consent evidence required before submission receipt')
            if parsed.hostname!='github.com' or not re.fullmatch(r'/[^/]+/[^/]+/pull/[1-9][0-9]*',parsed.path):
                raise ValueError('Actual GitHub PR URL required')
            item.update(authorization=authorization,url=url)
        elif status=='not_needed' and data['tasks']['experience_review']['status']!='not_valuable':
            raise ValueError('Contribution cannot be skipped without the experience assessment')
    if task=='cleanup':
        if status=='approved':item['authorization']=item['evidence']
        elif status=='cleaned':
            authorization=old.get('authorization',{})
            if not proof_valid(authorization):raise ValueError('Separate cleanup consent evidence required')
            item['authorization']=authorization
    validate_special(task,status,evidence)
    data['tasks'][task]=item
    data['history'].append({'task':task,**item})
    save(path,data);return item


def audit(path):
    data=load(path);tasks=data.get('tasks',{})
    if data.get('schema')!=1 or set(tasks)!=set(STATES):raise ValueError('Incomplete closeout schema')
    remaining={}
    for task,item in tasks.items():
        status=item.get('status')
        if status not in TERMINAL[task]:remaining[task]=status or 'pending';continue
        if not proof_valid(item.get('evidence',{})):
            remaining[task]='evidence_missing_or_changed';continue
        if ((task=='contribution' and status=='submitted') or (task=='cleanup' and status=='cleaned')) and not proof_valid(item.get('authorization',{})):
            remaining[task]='consent_missing_or_changed';continue
        if task=='contribution' and status=='not_needed' and tasks['experience_review']['status']!='not_valuable':
            remaining[task]='experience_assessment_changed';continue
        try:validate_special(task,status,item['evidence']['path'])
        except (ValueError,OSError,KeyError):remaining[task]='result_evidence_invalid'
    return {'complete':not remaining,'remaining':remaining,
            'pr_url':tasks['contribution'].get('url')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','record','status','audit']);parser.add_argument('ledger',type=Path)
    parser.add_argument('--task',choices=list(STATES));parser.add_argument('--status')
    parser.add_argument('--evidence',type=Path);parser.add_argument('--reason',default='');parser.add_argument('--url')
    args=parser.parse_args()
    try:
        if args.action=='init':result=plan(args.ledger)
        elif args.action=='record':result=record(args.ledger,args.task,args.status,args.evidence,args.reason,args.url)
        else:result=audit(args.ledger)
        print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
        if args.action=='audit' and not result['complete']:parser.exit(1)
    except (ValueError,OSError,KeyError,TypeError) as error:parser.exit(2,str(error)+'\n')
