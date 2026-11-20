"""Independent metric checks; real-checkpoint HTTP smoke is recorded separately."""
import unittest
import numpy as np
from evaluate_calibration import user_metrics,aggregate,evaluate_cache,paired_comparison

class CalibrationEvaluationTests(unittest.TestCase):
    def test_hand_calculated_ranking_metrics(self):
        entry={'truth':{0,2},'items':np.array([0,1,2]),'tier':np.array([0,1,2]),
               'target':np.array([1,1,0]),'profile_items':np.array([0,1]),'group':'LowPop'}
        m=user_metrics(entry,[0,1],np.array([1,2,3]),2)
        self.assertEqual(m['Recall@K'],.5);self.assertEqual(m['Precision@K'],.5)
        self.assertEqual(m['HitRate@K'],1.)
        self.assertAlmostEqual(m['NDCG@K'],1/(1+1/np.log2(3)))
        self.assertEqual(m['PopularityJSD'],0.)
        self.assertEqual(aggregate([],3),{'users':0,'metrics':None})

    def test_single_tier_means_calibration_cannot_change_mix(self):
        entry={'truth':{0},'items':np.array([0,1,2]),'tier':np.array([2,2,2]),
               'target':np.array([1.,0,0]),'profile_items':np.array([0]),
               'relevance':np.array([1.,.5,0.]),'group':'LowPop'}
        summary,users=evaluate_cache({0:entry},np.array([1,2,3]),2,{'LowPop':1.},{0:2})
        self.assertEqual(users['CausalEPP'][0]['recommendations'],users['CP_H'][0]['recommendations'])
        self.assertEqual(summary['CP_H']['All']['metrics']['PopularityJSD'],1.)
        c=paired_comparison(users)
        self.assertEqual(c['CP_H']['NDCG@K']['absolute_delta'],0.)
        self.assertEqual(c['CP_H']['NDCG@K']['paired_bootstrap_95_percent_interval'],[0.,0.])


class RecommendationApiTests(unittest.TestCase):
    def test_http_existing_new_and_invalid_users(self):
        import hashlib,json,tempfile,threading,urllib.request,urllib.error
        from pathlib import Path
        from http.server import HTTPServer
        import pandas as pd
        import torch
        from config import Config
        from models import CausalEPP
        from data.popularity import compute_local_popularity,compute_evolving_personal_popularity
        from compare_backbones import data_fingerprints
        from recommendation_api import RecommendationService,handler
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'data';data.mkdir()
            cols=['user','item','rating','timestamp','time_bin']
            tr=pd.DataFrame([(u,u+4*b,5.,float(10*b+u),b) for b in range(2) for u in range(4)],columns=cols)
            tr.to_csv(data/'train_data.csv',sep='\t',index=False)
            for name,offset,time in [('val',1,20),('test',2,30)]:
                pd.DataFrame([(u,(u+offset)%4,5.,float(time+u),1) for u in range(4)],columns=cols).to_csv(data/f'{name}_data.csv',sep='\t',index=False)
            p=compute_local_popularity(tr,2,8)
            np.save(data/'item_local_popularity.npy',p)
            np.save(data/'user_epp.npy',compute_evolving_personal_popularity(tr,p,4,num_time_bins=2))
            np.save(data/'time_bin_edges.npy',[0.,10.,14.])
            pd.DataFrame({'item':range(8),'raw_item':[str(i) for i in range(8)]}).to_csv(data/'item_mapping.csv',index=False)
            c=Config();c.embedding_dim=4;c.lightgcn_layers=1;c.mlp_hidden_dim=2
            model=CausalEPP(4,8,4,1,2,c.alpha);checkpoint=root/'model.pt'
            torch.save({'model':model.state_dict(),'config':c.__dict__,'num_users':4,'num_items':8},checkpoint)
            report={'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                    'data_fingerprints':data_fingerprints(data),'forecast_method':'moving_average','candidate_pool':8,
                    'results':{'2':{'fit':{'lambdas':{'LowPop':.5,'MedPop':.5,'HighPop':.5},'thresholds':[.5,2.]}}}}
            report_file=root/'calibration.json';report_file.write_text(json.dumps(report))
            # A deployed inference snapshot must not require held-out labels.
            heldout={name:(data/name).read_bytes() for name in ['val_data.csv','test_data.csv']}
            for name in heldout:(data/name).unlink()
            service=RecommendationService(checkpoint,data,report_file,1)
            for name,content in heldout.items():(data/name).write_bytes(content)
            self.assertEqual(service.recommend(0,k=1,mode='CausalEPP')['popularity_group'],
                             service.recommend(0,k=2,mode='CP_H')['popularity_group'])
            server=HTTPServer(('127.0.0.1',0),handler(service))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                url=f'http://127.0.0.1:{server.server_address[1]}'
                with urllib.request.urlopen(url+'/health') as response:self.assertEqual(response.status,200)
                for payload in [{'user_id':0,'k':2,'mode':'CP_H'},
                                {'user_id':100,'k':2,'mode':'CP_H'},
                                {'user_id':None,'history_items':[0,4],'k':2,'mode':'CP_Im'}]:
                    request=urllib.request.Request(url+'/recommend',json.dumps(payload).encode(),{'Content-Type':'application/json'})
                    with urllib.request.urlopen(request) as response:r=json.load(response)
                    ids=[x['item_id'] for x in r['recommendations']]
                    self.assertEqual(len(ids),2);self.assertEqual(len(set(ids)),2)
                    self.assertFalse(set(ids)&set(payload.get('history_items',[])))
                    if payload['user_id']==0:self.assertFalse(set(ids)&{0,4})
                    else:self.assertTrue(r['new_user'])
                    if payload['user_id']==100:self.assertEqual(r['applied_calibration_weight'],0.)
                request=urllib.request.Request(url+'/recommend',b'{"user_id":-1}',{'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
                self.assertEqual(error.exception.code,400)
            finally:server.shutdown();worker.join();server.server_close()
            # Exercise the complete training -> calibration -> test CLI on tiny data.
            import subprocess,sys
            result=subprocess.run([sys.executable,'-B','run_lightgcn_calibration.py',
                '--data-dir',str(data),'--output',str(root/'fresh'),'--epochs','1',
                '--k','2','--candidate-pool','8','--threads','1'],
                capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            fresh=json.loads((root/'fresh/evaluation/comparison.json').read_text())
            self.assertEqual(fresh['results']['2']['evaluated_users'],4)
            self.assertIn('Training dataset fingerprints verified.',fresh['limitations'])

if __name__=='__main__':unittest.main()
