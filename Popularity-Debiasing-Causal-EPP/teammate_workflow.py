"""Run Karan's three original non-LLM modes with isolated, auditable outputs."""
import argparse
import contextlib
import json
from pathlib import Path
import time
import traceback
import torch
from config import Config
from train import train
from compare_backbones import data_fingerprints


def run_modes(data_dir,output,epochs,modes,threads=2,seed=42):
    if epochs<1 or threads<1:raise ValueError('epochs and threads must be positive.')
    root=Path(output)
    if root.exists():raise FileExistsError('Choose a new output directory; previous outputs are preserved.')
    fingerprints=data_fingerprints(data_dir)
    root.mkdir(parents=True);torch.set_num_threads(threads);runs=[]
    for mode in modes:
        if mode not in ['moving_average','holt','calibration']:raise ValueError('Unknown mode: '+mode)
        c=Config();c.data_dir=str(Path(data_dir).resolve());c.dataset=Path(data_dir).name
        c.output_dir=str(root/mode);c.epochs=epochs;c.device='cpu';c.seed=seed
        c.forecast_method='holt' if mode=='holt' else 'moving_average'
        c.enable_popularity_calibration=mode=='calibration';c.data_fingerprints=fingerprints
        record={'mode':mode,'config':c.__dict__,'exit_code':0,'status':'PASS_EXECUTION_ONLY'}
        start=time.perf_counter()
        with (root/f'{mode}.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            try:
                _,metrics,_,_=train(c);record['metrics']=metrics
                if mode=='calibration':
                    record['calibrated_metrics']=json.loads((Path(c.output_dir)/'popularity_calibrated_test_metrics.json').read_text())
            except Exception as exc:
                record.update(exit_code=1,status='FAIL',error=repr(exc));traceback.print_exc()
        record['seconds']=time.perf_counter()-start;runs.append(record)
        (root/'execution_summary.json').write_text(json.dumps(runs,indent=2))
        print(mode,record['status'],f"{record['seconds']:.2f}s",flush=True)
        if data_fingerprints(data_dir)!=fingerprints:raise RuntimeError('Input data changed during execution.')
        if record['exit_code']:break
    return runs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',default='data/Ciao');p.add_argument('--output',required=True)
    p.add_argument('--epochs',required=True,type=int)
    p.add_argument('--mode',choices=['all','moving_average','holt','calibration'],default='all')
    p.add_argument('--threads',type=int,default=2);p.add_argument('--seed',type=int,default=42)
    a=p.parse_args();modes=['moving_average','holt','calibration'] if a.mode=='all' else [a.mode]
    runs=run_modes(a.data_dir,a.output,a.epochs,modes,a.threads,a.seed)
    raise SystemExit(any(r['exit_code'] for r in runs))

if __name__=='__main__':main()
