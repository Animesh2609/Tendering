import unittest
import numpy as np
from teammate_v2.calibration import _rerank,_compare_recommendation_lists
from teammate_v2.llm_baseline import LocalHuggingFaceScorer
class UpdateTests(unittest.TestCase):
    def test_zero_lambda_preserves_original_ties(self):
        entry={'items':np.array([1,2]),'original_top_items':np.array([2,1])}
        self.assertEqual(_rerank(entry,2,0),[2,1])
    def test_unequal_list_lengths(self):
        result=_compare_recommendation_lists({1:[3,4]},{1:[3]})
        self.assertEqual(result['changed_user_count'],1)
    def test_malformed_llm_values_are_missing(self):
        self.assertEqual(LocalHuggingFaceScorer._parse_scores('{"1":"bad","2":0.8}',[1,2]),{2:.8})

    def test_updated_training_pipeline_tiny_fixture(self):
        import contextlib,io,tempfile
        from pathlib import Path
        from test_teammate_workflow import TeammateWorkflowTests
        from prepare_douban import prepare
        from config import Config
        from teammate_v2.train import train
        import torch
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory);a=TeammateWorkflowTests().fixture(root);prepare(a)
            c=Config();c.data_dir=a.output;c.output_dir=str(root/'run');c.device='cpu'
            c.epochs=1;c.embedding_dim=4;c.lightgcn_layers=1;c.mlp_hidden_dim=4
            c.batch_size=64;c.eval_k=3;c.enable_popularity_calibration=True
            train(c)
            import json
            r=json.loads((root/'run'/'popularity_calibrated_test_metrics.json').read_text())
            self.assertIn('Original_CausalEPP',r);self.assertIn('CP_H',r)

    def test_batched_scores_preserve_request_order(self):
        import torch
        class Tokenizer:
            def apply_chat_template(self,*a,**k):return 'prompt'
            def __call__(self,prompts,**kw):return {'input_ids':torch.ones((len(prompts),2),dtype=torch.long)}
            def batch_decode(self,*a,**k):return ['{"1":0.3}','{"2":0.7}']
            eos_token_id=0
        class Model:
            def generate(self,**kw):return torch.ones((2,3),dtype=torch.long)
        s=LocalHuggingFaceScorer.__new__(LocalHuggingFaceScorer)
        s.tokenizer=Tokenizer();s.model=Model();s.device='cpu'
        self.assertEqual(s.score_batch([('a',[(1,'A')]),('b',[(2,'B')])]),[{1:.3},{2:.7}])
