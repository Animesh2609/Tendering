"""End-to-end tiny synthetic comparison; not evidence of recommendation quality."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
from data.popularity import compute_local_popularity, compute_evolving_personal_popularity
from llm_embedding_baseline import mapping_digest
from compare_backbones import compare_results,read_cache


class ComparisonTests(unittest.TestCase):
    def test_zero_baseline_and_regression(self):
        r=compare_results([{'seed':42,'lightgcn':{'CausalEPP':{'NDCG@K':0.,'Recall@K':.5}},
                          'llm':{'CausalEPP':{'NDCG@K':.2,'Recall@K':.25}}}])
        self.assertIsNone(r['per_seed'][0]['relative_change_percent'])
        self.assertEqual(r['per_seed'][1]['relative_change_percent'],-50.)

    def test_train_compare_reload_and_guards(self):
        Path('work/comparison_tests').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir='work/comparison_tests') as directory:
            root=Path(directory);data=root/'data';data.mkdir()
            columns=['user','item','rating','timestamp','time_bin']
            tr=pd.DataFrame([(u,(u*4+t)%24,5.,float(t*100+u),t)
                             for t in range(12) for u in range(6)],columns=columns)
            for name,offset,stamp in [('train',None,None),('val',12,1300),('test',13,1400)]:
                d=tr if offset is None else pd.DataFrame([(u,(u*4+offset)%24,5.,float(stamp+u),11)
                                                        for u in range(6)],columns=columns)
                d.to_csv(data/f'{name}_data.csv',sep='\t',index=False)
            p=compute_local_popularity(tr,12,24)
            np.save(data/'item_local_popularity.npy',p)
            np.save(data/'user_epp.npy',compute_evolving_personal_popularity(tr,p,6,num_time_bins=12))
            np.save(data/'time_bin_edges.npy',np.arange(13)*100.)
            mapping=pd.DataFrame({'item':np.arange(24),'raw_item':[f'fixture {i}' for i in range(24)]})
            mapping.to_csv(data/'item_mapping.csv',index=False)
            meta={'complete':True,'mapping_sha256':mapping_digest(mapping),'source':'SYNTHETIC TEST ONLY'}
            cache=root/'vectors.npz'
            np.savez(cache,embeddings=np.random.default_rng(42).normal(size=(24,12)).astype('float32'),
                     item_ids=np.arange(24),metadata=json.dumps(meta))
            partial=root/'partial.npz'
            np.savez(partial,embeddings=np.ones((24,12)),item_ids=np.arange(24),metadata=json.dumps({**meta,'complete':False}))
            with self.assertRaises(ValueError):read_cache(partial,data,24)
            out=root/'experiment'
            command=[sys.executable,'-B','compare_backbones.py','run','--data-dir',str(data),
                     '--cache',str(cache),'--output',str(out),'--epochs','1','--seeds','42',
                     '--dim','8','--layers','1','--k','3','--candidate-pool','12',
                     '--batch-size','72','--threads','1']
            proc=subprocess.run(command,capture_output=True,text=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            report=json.loads((out/'comparison.json').read_text())
            self.assertEqual({r['mode'] for r in report['per_seed']},{'CausalEPP','CP_H','CP_Im'})
            self.assertTrue((out/'comparison.csv').exists())
            for backend in ['lightgcn','llm']:
                run=out/'seed_42'/backend;result=root/f'{backend}_evaluation.json'
                cmd=[sys.executable,'-B','compare_backbones.py','evaluate','--run-dir',str(run),'--output',str(result),'--threads','1']
                proc=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
                self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
                restored=json.loads(result.read_text())
                self.assertEqual(restored['CausalEPP'],json.loads((run/'test_metrics.json').read_text()))
                self.assertEqual(restored['calibrated'],json.loads((run/'popularity_calibrated_test_metrics.json').read_text()))
            # Modified data must not silently be accepted for checkpoint evaluation.
            with (data/'test_data.csv').open('a') as f:f.write('\n')
            proc=subprocess.run([sys.executable,'-B','compare_backbones.py','evaluate',
                 '--run-dir',str(run),'--output',str(root/'mismatch.json')],capture_output=True,text=True,timeout=30)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('Dataset hashes differ',proc.stderr)

if __name__=='__main__':unittest.main()
