"""Matched CPU experiments: LightGCN vs frozen-LLM CausalEPP, with POI calibration.

No model downloads. Explicit epochs and new output directories are required.
"""
import argparse
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd
import torch
from config import Config
from train import train, load_training_data
from models import CausalEPP, LightGCN
from llm_embedding_baseline import TextCausalEPP, mapping_digest
from forecasting.moving_average import forecast_all
from data.popularity import compute_global_popularity
from evaluate import ranking_metrics
from calibration import calibrated_ranking_metrics

DATA_FILES = ('train_data.csv', 'val_data.csv', 'test_data.csv',
              'item_local_popularity.npy', 'user_epp.npy', 'time_bin_edges.npy',
              'item_mapping.csv')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def data_fingerprints(directory):
    return {name:digest(Path(directory)/name) for name in DATA_FILES}


def read_cache(path, data_dir, num_items):
    mapping=pd.read_csv(Path(data_dir)/'item_mapping.csv')
    with np.load(path,allow_pickle=False) as f:
        vectors=f['embeddings'].copy();ids=f['item_ids'].copy()
        metadata=json.loads(str(f['metadata']))
    if (vectors.ndim!=2 or not np.isfinite(vectors).all()
            or not metadata.get('complete')
            or metadata.get('mapping_sha256')!=mapping_digest(mapping)
            or len(vectors)!=len(mapping) or len(vectors)<num_items
            or not np.array_equal(ids,np.arange(len(vectors)))):
        raise ValueError('A complete, finite cache matching the dataset item mapping is required.')
    return vectors[:num_items],metadata


def read_modes(directory):
    result={'CausalEPP':json.loads((directory/'test_metrics.json').read_text())}
    calibrated=json.loads((directory/'popularity_calibrated_test_metrics.json').read_text())
    for mode in ('CP_H','CP_Im'): result[mode]=calibrated[mode]['All']
    return result


def compare_results(results):
    """Matched per-seed differences. Never invent a percentage for a zero baseline."""
    rows=[]
    for entry in results:
        for mode,baseline in entry['lightgcn'].items():
            candidate=entry['llm'][mode]
            for metric,b in baseline.items():
                value=candidate[metric]
                rows.append(dict(seed=entry['seed'],mode=mode,metric=metric,
                                 lightgcn=b,llm=value,delta=value-b,
                                 relative_change_percent=(100*(value-b)/b if b!=0 else None),
                                 direction=('lower' if metric=='PopularityJSD' else
                                            'closer_to_zero' if metric=='PopLift' else
                                            'descriptive' if metric=='AverageRecommendedPopularity' else 'higher')))
    aggregate=[]
    for mode,metric in sorted({(r['mode'],r['metric']) for r in rows}):
        group=[r for r in rows if r['mode']==mode and r['metric']==metric]
        values=np.array([r['delta'] for r in group])
        aggregate.append(dict(mode=mode,metric=metric,seeds=len(group),
                              lightgcn_mean=float(np.mean([r['lightgcn'] for r in group])),
                              llm_mean=float(np.mean([r['llm'] for r in group])),
                              mean_paired_delta=float(values.mean()),
                              std_paired_delta=float(values.std(ddof=1)) if len(values)>1 else None))
    return dict(per_seed=rows,aggregate=aggregate,
                note='Relative changes are null for zero baselines. No significance claim. ARP is descriptive; PopLift is best assessed relative to zero.')


def run(args):
    if args.epochs<1 or args.k<1 or args.batch_size<1 or args.candidate_pool<args.k:
        raise ValueError('Use positive epochs/k/batch size and candidate_pool >= k.')
    if len(set(args.seeds))!=len(args.seeds): raise ValueError('Seeds must be unique.')
    output=Path(args.output)
    if output.exists(): raise FileExistsError('Choose a new output directory; existing runs are preserved.')
    loaded=load_training_data(args.data_dir)
    if loaded[1].empty or loaded[2].empty: raise ValueError('Validation and test splits must be nonempty.')
    fingerprints=data_fingerprints(args.data_dir)
    vectors,metadata=read_cache(args.cache,args.data_dir,loaded[-1])
    cache_sha=digest(args.cache)
    torch.set_num_threads(args.threads)
    output.mkdir(parents=True)
    results=[]
    for seed in args.seeds:
        entry={'seed':seed,'seconds':{}}
        for backbone in ('lightgcn','llm'):
            c=Config();c.data_dir=str(Path(args.data_dir).resolve())
            c.output_dir=str(output/f'seed_{seed}'/backbone);c.device='cpu'
            c.seed=seed;c.epochs=args.epochs;c.eval_k=args.k;c.batch_size=args.batch_size
            c.embedding_dim=args.dim;c.lightgcn_layers=args.layers
            c.forecast_method=args.forecast_method;c.enable_popularity_calibration=True
            c.calibration_candidate_pool=args.candidate_pool
            c.matching_backend=backbone
            if backbone=='llm':
                c.text_cache_sha256=cache_sha;c.text_encoder_metadata=metadata
            def factory(config,frame,nu,ni,device):
                return TextCausalEPP(vectors,frame,nu,config.embedding_dim,
                                    config.mlp_hidden_dim,config.alpha).to(device),None
            start=time.perf_counter()
            train(c,backend_factory=factory if backbone=='llm' else None)
            elapsed=time.perf_counter()-start
            run_dir=Path(c.output_dir)
            manifest=dict(backbone=backbone,data_fingerprints=fingerprints,
                          config=c.__dict__,elapsed_seconds=elapsed,
                          python=platform.python_version(),torch=torch.__version__,
                          numpy=np.__version__,pandas=pd.__version__)
            (run_dir/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
            entry[backbone]=read_modes(run_dir);entry['seconds'][backbone]=elapsed
        results.append(entry)
        (output/'raw_results.json').write_text(json.dumps(results,indent=2))
    if data_fingerprints(args.data_dir)!=fingerprints: raise RuntimeError('Dataset changed during experiment.')
    report=compare_results(results)
    (output/'comparison.json').write_text(json.dumps(report,indent=2))
    pd.DataFrame(report['per_seed']).to_csv(output/'comparison.csv',index=False)
    print('COMPARISON SAVED:',output/'comparison.csv')
    for row in report['aggregate']:
        if row['metric']=='NDCG@K': print(row)


def evaluate(args):
    """Reload a saved best checkpoint. No optimization, downloads or lambda tuning."""
    directory=Path(args.run_dir);output=Path(args.output)
    if output.exists(): raise FileExistsError('Evaluation output already exists.')
    manifest=json.loads((directory/'run_manifest.json').read_text())
    data_dir=args.data_dir or manifest['config']['data_dir']
    if data_fingerprints(data_dir)!=manifest['data_fingerprints']:
        raise ValueError('Dataset hashes differ from the training run; refusing incomparable evaluation.')
    checkpoint=torch.load(directory/'causalepp_ciao.pt',map_location='cpu',weights_only=True)
    cfg=checkpoint['config'];c=Config()
    for f in fields(c):
        if f.name in cfg:setattr(c,f.name,cfg[f.name])
    tr,va,te,edges,p,e,nu,ni=load_training_data(data_dir)
    if (nu,ni)!=(checkpoint['num_users'],checkpoint['num_items']):raise ValueError('Checkpoint dimensions differ.')
    torch.set_num_threads(args.threads)
    if manifest['backbone']=='llm':
        # Frozen features are included in state_dict: original cache/model is not needed.
        features=checkpoint['model']['lightgcn.item_text'].numpy()
        model=TextCausalEPP(features,tr,nu,c.embedding_dim,c.mlp_hidden_dim,c.alpha)
        adj=None
    elif manifest['backbone']=='lightgcn':
        model=CausalEPP(nu,ni,c.embedding_dim,c.lightgcn_layers,c.mlp_hidden_dim,c.alpha)
        adj=LightGCN.normalized_adjacency(tr,nu,ni,'cpu')
    else:raise ValueError('Unknown backbone in run manifest.')
    model.load_state_dict(checkpoint['model'],strict=True);model.eval()
    ps,ss=forecast_all(p,e,c.moving_average_window,c.item_forecast_horizon,
                      c.user_forecast_horizon,c.forecast_method,
                      c.forecast_level_alpha,c.forecast_trend_beta)
    history=pd.concat([tr,va],ignore_index=True)
    base=ranking_metrics(model,adj,history,te,nu,ni,ps,ss,c.eval_k,'cpu')
    fitted=json.loads((directory/'calibration_lambdas.json').read_text())
    calibrated=calibrated_ranking_metrics(model,adj,history,te,nu,ni,ps,ss,
               compute_global_popularity(tr,ni),c.eval_k,c.calibration_candidate_pool,
               fitted['lambdas'],fitted['thresholds'],'cpu')
    result={'CausalEPP':base,'calibrated':calibrated,
            'checkpoint_sha256':digest(directory/'causalepp_ciao.pt'),
            'calibration_selection':'Saved validation-selected lambdas; never retuned on test.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('--data-dir',default='data/Ciao')
    p.add_argument('--cache',required=True);p.add_argument('--output',required=True)
    p.add_argument('--epochs',type=int,required=True);p.add_argument('--seeds',type=int,nargs='+',default=[42])
    p.add_argument('--forecast-method',choices=['moving_average','holt'],default='moving_average')
    p.add_argument('--k',type=int,default=20);p.add_argument('--candidate-pool',type=int,default=150)
    p.add_argument('--batch-size',type=int,default=2048);p.add_argument('--dim',type=int,default=64)
    p.add_argument('--layers',type=int,default=3);p.add_argument('--threads',type=int,default=2)
    p.set_defaults(func=run)
    p=sub.add_parser('evaluate');p.add_argument('--run-dir',required=True)
    p.add_argument('--data-dir');p.add_argument('--output',required=True)
    p.add_argument('--threads',type=int,default=2);p.set_defaults(func=evaluate)
    args=parser.parse_args()
    if args.threads<1:parser.error('threads must be positive')
    args.func(args)

if __name__=='__main__':main()
