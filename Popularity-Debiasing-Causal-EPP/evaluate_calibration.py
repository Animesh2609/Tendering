"""All-user, paired LightGCN+CausalEPP vs popularity-calibration evaluation.

No training or downloads. Fits calibration on validation, reports test once.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
import torch
from models import CausalEPP, LightGCN
from train import load_training_data
from compare_backbones import data_fingerprints
from forecasting.moving_average import forecast_all
from data.popularity import compute_global_popularity
from calibration import (GROUPS, fit_group_lambdas, _make_candidate_cache,
                         _rerank, _js_divergence)


def user_metrics(entry, recommendations, counts, k):
    truth=entry['truth'];hits=np.array([i in truth for i in recommendations],dtype=float)
    idcg=sum(1/np.log2(j+2) for j in range(min(len(truth),k)))
    tier_lookup=dict(zip(entry['items'],entry['tier']))
    distribution=np.bincount([tier_lookup[i] for i in recommendations],minlength=3)
    arp=float(np.mean(counts[recommendations])) if recommendations else 0.
    profile=entry['profile_items'];profile_pop=float(np.mean(counts[profile])) if len(profile) else 0.
    return {'Recall@K':float(hits.sum()/len(truth)) if truth else 0.,
            'Precision@K':float(hits.sum()/k),
            'NDCG@K':float(sum(v/np.log2(j+2) for j,v in enumerate(hits))/idcg) if idcg else 0.,
            'HitRate@K':float(hits.sum()>0),
            'PopularityJSD':_js_divergence(entry['target'],distribution),
            'AverageRecommendedPopularity':arp,
            'PopLift':arp/profile_pop-1 if profile_pop>0 else 0.}


def aggregate(rows, catalog_size):
    if not rows:return {'users':0,'metrics':None}
    metrics={name:float(np.mean([r['metrics'][name] for r in rows])) for name in rows[0]['metrics']}
    metrics['CatalogCoverage@K']=len({i for r in rows for i in r['recommendations']})/catalog_size
    return {'users':len(rows),'metrics':metrics}


def evaluate_cache(cache,counts,k,lambdas,train_activity):
    methods={'CausalEPP':{},'CP_H':{},'CP_Im':{}}
    for uid,entry in cache.items():
        n=train_activity.get(uid,0)
        activity='Sparse_1_to_10' if n<=10 else 'Medium_11_to_50' if n<=50 else 'Active_over_50'
        for mode in methods:
            rec=(entry['items'][:k].astype(int).tolist() if mode=='CausalEPP' else
                 _rerank(entry,k,lambdas.get(entry['group'],0.) if mode=='CP_H' else 1.))
            methods[mode][uid]={'user':int(uid),'popularity_group':entry['group'],
                               'activity_group':activity,'recommendations':rec,
                               'metrics':user_metrics(entry,rec,counts,k)}
    summaries={}
    for mode,users in methods.items():
        rows=list(users.values())
        summaries[mode]={'All':aggregate(rows,len(counts)),
            'by_popularity':{g:aggregate([r for r in rows if r['popularity_group']==g],len(counts)) for g in GROUPS},
            'by_activity':{g:aggregate([r for r in rows if r['activity_group']==g],len(counts))
                           for g in ['Sparse_1_to_10','Medium_11_to_50','Active_over_50']}}
    return summaries,methods


def paired_comparison(methods,seed=42):
    ids=sorted(methods['CausalEPP']);result={};rng=np.random.default_rng(seed)
    for mode in ['CP_H','CP_Im']:
        metrics={}
        for metric in ['Recall@K','Precision@K','NDCG@K','HitRate@K','PopularityJSD','PopLift']:
            base=np.array([methods['CausalEPP'][u]['metrics'][metric] for u in ids])
            other=np.array([methods[mode][u]['metrics'][metric] for u in ids]);delta=other-base
            means=delta[rng.integers(0,len(ids),size=(500,len(ids)))].mean(1) if ids else np.array([np.nan])
            metrics[metric]={'absolute_delta':float(delta.mean()) if ids else None,
                'relative_change_percent':float(100*delta.mean()/base.mean()) if ids and base.mean()!=0 else None,
                'paired_bootstrap_95_percent_interval':np.quantile(means,[.025,.975]).tolist() if ids else None,
                'users_with_increase':int((delta>1e-12).sum()),'users_with_decrease':int((delta< -1e-12).sum())}
        result[mode]=metrics
    return result


def run(args):
    if any(k<1 for k in args.k) or args.candidate_pool<max(args.k):
        raise ValueError('Positive K and candidate_pool >= max(K) required.')
    output=Path(args.output)
    if output.exists():raise FileExistsError('Use a new output directory.')
    torch.set_num_threads(args.threads);start=time.perf_counter()
    tr,va,te,edges,p,e,nu,ni=load_training_data(args.data_dir)
    if va.empty or te.empty:raise ValueError('Validation/test must be nonempty.')
    checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=True);cfg=checkpoint['config']
    fingerprints=data_fingerprints(args.data_dir)
    if cfg.get('data_fingerprints') and cfg['data_fingerprints']!=fingerprints:
        raise ValueError('Training dataset fingerprints differ; refusing evaluation.')
    if cfg.get('matching_backend')=='llm' or cfg.get('use_llm_matching'):
        raise ValueError('This comparison requires a standard LightGCN CausalEPP checkpoint.')
    if (nu,ni)!=(checkpoint['num_users'],checkpoint['num_items']):raise ValueError('Checkpoint/data ID dimensions differ.')
    model=CausalEPP(nu,ni,cfg['embedding_dim'],cfg['lightgcn_layers'],cfg['mlp_hidden_dim'],cfg['alpha'])
    model.load_state_dict(checkpoint['model'],strict=True);model.eval()
    adj=LightGCN.normalized_adjacency(tr,nu,ni,'cpu')
    forecast=args.forecast_method or cfg.get('forecast_method','moving_average')
    ps,ss=forecast_all(p,e,cfg['moving_average_window'],cfg['item_forecast_horizon'],
                      cfg['user_forecast_horizon'],forecast,cfg.get('forecast_level_alpha',.3),cfg.get('forecast_trend_beta',.1))
    counts=compute_global_popularity(tr,ni);history=pd.concat([tr,va],ignore_index=True)
    activity=tr.groupby('user')['item'].nunique().to_dict()
    output.mkdir(parents=True)
    result={'checkpoint':str(args.checkpoint),'forecast_method':forecast,
            'data_fingerprints':fingerprints,
            'checkpoint_sha256':hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest(),
            'checkpoint_saved_epochs':cfg.get('epochs'),'training_rows':len(tr),
            'validation_users':int(va.user.nunique()),'test_users':int(te.user.nunique()),
            'test_rows':len(te),'catalog_size':ni,'candidate_pool':args.candidate_pool,
            'scope':'All eligible test users, same model and candidates; validation-only lambda fitting.',
            'limitations':['Single checkpoint; no training-seed uncertainty.',
                          ('Training dataset fingerprints verified.' if cfg.get('data_fingerprints') else 'Supplied checkpoint has no dataset fingerprint: provenance cannot be certified.'),
                          'Bootstrap intervals condition on this checkpoint and selected validation lambdas.',
                          'Retains audited original data/time-window and repeated-positive semantics.'],
            'results':{}}
    csv=[]
    for k in args.k:
        fit=fit_group_lambdas(model,adj,tr,va,nu,ni,ps,ss,counts,k,args.candidate_pool,
                             tuple(np.arange(11)/10),'cpu')
        cache,_,_= _make_candidate_cache(model,adj,history,te,nu,ni,ps,ss,counts,
                                         args.candidate_pool,'cpu',group_thresholds=fit['thresholds'])
        summaries,per_user=evaluate_cache(cache,counts,k,fit['lambdas'],activity)
        same_topk=sum(per_user['CausalEPP'][u]['recommendations']==per_user['CP_H'][u]['recommendations'] for u in cache)
        single_tier=sum(len(set(entry['tier'].tolist()))<=1 for entry in cache.values())
        result['results'][str(k)]={'fit':fit,'evaluated_users':len(cache),
            'excluded_users':int(te.user.nunique())-len(cache),'CP_H_unchanged_lists':same_topk,
            'single_tier_candidate_users':single_tier,'summaries':summaries,
            'paired_comparison':paired_comparison(per_user)}
        (output/f'per_user_at_{k}.json').write_text(json.dumps(per_user,indent=2))
        for mode,summary in summaries.items():
            for grouping,groups in [('overall',{'All':summary['All']}),('popularity',summary['by_popularity']),('activity',summary['by_activity'])]:
                for group,data in groups.items():
                    csv.append({'k':k,'mode':mode,'grouping':grouping,'group':group,'users':data['users'],**(data['metrics'] or {})})
        print('Completed K=',k,'users=',len(cache),'lambdas=',fit['lambdas'],flush=True)
    result['runtime_seconds']=time.perf_counter()-start
    pd.DataFrame(csv).to_csv(output/'metrics.csv',index=False)
    (output/'comparison.json').write_text(json.dumps(result,indent=2))
    print('Saved',output,'runtime_seconds',result['runtime_seconds'],flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',required=True);p.add_argument('--data-dir',default='data/Ciao')
    p.add_argument('--output',required=True);p.add_argument('--k',type=int,nargs='+',default=[10,20])
    p.add_argument('--candidate-pool',type=int,default=150)
    p.add_argument('--forecast-method',choices=['moving_average','holt'])
    p.add_argument('--threads',type=int,default=2)
    args=p.parse_args()
    if args.threads<1:p.error('threads must be positive')
    run(args)

if __name__=='__main__':main()
