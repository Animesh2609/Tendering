"""Local JSON recommendation API for a frozen LightGCN+CausalEPP snapshot.

Existing-user scores use the trained model. Unknown users use an explicitly
labeled training-popularity fallback. This is not automatic online learning.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from models import CausalEPP, LightGCN
from forecasting.moving_average import forecast_all
from data.popularity import compute_global_popularity
from calibration import _tiers, _rerank
from compare_backbones import digest


class RecommendationService:
    def __init__(self, checkpoint, data_dir, calibration_report, threads=2):
        torch.set_num_threads(threads)
        self.checkpoint_hash=hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
        report=json.loads(Path(calibration_report).read_text())
        if report['checkpoint_sha256']!=self.checkpoint_hash:
            raise ValueError('Calibration belongs to a different checkpoint.')
        needed=('train_data.csv','item_local_popularity.npy','user_epp.npy',
                'time_bin_edges.npy','item_mapping.csv')
        if any(report.get('data_fingerprints',{}).get(name)!=digest(Path(data_dir)/name) for name in needed):
            raise ValueError('Calibration training-data fingerprint is missing or different.')
        self.report=report
        ck=torch.load(checkpoint,map_location='cpu',weights_only=True);c=ck['config']
        if c.get('use_llm_matching') or c.get('matching_backend') == 'llm':
            raise ValueError('This API supports LightGCN checkpoints only; LLM matching requires its own serving backend.')
        nu,ni=ck['num_users'],ck['num_items']
        # Serving needs training features, not validation/test labels.
        tr=pd.read_csv(Path(data_dir)/'train_data.csv',sep='\t')
        p=np.load(Path(data_dir)/'item_local_popularity.npy',allow_pickle=False)
        e=np.load(Path(data_dir)/'user_epp.npy',allow_pickle=False)
        edges=np.load(Path(data_dir)/'time_bin_edges.npy',allow_pickle=False)
        if (p.ndim!=2 or e.ndim!=2 or p.shape[1]!=ni or e.shape[1]!=nu
                or p.shape[0]!=e.shape[0] or p.shape[0]!=len(edges)-1
                or not np.isfinite(p).all() or not np.isfinite(e).all()
                or not tr.user.between(0,nu-1).all() or not tr.item.between(0,ni-1).all()):
            raise ValueError('Training features or IDs do not match the checkpoint.')
        active=np.flatnonzero(p.sum(axis=1)>0)
        if not len(active):raise ValueError('No active training history.')
        end=int(active[-1])+1;p=p[:end];e=e[:end]
        self.num_users,self.num_items=nu,ni
        model=CausalEPP(nu,ni,c['embedding_dim'],c['lightgcn_layers'],c['mlp_hidden_dim'],c['alpha'])
        model.load_state_dict(ck['model'],strict=True);model.eval()
        adj=LightGCN.normalized_adjacency(tr,nu,ni,'cpu')
        with torch.inference_mode():
            self.users,self.items=model.lightgcn.propagate(adj)
            self.item_mapping=model.item_mlp(self.items).squeeze(-1)
        self.q=model.q.detach();self.alpha=model.alpha
        ps,ss=forecast_all(p,e,c['moving_average_window'],c['item_forecast_horizon'],c['user_forecast_horizon'],
                          report['forecast_method'],c.get('forecast_level_alpha',.3),c.get('forecast_trend_beta',.1))
        self.p=torch.tensor(ps);self.s=torch.tensor(ss)
        self.counts=compute_global_popularity(tr,ni);self.tiers=_tiers(self.counts)
        self.histories=tr.groupby('user')['item'].apply(list).to_dict()
        names=pd.read_csv(Path(data_dir)/'item_mapping.csv')
        self.names=dict(zip(names.item.astype(int),names.raw_item.astype(str)))
        self.training_max_timestamp=float(tr.timestamp.max())

    def recommend(self,user_id=None,history_items=None,k=20,mode='CP_H'):
        if type(k) is not int or not 1<=k<=self.report['candidate_pool']:
            raise ValueError('k must be an integer between 1 and the configured candidate pool.')
        if mode not in ('CausalEPP','CP_H','CP_Im'):raise ValueError('Unknown recommendation mode.')
        if user_id is not None and (type(user_id) is not int or user_id<0):
            raise ValueError('user_id must be a nonnegative mapped integer ID or null.')
        if history_items is None:history_items=[]
        if not isinstance(history_items,list) or len(history_items)>10000:
            raise ValueError('history_items must be a list of at most 10000 mapped item IDs.')
        if any(type(i) is not int or not 0<=i<self.num_items for i in history_items):
            raise ValueError('History contains an invalid item ID.')
        fit=self.report['results'].get(str(k),{}).get('fit')
        if mode!='CausalEPP' and fit is None:
            raise ValueError('No validation-fitted calibration for this K; evaluate that K first.')
        known=user_id in self.histories
        events=list(self.histories.get(user_id,[]))+history_items
        previous=set(events)
        with torch.inference_mode():
            if known:
                matching=(self.users[user_id].unsqueeze(0)*self.items).sum(-1)
                conformity=torch.exp(-self.alpha*torch.abs(self.s[user_id]-self.p))*self.p*self.item_mapping
                scores=torch.tanh(self.q+conformity)*F.softplus(matching)
                backend='LightGCN+CausalEPP'
            else:
                scores=torch.tensor(self.counts.copy())
                backend='cold_start_training_popularity_fallback'
            if previous:scores[torch.tensor(sorted(previous),dtype=torch.long)]=-torch.inf
            take=min(self.report['candidate_pool'],self.num_items-len(previous))
            values,indices=torch.topk(scores,take)
        ids=indices.numpy();raw=values.numpy();rel=raw.astype(float)
        if len(rel):
            span=rel.max()-rel.min();rel=(rel-rel.min())/span if span>1e-12 else np.ones_like(rel)
        target=np.bincount(self.tiers[list(previous)],minlength=3).astype(float)
        no_profile=not events
        if not target.sum():target=np.array([1.,0.,0.])
        mean=float(np.log1p(self.counts[events]).mean()) if events else 0.
        group_fit=fit or next(iter(self.report['results'].values()))['fit']
        thresholds=group_fit['thresholds']
        group='LowPop' if mean<=thresholds[0] else 'HighPop' if mean>=thresholds[1] else 'MedPop'
        weight=(fit['lambdas'].get(group,0.) if mode=='CP_H' else 1. if mode=='CP_Im' else 0.)
        # No history means no evidence of a desired popularity distribution.
        # Fall back explicitly to the base list instead of inventing a preference.
        if no_profile:weight=0.
        entry={'items':ids,'relevance':rel,'tier':self.tiers[ids],'target':target}
        selected=ids[:k].tolist() if weight==0 else _rerank(entry,k,weight)
        raw_scores=dict(zip(ids.tolist(),raw.tolist()))
        return {'user_id':user_id,'backend':backend,'requested_mode':mode,
                'applied_calibration_weight':weight,'popularity_group':group if events else None,
                'new_user':not known,'profile_available':not no_profile,
                'checkpoint_sha256':self.checkpoint_hash,'training_max_timestamp':self.training_max_timestamp,
                'snapshot_policy':'Frozen model and forecasts; supplied history updates exclusions/calibration only.',
                'recommendations':[{'item_id':int(i),'title':self.names.get(i),
                                    'base_ranking_score':float(raw_scores[i])} for i in selected]}


def handler(service):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,value):
            body=json.dumps(value,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path!='/health':return self.reply(404,{'error':'Not found'})
            self.reply(200,{'status':'ready','checkpoint_sha256':service.checkpoint_hash})
        def do_POST(self):
            if self.path!='/recommend':return self.reply(404,{'error':'Not found'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=131072:raise ValueError('JSON body must be 1–131072 bytes.')
                payload=json.loads(self.rfile.read(length))
                if not isinstance(payload,dict):raise ValueError('Expected JSON object.')
                unknown=set(payload)-{'user_id','history_items','k','mode'}
                if unknown:raise ValueError('Unknown request fields: '+', '.join(sorted(unknown)))
                self.reply(200,service.recommend(**payload))
            except (ValueError,TypeError) as exc:self.reply(400,{'error':str(exc)})
        def log_message(self,*args):pass
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',required=True);p.add_argument('--data-dir',default='data/Ciao')
    p.add_argument('--calibration-report',required=True);p.add_argument('--port',type=int,default=8000)
    p.add_argument('--threads',type=int,default=2)
    a=p.parse_args()
    if a.threads<1 or not 1<=a.port<=65535:p.error('Invalid threads or port.')
    service=RecommendationService(a.checkpoint,a.data_dir,a.calibration_report,a.threads)
    server=HTTPServer(('127.0.0.1',a.port),handler(service))
    print(f'Local API ready at http://127.0.0.1:{a.port}; Ctrl+C stops it.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
