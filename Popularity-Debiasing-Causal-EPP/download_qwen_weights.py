"""Explicit, bounded public Qwen download. Never invoked by training."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

REVISION='c1899de289a04d12100db370d81485cdf75e47ca'
FILES={'config.json','model.safetensors','tokenizer.json','tokenizer_config.json',
       'merges.txt','vocab.json','LICENSE','generation_config.json'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,help='New local model directory')
    args=p.parse_args();out=Path(args.output)
    if out.exists():raise FileExistsError('Choose a new directory; existing weights are preserved.')
    base='https://huggingface.co/Qwen/Qwen3-0.6B/resolve/'+REVISION+'/'
    with urllib.request.urlopen('https://huggingface.co/api/models/Qwen/Qwen3-0.6B/revision/'+REVISION+'?blobs=true',timeout=30) as response:
        manifest=json.load(response)
    if manifest['sha']!=REVISION:raise ValueError('Unexpected model revision.')
    files=[x for x in manifest['siblings'] if x['rfilename'] in FILES]
    cap=3_000_000_000
    if len(files)!=len(FILES) or sum(x['size'] for x in files)>cap:
        raise ValueError('Missing files or planned download exceeds 3 GB.')
    out.mkdir(parents=True);received=0;receipt=[]
    for entry in files:
        name=entry['rfilename'];target=out/name;temporary=out/(name+'.partial')
        sha=hashlib.sha256();size=0
        with urllib.request.urlopen(base+name,timeout=60) as response,temporary.open('xb') as f:
            while True:
                block=response.read(min(4*1024*1024,cap-received+1))
                if not block:break
                received+=len(block);size+=len(block)
                if received>cap:raise RuntimeError('Download exceeded 3 GB; stopping.')
                f.write(block);sha.update(block)
        if size!=entry['size']:raise ValueError('Incorrect file size: '+name)
        if entry.get('lfs') and sha.hexdigest()!=entry['lfs']['sha256']:
            raise ValueError('Checksum mismatch: '+name)
        temporary.rename(target)
        receipt.append({'file':name,'bytes':size,'sha256':sha.hexdigest()})
        print(name, 'verified', flush=True)
    (out/'download_receipt.json').write_text(json.dumps({'revision':REVISION,'bytes':received,'files':receipt},indent=2))

if __name__=='__main__':main()
