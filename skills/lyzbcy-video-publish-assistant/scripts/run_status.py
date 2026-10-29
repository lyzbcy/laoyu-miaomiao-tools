"""Compact, local-only recovery plan. Never opens a browser or posts."""
from pathlib import Path
import argparse, hashlib, json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def next_action(platform, item, state, video_hash, run_dir):
    supported=platform in ('douyin','bilibili','xiaohongshu','youtube')
    if not state:
        return {'action':'open' if supported else 'manual_ui_adapter_required','light':'yellow'}
    copy_hash=hashlib.sha256(json.dumps(item,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if state.get('video_sha256')!=video_hash or state.get('copy_sha256')!=copy_hash:
        return {'action':'review_changed_manifest','light':'red'}
    # A manual terminal review is distinct from an automatic publication signal.
    review=state.get('terminal_review',{})
    evidence=Path(review.get('evidence',''))
    if (review.get('video_sha256')==video_hash and review.get('copy_sha256')==copy_hash
            and review.get('status') in ('published','public') and review.get('id')
            and evidence.is_file() and digest(evidence)==review.get('evidence_sha256')):
        return {'action':'done','light':'green','status':review['status']}
    if not supported:
        return {'action':'query_manual_ui' if state.get('submission_attempted') else 'manual_ui_adapter_required','light':'yellow'}
    if state.get('submission_attempted'):
        name=platform+'-published.json' if platform=='xiaohongshu' else platform+'-publication.json'
        receipt=Path(run_dir)/name
        proof=load(receipt).get('gate',{}).get('proof',{}) if receipt.is_file() else {}
        expected=state.get('youtube_video_id') if platform=='youtube' else state.get('xiaohongshu_note_id')
        actual=proof.get('video_id') if platform=='youtube' else proof.get('note_id')
        if platform in ('youtube','xiaohongshu') and expected and actual==expected and proof.get('status') in ('published','public'):
            return {'action':'done','light':'green','status':proof['status']}
        return {'action':'confirm_published' if platform=='xiaohongshu' else 'confirm','light':'yellow','reason':'submission_attempted_query_only'}
    if state.get('last_error'):
        error=state['last_error']
        return {'action':'repair_from_local_error','light':'red','step':error.get('step'),'reason':str(error.get('error',''))[:160]}
    steps=state.get('steps',{})
    if state.get('upload_attempted') and steps.get('upload',{}).get('status')!='done':
        return {'action':'inspect_upload_once','light':'yellow','reason':'do_not_retransmit'}
    order=['upload','text','declaration','topics','settings','covers']
    if platform=='youtube':order+=['checks']
    order+=['save','reopen','verify']
    for step in order:
        if step in ('save','reopen','verify') and state.get('cover_visual_review')!='passed':
            return {'action':'review_covers','light':'yellow'}
        status=steps.get(step,{}).get('status')
        if status!='done':
            return {'action':'await_'+step if status=='pending' else step,'light':'yellow'}
    return {'action':'review_plan_then_authorized_submit','light':'yellow'}


def summarize(manifest, run_dir):
    manifest=Path(manifest);data=load(manifest)
    video=(manifest.parent/data['video']).resolve()
    actual=digest(video)
    if data.get('video_sha256') and data['video_sha256']!=actual:
        raise ValueError('Locked video hash differs')
    result={}
    for platform,item in data['platforms'].items():
        file=Path(run_dir)/(platform+'-state.json')
        result[platform]=next_action(platform,item,load(file) if file.is_file() else None,actual,run_dir)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path);parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--closeout-ledger',type=Path)
    args=parser.parse_args()
    try:
        result=summarize(args.manifest,args.run_dir)
        if args.closeout_ledger:
            from closeout import audit
            result['_closeout']=audit(args.closeout_ledger)
        print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
    except (ValueError,OSError,KeyError) as error:parser.exit(2,str(error)+'\n')
