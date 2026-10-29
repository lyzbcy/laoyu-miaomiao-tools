"""Install an official, digest-verified Windows Node runtime without editing QQ."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import tempfile
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = 'NapNeko/NapCatQQ'
ASSET = 'NapCat.Shell.Windows.Node.zip'
SKILL = Path(__file__).resolve().parents[1]


def bind_target(release):
    tag = release['tag_name']
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag) or release.get('draft') or release.get('prerelease'):
        raise ValueError('not a stable runtime release')
    asset = next(x for x in release['assets'] if x['name'] == ASSET)
    url = asset['browser_download_url']
    expected = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{ASSET}'
    digest = asset.get('digest') or ''
    if url != expected or not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise ValueError('official asset URL or SHA256 unavailable; keep existing runtime')
    return {'tag': tag, 'url': url, 'sha256': digest[7:], 'size': int(asset['size'])}


def extract_verified(archive, target, destination):
    destination = Path(destination)
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != target['sha256']:
        raise ValueError('runtime SHA256 mismatch')
    with zipfile.ZipFile(archive) as z:
        if sum(x.file_size for x in z.infolist()) > 800_000_000:
            raise ValueError('runtime exceeds extraction limit')
        # Check the complete archive before writing a single entry.
        for entry in z.infolist():
            p = PurePosixPath(entry.filename)
            if ('\\' in entry.filename or ':' in entry.filename or p.is_absolute()
                    or '..' in p.parts or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('unsafe archive path')
            resolved = destination.joinpath(*p.parts).resolve()
            if not resolved.is_relative_to(destination.resolve()):
                raise ValueError('archive escapes runtime directory')
        z.extractall(destination)
    for relative in ('node.exe', 'index.js', 'wrapper.node', 'napcat/napcat.mjs'):
        if not (destination / relative).is_file():
            raise ValueError('incomplete runtime: ' + relative)


def save_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temporary,path)


def install(target, qq, cache, local_path, opener):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    final=cache/target['tag']
    previous={}
    if Path(local_path).is_file():
        previous=json.loads(Path(local_path).read_text(encoding='utf-8-sig'))
    if final.exists():
        marker=final/'.official-runtime.json'
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8'))!=target:
            raise ValueError('existing runtime differs; preserve it and choose another --cache-dir')
        for name in ('node.exe','index.js','wrapper.node','napcat/napcat.mjs'):
            if not (final/name).is_file():
                raise ValueError('existing runtime is incomplete; preserve it and choose another --cache-dir')
    else:
        with tempfile.TemporaryDirectory(prefix='.runtime-stage-',dir=cache) as stage:
            stage=Path(stage);archive=stage/'runtime.zip'
            request=urllib.request.Request(target['url'],headers={'User-Agent':'laoyu-qq-runtime/1.1'})
            with opener.open(request,timeout=120) as response,archive.open('wb') as stream:
                total=0
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>target['size'] or total>250_000_000:
                        raise ValueError('runtime download exceeds bound target size')
                    stream.write(chunk)
            if total!=target['size']:
                raise ValueError('incomplete runtime download')
            extracted=stage/'extracted'
            extract_verified(archive,target,extracted)
            save_json(extracted/'.official-runtime.json',target)
            os.replace(extracted,final)
    config=final/'napcat'/'config';config.mkdir(parents=True,exist_ok=True)
    account=config/f'onebot11_{qq}.json'
    if not account.exists():
        old_cfg=os.environ.get('NAPCAT_CFG_DIR',previous.get('cfg_dir',''))
        source=Path(old_cfg)/account.name if old_cfg else None
        if source and source.is_file():
            shutil.copy2(source,account)
        else:
            save_json(account,{'network':{'httpServers':[{
                'name':'local-skill','enable':True,'host':'127.0.0.1','port':30001,
                'messagePostFormat':'array','enableCors':False,'token':secrets.token_hex(24)
            }],'httpClients':[],'websocketServers':[],'websocketClients':[]}})
    # Preserve unrelated private settings; no credentials enter the distributed package.
    previous.update(qq=str(qq),node_dir=str(final),cfg_dir=str(config))
    save_json(local_path,previous)
    return final


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qq',required=True)
    parser.add_argument('--version',default='latest',help='latest or official vX.Y.Z')
    parser.add_argument('--proxy',help='Explicit HTTPS download proxy; never changes system settings')
    parser.add_argument('--cache-dir',default=str(Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'LaoyuQQ'/'napcat'))
    parser.add_argument('--local-config',default=os.environ.get('QQ_SKILL_LOCAL_CONFIG',str(SKILL/'runtime.local.json')))
    args=parser.parse_args(argv)
    if os.name!='nt':
        parser.error('Windows Node runtime installer requires Windows; existing remote OneBot still works')
    if not re.fullmatch(r'\d{5,12}',args.qq):
        parser.error('invalid QQ number')
    if args.version!='latest' and not re.fullmatch(r'v\d+\.\d+\.\d+',args.version):
        parser.error('invalid release version')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'https':args.proxy,'http':args.proxy})) if args.proxy else urllib.request.build_opener()
    endpoint='latest' if args.version=='latest' else 'tags/'+args.version
    request=urllib.request.Request(f'https://api.github.com/repos/{REPOSITORY}/releases/{endpoint}',headers={'User-Agent':'laoyu-qq-runtime/1.1'})
    # A setup/update click always fetches a fresh release target, never a previous prompt/cache.
    with opener.open(request,timeout=15) as response:
        release=json.load(response)
    target=bind_target(release)
    print('Runtime target: '+target['tag']+' SHA256='+target['sha256'])
    directory=install(target,args.qq,args.cache_dir,args.local_config,opener)
    print('Installed verified official runtime: '+str(directory))
    print('Next: python scripts/qq.py doctor; python scripts/qq.py grab')


if __name__=='__main__':
    main()
