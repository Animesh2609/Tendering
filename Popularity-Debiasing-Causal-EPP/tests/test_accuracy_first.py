import unittest
import numpy as np
from accuracy_first_calibration import candidate_ids,fit_accuracy_first,recommend

class AccuracyFirstTests(unittest.TestCase):
    def test_candidates_keep_baseline_and_add_other_tiers(self):
        scores=np.arange(30.,0.,-1);tiers=np.array([2]*20+[1]*5+[0]*5)
        ids=candidate_ids(scores,tiers,{0},12,3)
        self.assertEqual(ids[:3].tolist(),[1,2,3]);self.assertEqual(set(tiers[ids]),{0,1,2})
        self.assertNotIn(0,ids);self.assertEqual(len(ids),12)
    def test_positive_validation_example_and_baseline_fallback(self):
        entry={'items':np.array([0,1,2]),'tier':np.array([2,2,0]),'relevance':np.array([1.,.9,0.]),
               'target':np.array([1.,0,0]),'truth':{2},'profile_items':np.array([2]),'group':'LowPop'}
        weights,trials=fit_accuracy_first({0:entry},np.array([10,9,1]),1,[0,.5,1])
        self.assertGreater(weights['LowPop'],0.)
        self.assertEqual(recommend(entry,1,weights['LowPop']),[2])
        entry['truth']={0}
        weights,_=fit_accuracy_first({0:entry},np.array([10,9,1]),1,[0,.5,1])
        self.assertEqual(weights['LowPop'],0.)
        self.assertEqual(weights['HighPop'],0.)
    def test_zero_weight_returns_exact_baseline(self):
        entry={'items':np.array([4,3,2]),'relevance':np.ones(3),'tier':np.array([0,1,2]),'target':np.ones(3)}
        self.assertEqual(recommend(entry,2,0),[4,3])

class HeldOutLabelTests(unittest.TestCase):
    def test_fitting_succeeds_without_any_test_file(self):
        import json,tempfile
        from pathlib import Path
        from types import SimpleNamespace
        import pandas as pd
        import torch
        from config import Config
        from models import CausalEPP
        from data.popularity import compute_local_popularity,compute_evolving_personal_popularity
        from accuracy_first_calibration import fit
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tr=pd.DataFrame({'user':[0,0,1,1],'item':[0,1,2,3],
                             'timestamp':[0.,1.,0.,1.],'time_bin':[0,1,0,1]})
            tr.to_csv(root/'train_data.csv',sep='\t',index=False)
            pd.DataFrame({'user':[0,1],'item':[2,0],'timestamp':[2.,2.],
                          'time_bin':[1,1]}).to_csv(root/'val_data.csv',sep='\t',index=False)
            pop=compute_local_popularity(tr,2,4)
            np.save(root/'item_local_popularity.npy',pop)
            np.save(root/'user_epp.npy',compute_evolving_personal_popularity(tr,pop,2,num_time_bins=2))
            np.save(root/'time_bin_edges.npy',[0.,.5,1.])
            c=Config();c.embedding_dim=4;c.lightgcn_layers=1;c.mlp_hidden_dim=2
            model=CausalEPP(2,4,4,1,2,c.alpha)
            torch.save({'model':model.state_dict(),'config':c.__dict__,'num_users':2,'num_items':4},root/'model.pt')
            fit(SimpleNamespace(checkpoint=root/'model.pt',data_dir=root,output=root/'policy.json',
                                threads=1,candidate_pool=4,k=1))
            self.assertFalse((root/'test_data.csv').exists())
            policy=json.loads((root/'policy.json').read_text())
            self.assertEqual(policy['validation_users'],2)
            self.assertNotIn('test_data.csv',policy['training_validation_hashes'])

if __name__=='__main__':unittest.main()
