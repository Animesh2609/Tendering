"""Train LightGCN+CausalEPP once, then evaluate with/without calibration.

CPU only. Epochs must be explicit; outputs must be new. No LLM downloads.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from config import Config
from train import train
from compare_backbones import data_fingerprints
from evaluate_calibration import run as evaluate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',default='data/Ciao');p.add_argument('--output',required=True)
    p.add_argument('--epochs',type=int,required=True);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--forecast-method',choices=['moving_average','holt'],default='moving_average')
    p.add_argument('--k',type=int,nargs='+',default=[10,20])
    p.add_argument('--candidate-pool',type=int,default=150);p.add_argument('--threads',type=int,default=2)
    a=p.parse_args()
    if a.epochs<1 or a.threads<1 or min(a.k)<1 or a.candidate_pool<max(a.k):p.error('Invalid positive limits.')
    root=Path(a.output)
    if root.exists():raise FileExistsError('Use a new output directory.')
    c=Config();c.data_dir=str(Path(a.data_dir).resolve());c.output_dir=str(root/'training')
    c.device='cpu';c.epochs=a.epochs;c.seed=a.seed;c.forecast_method=a.forecast_method
    c.enable_popularity_calibration=False;c.eval_k=max(a.k)
    c.data_fingerprints=data_fingerprints(c.data_dir)
    torch.set_num_threads(a.threads)
    train(c)
    if data_fingerprints(c.data_dir)!=c.data_fingerprints:raise RuntimeError('Data changed during training.')
    evaluate(SimpleNamespace(checkpoint=str(Path(c.output_dir)/'causalepp_ciao.pt'),
             data_dir=c.data_dir,output=str(root/'evaluation'),k=a.k,
             candidate_pool=a.candidate_pool,forecast_method=a.forecast_method,threads=a.threads))
    (root/'run_config.json').write_text(json.dumps(c.__dict__,indent=2))

if __name__=='__main__':main()
