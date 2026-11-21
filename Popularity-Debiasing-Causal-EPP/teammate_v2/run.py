"""Opt-in training entry point for the reviewed teammate update."""
import argparse
from pathlib import Path
from config import Config
from teammate_v2.train import train

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',default='data/Ciao')
    p.add_argument('--output',required=True)
    p.add_argument('--epochs',required=True,type=int)
    p.add_argument('--forecast-method',choices=['moving_average','holt'],default='moving_average')
    p.add_argument('--calibrate',action='store_true')
    p.add_argument('--llm-baseline',action='store_true')
    p.add_argument('--llm-model-path')
    a=p.parse_args()
    if a.epochs<1:p.error('epochs must be positive')
    if Path(a.output).exists():p.error('Use a new output directory to preserve prior runs.')
    if a.llm_baseline and (not a.llm_model_path or not Path(a.llm_model_path).is_dir()):
        p.error('Supply an existing local model directory; this command does not download weights.')
    c=Config();c.data_dir=a.data_dir;c.output_dir=a.output;c.epochs=a.epochs
    c.forecast_method=a.forecast_method;c.enable_popularity_calibration=a.calibrate
    c.use_llm_matching=a.llm_baseline;c.llm_batch_size=4;c.device='cpu';c.llm_device='cpu'
    if a.llm_model_path:c.llm_model_id=a.llm_model_path
    train(c)
if __name__=='__main__':main()
