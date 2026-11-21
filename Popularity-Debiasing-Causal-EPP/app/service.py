"""Explicit teammate-v2 serving; shared candidate builder and reranker."""
import numpy as np
import torch
import torch.nn.functional as F
from recommendation_api import RecommendationService
from teammate_v2.calibration import balanced_candidates, _rerank

class ReviewedRecommendationService(RecommendationService):
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
            pool=balanced_candidates(scores,torch.arange(self.num_items),self.tiers,self.report['candidate_pool'],k)
        if pool is None:
            ids=np.array([],dtype=int);rel=np.array([]);original=np.array([],dtype=int)
        else:
            ids,rel,original=pool
        raw=scores[torch.as_tensor(ids,dtype=torch.long)].numpy()
        target=np.bincount(self.tiers[events],minlength=3).astype(float)
        no_profile=not events
        if not target.sum():target=np.array([1.,0.,0.])
        mean=float(np.log1p(self.counts[events]).mean()) if events else 0.
        group_fit=fit or next(iter(self.report['results'].values()))['fit']
        thresholds=group_fit['thresholds']
        group='LowPop' if mean<=thresholds[0] else 'HighPop' if mean>=thresholds[1] else 'MedPop'
        if known and fit:
            group=fit.get('user_groups',{}).get(str(user_id),fit.get('user_groups',{}).get(user_id,group))
        weight=(fit['lambdas'].get(group,0.) if mode=='CP_H' else 1. if mode=='CP_Im' else 0.)
        # No history means no evidence of a desired popularity distribution.
        # Fall back explicitly to the base list instead of inventing a preference.
        if no_profile:weight=0.
        entry={'items':ids,'relevance':rel,'tier':self.tiers[ids],'target':target,'original_top_items':original}
        selected=_rerank(entry,k,weight)
        raw_scores=dict(zip(ids.tolist(),raw.tolist()))
        return {'user_id':user_id,'backend':backend,'requested_mode':mode,
                'applied_calibration_weight':weight,'popularity_group':group if events else None,
                'new_user':not known,'profile_available':not no_profile,
                'checkpoint_sha256':self.checkpoint_hash,'training_max_timestamp':self.training_max_timestamp,
                'snapshot_policy':'Frozen model and forecasts; supplied history updates exclusions/calibration only.',
                'recommendations':[{'item_id':int(i),'title':self.names.get(i),
                                    'base_ranking_score':float(raw_scores[i])} for i in selected]}
