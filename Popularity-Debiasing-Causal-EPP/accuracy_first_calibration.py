"""Validation-selected, accuracy-first popularity calibration extension.

Preserves CausalEPP equations. Diversifies retrieval, retains baseline top-K,
then accepts calibration only when validation accuracy and JSD do not regress.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from models import CausalEPP,LightGCN
from forecasting.moving_average import forecast_all
from data.popularity import compute_global_popularity
from calibration import _tiers,_profile_groups,_group_name,_rerank,GROUPS
from evaluate_calibration import user_metrics,aggregate,paired_comparison


def candidate_ids(scores,tiers,seen,pool,k):
    scores=np.asarray(scores,dtype=float);tiers=np.asarray(tiers)
    if not 0<k<=pool or scores.ndim!=1 or tiers.shape!=scores.shape:
        raise ValueError('Invalid scores, tiers or candidate limits.')
    valid=np.flatnonzero(np.isfinite(scores))
    valid=valid[~np.isin(valid,list(seen))]
    ordered=valid[np.lexsort((valid,-scores[valid]))]
    # Always retain baseline top-K. Add relevance-ranked candidates per tier.
    selected=set(ordered[:k].tolist());quota=max(0,(pool-k)//3)
    for tier in range(3):selected.update(ordered[tiers[ordered]==tier][:quota].tolist())
    for item in ordered:
        if len(selected)>=pool:break
        selected.add(int(item))
    return np.array([int(i) for i in ordered if int(i) in selected],dtype=np.int64)


def recommend(entry,k,weight):
    if weight==0:return entry['items'][:k].astype(int).tolist()
    return _rerank(entry,k,float(weight))


def summary(cache,counts,k,weight):
    rows=[]
    for uid,entry in cache.items():
        w=weight.get(entry['group'],0.) if isinstance(weight,dict) else weight
        items=recommend(entry,k,w)
        rows.append({'user':int(uid),'group':entry['group'],'recommendations':items,
                     'metrics':user_metrics(entry,items,counts,k)})
    return aggregate(rows,len(counts)),{r['user']:r for r in rows}


def fit_accuracy_first(validation_cache,counts,k,grid):
    selected={};trials={}
    for group in GROUPS:
        cache={u:e for u,e in validation_cache.items() if e['group']==group}
        if not cache:
            selected[group]=0.;trials[group]={'users':0,'selected_weight':0.,'trials':[]};continue
        baseline,_=summary(cache,counts,k,0.);base=baseline['metrics']
        best_key=None;best_weight=0.;rows=[]
        for weight in sorted(set([0.]+[float(x) for x in grid])):
            if not 0<=weight<=1:raise ValueError('Calibration weight must be in [0,1].')
            report,_=summary(cache,counts,k,weight);m=report['metrics']
            feasible=(all(m[key]>=base[key]-1e-12 for key in ['NDCG@K','Recall@K','Precision@K','HitRate@K'])
                      and m['PopularityJSD']<=base['PopularityJSD']+1e-12)
            rows.append({'weight':weight,'metrics':m,'accepted_by_guard':bool(feasible)})
            key=(m['NDCG@K'],m['Recall@K'],-m['PopularityJSD'],-weight)
            if feasible and (best_key is None or key>best_key):best_weight=weight;best_key=key
        selected[group]=best_weight
        trials[group]={'users':len(cache),'selected_weight':best_weight,'baseline':base,'trials':rows}
    return selected,trials


class FrozenScorer:
    def __init__(self,checkpoint,data_dir):
        root=Path(data_dir)
        ck=torch.load(checkpoint,map_location='cpu',weights_only=True);c=ck['config']
        if c.get('matching_backend')=='llm' or c.get('use_llm_matching'):raise ValueError('LightGCN checkpoint required.')
        self.nu,self.ni=ck['num_users'],ck['num_items']
        self.train=pd.read_csv(root/'train_data.csv',sep='\t')
        self.counts=compute_global_popularity(self.train,self.ni);self.tiers=_tiers(self.counts)
        _,self.thresholds=_profile_groups(self.train,self.nu,self.counts)
        self.model=CausalEPP(self.nu,self.ni,c['embedding_dim'],c['lightgcn_layers'],c['mlp_hidden_dim'],c['alpha'])
        self.model.load_state_dict(ck['model'],strict=True);self.model.eval()
        graph=LightGCN.normalized_adjacency(self.train,self.nu,self.ni,'cpu')
        with torch.inference_mode():
            self.users,self.items=self.model.lightgcn.propagate(graph)
            self.item_mapping=self.model.item_mlp(self.items).squeeze(-1)
        p=np.load(root/'item_local_popularity.npy');s=np.load(root/'user_epp.npy')
        if p.shape[1]!=self.ni or s.shape[1]!=self.nu:raise ValueError('Feature/checkpoint dimensions differ.')
        active=np.flatnonzero(p.sum(1)>0)
        if not len(active):raise ValueError('Empty training features.')
        end=int(active[-1])+1
        p,s=forecast_all(p[:end],s[:end],c['moving_average_window'],c['item_forecast_horizon'],
                        c['user_forecast_horizon'],c.get('forecast_method','moving_average'),
                        c.get('forecast_level_alpha',.3),c.get('forecast_trend_beta',.1))
        self.p=torch.tensor(p);self.s=torch.tensor(s)

    def cache(self,history,labels,pool,k):
        histories=history.groupby('user')['item'].apply(list).to_dict();result={}
        for uid,actual in labels.groupby('user')['item']:
            uid=int(uid)
            if uid not in histories or not 0<=uid<self.nu:raise ValueError('This protocol requires known users with earlier history.')
            events=histories[uid];seen=set(events)
            with torch.inference_mode():
                matching=(self.users[uid].unsqueeze(0)*self.items).sum(-1)
                conformity=torch.exp(-self.model.alpha*torch.abs(self.s[uid]-self.p))*self.p*self.item_mapping
                scores=(torch.tanh(self.model.q+conformity)*F.softplus(matching)).numpy()
            ids=candidate_ids(scores,self.tiers,seen,pool,k)
            raw=scores[ids].astype(float)
            span=np.ptp(raw) if len(raw) else 0
            relevance=(raw-raw.min())/span if span>1e-12 else np.ones_like(raw)
            target=np.bincount(self.tiers[list(seen)],minlength=3).astype(float)
            mean=float(np.log1p(self.counts[events]).mean())
            group='LowPop' if mean<=self.thresholds[0] else 'HighPop' if mean>=self.thresholds[1] else 'MedPop'
            result[uid]={'items':ids,'relevance':relevance,'tier':self.tiers[ids],
                         'target':target,'profile_items':np.array(sorted(seen),dtype=int),
                         'group':group,'truth':set(int(i) for i in actual)}
        return result


def fit(args):
    output=Path(args.output)
    if output.exists():raise FileExistsError('Use a new output directory.')
    torch.set_num_threads(args.threads);start=time.perf_counter()
    model=FrozenScorer(args.checkpoint,args.data_dir)
    validation=pd.read_csv(Path(args.data_dir)/'val_data.csv',sep='\t')
    if validation.empty:raise ValueError('Validation data is empty.')
    if model.train.timestamp.max()>=validation.timestamp.min():raise ValueError('Training/validation time overlap.')
    cache=model.cache(model.train,validation,args.candidate_pool,args.k)
    grid=[0,.005,.01,.02,.05,.1,.2,.4,.7,1.]
    weights,trials=fit_accuracy_first(cache,model.counts,args.k,grid)
    result={'checkpoint':str(Path(args.checkpoint).resolve()),'checkpoint_sha256':hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest(),
            'data_dir':str(Path(args.data_dir).resolve()),'k':args.k,'candidate_pool':args.candidate_pool,
            'weights':weights,'grid':grid,'thresholds':model.thresholds,'trials':trials,
            'validation_users':len(cache),'validation_single_tier_pools':sum(len(set(e['tier']))<=1 for e in cache.values()),
            'protocol':'Temporal held-out interactions of known users; test labels not read during fit.',
            'variant':'Accuracy-first validation guard with baseline-preserving tier-diverse candidates; not original CP_H.',
            'training_validation_hashes':{name:hashlib.sha256((Path(args.data_dir)/name).read_bytes()).hexdigest()
                for name in ['train_data.csv','val_data.csv','item_local_popularity.npy','user_epp.npy','time_bin_edges.npy']},
            'runtime_seconds':time.perf_counter()-start}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({'weights':weights,'validation_users':len(cache),'single_tier_pools':result['validation_single_tier_pools'],'seconds':result['runtime_seconds']},indent=2))


def test(args):
    output=Path(args.output)
    if output.exists():raise FileExistsError('Use a new output directory; do not overwrite a test result.')
    policy=json.loads(Path(args.policy).read_text())
    if hashlib.sha256(Path(policy['checkpoint']).read_bytes()).hexdigest()!=policy['checkpoint_sha256']:raise ValueError('Checkpoint changed after validation.')
    root=Path(policy['data_dir'])
    for name,sha in policy['training_validation_hashes'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:raise ValueError('Data changed after validation: '+name)
    torch.set_num_threads(args.threads);start=time.perf_counter()
    model=FrozenScorer(policy['checkpoint'],root)
    validation=pd.read_csv(root/'val_data.csv',sep='\t')
    labels=pd.read_csv(root/'test_data.csv',sep='\t')
    if labels.empty or validation.timestamp.max()>=labels.timestamp.min():raise ValueError('Empty test or validation/test time overlap.')
    cache=model.cache(pd.concat([model.train,validation]),labels,policy['candidate_pool'],policy['k'])
    baseline,b=summary(cache,model.counts,policy['k'],0.)
    calibrated,c=summary(cache,model.counts,policy['k'],policy['weights'])
    groups={g:{'baseline':aggregate([r for r in b.values() if r['group']==g],model.ni),
               'calibrated':aggregate([r for r in c.values() if r['group']==g],model.ni)} for g in GROUPS}
    # Reuse paired bootstrap implementation; CP_Im slot is ignored here.
    diffs=paired_comparison({'CausalEPP':b,'CP_H':c,'CP_Im':c})['CP_H']
    result={'policy_sha256':hashlib.sha256(Path(args.policy).read_bytes()).hexdigest(),
            'test_file_sha256':hashlib.sha256((root/'test_data.csv').read_bytes()).hexdigest(),
            'baseline':baseline,'accuracy_first_calibration':calibrated,'groups':groups,'paired_differences':diffs,
            'single_tier_pools':sum(len(set(e['tier']))<=1 for e in cache.values()),
            'changed_lists':sum(b[u]['recommendations']!=c[u]['recommendations'] for u in cache),
            'seconds':time.perf_counter()-start,
            'caveat':'Previously inspected test split; reused evaluation, not a blind new holdout. No test-driven retuning.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('fit');a.add_argument('--checkpoint',required=True);a.add_argument('--data-dir',default='data/Ciao')
    a.add_argument('--output',required=True);a.add_argument('--k',type=int,default=20);a.add_argument('--candidate-pool',type=int,default=150)
    a.add_argument('--threads',type=int,default=2);a.set_defaults(func=fit)
    a=sub.add_parser('test');a.add_argument('--policy',required=True);a.add_argument('--output',required=True)
    a.add_argument('--threads',type=int,default=2);a.set_defaults(func=test)
    args=p.parse_args()
    if args.threads<1:p.error('threads must be positive')
    args.func(args)

if __name__=='__main__':main()
