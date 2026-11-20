"""Tiny CPU tests; synthetic vectors do not validate pretrained LLM quality."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import torch
from config import Config
from llm_embedding_baseline import TextCausalEPP, TextBackbone, mapping_digest
from models import LightGCN
from train import train
from data.popularity import compute_local_popularity, compute_evolving_personal_popularity


class TextBackendTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(42)
        self.frame = pd.DataFrame({'user':[0,0,1], 'item':[0,1,2]})
        self.features = np.eye(3, dtype=np.float32)

    def test_training_only_profile_and_gradients(self):
        m = TextCausalEPP(self.features, self.frame, 3, dim=4, mlp_hidden=2)
        self.assertFalse(any(isinstance(x, LightGCN) for x in m.modules()))
        self.assertTrue(torch.allclose(m.lightgcn.user_text[0], torch.tensor([2**-.5,2**-.5,0.])))
        self.assertEqual(float(m.lightgcn.user_text[2].sum()), 0.)
        original = m.lightgcn.item_text.clone()
        u = torch.tensor([0,1]);i = torch.tensor([1,2])
        y = m(u,i,None,torch.tensor([.2,.5]),torch.tensor([.4,.3]))
        y.sum().backward()
        self.assertTrue(torch.isfinite(y).all())
        self.assertIsNotNone(m.lightgcn.user_projection.weight.grad)
        self.assertGreater(float(m.lightgcn.item_projection.weight.grad.abs().sum()), 0.)
        self.assertIsNone(m.lightgcn.item_text.grad)
        self.assertTrue(torch.equal(original,m.lightgcn.item_text))

    def test_bad_features_and_mapping_fingerprint(self):
        with self.assertRaises(ValueError):
            TextBackbone([[float('nan')]], self.frame,3,4)
        mapping=pd.DataFrame({'item':[0,1], 'raw_item':['book','music']})
        self.assertEqual(mapping_digest(mapping),mapping_digest(mapping.iloc[::-1]))
        changed=mapping.copy();changed.loc[0,'raw_item']='different'
        self.assertNotEqual(mapping_digest(mapping),mapping_digest(changed))

    def test_conflicting_backend_fails_before_generation(self):
        c=Config();c.use_llm_matching=True
        with patch('llm_baseline.build_llm_matching_scores',side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(ValueError,'Choose one'):
                train(c,backend_factory=lambda *a:None)

    def test_pipeline_default_and_text_forecasts_and_calibration(self):
        # Reuse the audited tiny interaction fixture, never the original Ciao outputs.
        features=np.random.default_rng(42).normal(size=(24,12)).astype(np.float32)
        def factory(c,frame,nu,ni,device):
            return TextCausalEPP(features,frame,nu,8,4,c.alpha).to(device),None
        Path('work/llm_prototype').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir='work/llm_prototype') as directory:
            fixture=Path(directory)/'fixture';fixture.mkdir()
            columns=['user','item','rating','timestamp','time_bin']
            frame=pd.DataFrame([(u,(u*4+t)%24,5.,float(t*100+u),t)
                                for t in range(12) for u in range(6)],columns=columns)
            for name,offset,stamp in [('train',None,None),('val',12,1300),('test',13,1400)]:
                part=frame if offset is None else pd.DataFrame(
                    [(u,(u*4+offset)%24,5.,float(stamp+u),11) for u in range(6)],columns=columns)
                part.to_csv(fixture/f'{name}_data.csv',sep='\t',index=False)
            pop=compute_local_popularity(frame,12,24)
            epp=compute_evolving_personal_popularity(frame,pop,6,num_time_bins=12)
            np.save(fixture/'item_local_popularity.npy',pop)
            np.save(fixture/'user_epp.npy',epp)
            np.save(fixture/'time_bin_edges.npy',np.arange(13)*100.)
            results={}
            for name,method,calibrate,use_text in [
                ('default','moving_average',False,False),
                ('text_ma','moving_average',False,True),
                ('text_holt','holt',False,True),
                ('text_calibration','moving_average',True,True)]:
                c=Config();c.data_dir=str(fixture);c.output_dir=str(Path(directory)/name)
                c.epochs=1;c.device='cpu';c.embedding_dim=8;c.lightgcn_layers=1
                c.mlp_hidden_dim=4;c.batch_size=72;c.eval_k=3
                c.calibration_candidate_pool=12;c.forecast_method=method
                c.enable_popularity_calibration=calibrate
                model,metrics,*_=train(c,backend_factory=factory if use_text else None)
                self.assertTrue(all(np.isfinite(v) for v in metrics.values()))
                if use_text:
                    self.assertFalse(any(isinstance(x,LightGCN) for x in model.modules()))
                    clone=factory(c,self.frame,6,24,'cpu')[0]
                    clone.load_state_dict(model.state_dict(),strict=True)
                results[name]=metrics
                if calibrate:
                    results['calibrated']=json.loads((Path(c.output_dir)/'popularity_calibrated_test_metrics.json').read_text())
            self.assertAlmostEqual(results['default']['NDCG@K'],.2718216255952429)
            Path('work/llm_prototype/test_metrics.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__': unittest.main()
