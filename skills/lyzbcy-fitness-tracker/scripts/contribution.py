"""Prepare a small reviewed contribution draft and clean only its owned temporary files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid

PRIVATE = re.compile(r'-----BEGIN .*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}|'
                     r'https://qyapi\.weixin\.qq\.com/\S*key=|'
                     r'(?i:api[_-]?key|password|secret)\s*[:=]\s*["\']?\S+|'
                     r'[A-Za-z]:[\\/]|/home/|/Users/|'
                     r'"action"\s*:\s*"(?:set|bodyweight|cardio)"|'
                     r'\b\d{1,3}(?:\.\d{1,3}){3}\b')


def text_file(path):
    p = Path(path)
    if p.is_symlink() or p.suffix.lower() not in {'.md','.txt','.patch','.diff'}:
        raise ValueError('只接受显式指定的短文本草案/补丁，不读取训练JSONL或整套工程')
    data = p.read_bytes()
    if len(data)>128_000:
        raise ValueError('草案过大，请改成最小文字补丁')
    text = data.decode('utf-8-sig')
    if PRIVATE.search(text):
        raise ValueError('草案可能包含私有数据；请人工脱敏后重试')
    return text


def run_dir(workspace, run_id):
    if not re.fullmatch('[a-f0-9]{32}',run_id):
        raise ValueError('无效的本次贡献编号')
    root = Path(workspace).expanduser().resolve()
    base = root/'.contribution-tmp'
    if base.is_symlink():
        raise ValueError('贡献目录不能是符号链接')
    folder=base/run_id
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError('贡献目录越界')
    return root,folder


def prepare(workspace, summary, patch=None, confirmed=False):
    if not confirmed:
        raise ValueError('用户尚未确认最终交付，不准备或邀请贡献')
    files={'summary.md':text_file(summary)}
    if patch:
        files['proposal.patch']=text_file(patch)
    run_id=uuid.uuid4().hex
    root,folder=run_dir(workspace,run_id)
    folder.mkdir(parents=True,exist_ok=False)
    hashes={}
    for name,text in files.items():
        data=text.encode('utf-8');(folder/name).write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
    (folder/'.owned.json').write_text(json.dumps({'run_id':run_id,'files':hashes}),encoding='utf-8')
    return {'run_id':run_id,'draft':str(folder/'summary.md'),'state':'awaiting_consent',
            'submission':'not_submitted','reminder':'人工复核脱敏内容，用户同意范围后才可提交PR；不要从账号缓存猜署名。'}


def cleanup(folder, owned):
    for name in owned:
        if name not in {'summary.md','proposal.patch'}:
            raise ValueError('未知临时文件，不扩展清理范围')
        p=folder/name
        if p.is_symlink() or not p.resolve().is_relative_to(folder.resolve()):
            raise ValueError('临时文件是符号链接或越界')
    for name in owned:
        (folder/name).unlink(missing_ok=True)
    (folder/'.owned.json').unlink()
    # Unexpected files may belong to somebody else: leave them in place, never rmtree.
    empty=not any(folder.iterdir())
    if empty:
        folder.rmdir()
    return {'owned_files_cleaned':True,'folder_removed':empty}


def answer(workspace,run_id,decision,result_url=None,patch_out=None,credit='anonymous'):
    root,folder=run_dir(workspace,run_id)
    marker=folder/'.owned.json'
    if marker.is_symlink():
        raise ValueError('无效的临时清单')
    owned=json.loads(marker.read_text(encoding='utf-8'))
    if owned.get('run_id')!=run_id:
        raise ValueError('清单与本次任务不符')
    if decision=='pending':
        return {'state':'awaiting_consent','submitted':False,'cleaned':False}
    if decision not in {'accept','decline'}:
        raise ValueError('无效答复')
    if decision=='accept':
        if result_url:
            if not re.fullmatch(r'https://github\.com/lyzbcy/laoyu-miaomiao-tools/pull/\d+',result_url):
                raise ValueError('需记录目标仓库实际PR链接；不代表已合入')
        elif patch_out:
            p=Path(patch_out).resolve()
            if not p.is_relative_to(root) or p.is_relative_to(folder.resolve()) or p.exists():
                raise ValueError('最小补丁应另存于本次workspace内、临时包外，且不能覆盖已有文件')
            if 'proposal.patch' not in owned['files']:
                raise ValueError('没有可保留的补丁')
            data=text_file(folder/'proposal.patch')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data.encode('utf-8'))
        else:
            raise ValueError('同意后先提交并记录真实PR，或将最小补丁另存交付，再清理')
    if not isinstance(credit,str) or len(credit)>100 or '\n' in credit:
        raise ValueError('署名需用户确认的简短名字/账号，或anonymous')
    result={'run_id':run_id,'decision':decision,'pr_url':result_url,
            'patch':str(patch_out) if patch_out else None,'credit':credit,'merged':False}
    with (root/'contribution-results.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(result,ensure_ascii=False)+'\n')
    result.update(cleanup(folder,owned['files']))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('prepare');a.add_argument('--workspace',required=True);a.add_argument('--summary',required=True)
    a.add_argument('--patch');a.add_argument('--confirmed',action='store_true')
    a=sub.add_parser('answer');a.add_argument('--workspace',required=True);a.add_argument('--run-id',required=True)
    a.add_argument('--decision',choices=['pending','accept','decline'],required=True)
    a.add_argument('--result-url');a.add_argument('--patch-out');a.add_argument('--credit',default='anonymous')
    a=p.parse_args()
    try:
        result=prepare(a.workspace,a.summary,a.patch,a.confirmed) if a.cmd=='prepare' else answer(a.workspace,a.run_id,a.decision,a.result_url,a.patch_out,a.credit)
        print(json.dumps(result,ensure_ascii=False))
    except (ValueError,OSError) as e:
        p.exit(1,str(e)+'\n')


if __name__=='__main__':
    main()
