import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
import pandas as pd
from prepare_douban import prepare
from teammate_workflow import run_modes
from train import load_training_data


class TeammateWorkflowTests(unittest.TestCase):
    def fixture(self,root,unit='s',header=True):
        rows=[]
        for n in range(420):
            u=n%6;step=n//6
            rows.append((f'user{u}',f'item{u*4+step%4}',5,1700000000+n*86400))
        raw=pd.DataFrame(rows,columns=['uid','iid','stars','when'])
        if unit=='ms':raw['when']*=1000
        source=root/f'raw_{unit}_{header}.csv'
        raw.to_csv(source,index=False,header=header,sep=',' if header else '\t')
        return SimpleNamespace(input=str(source),output=str(root/'processed'),sep=',' if header else r'\t',
            no_header=not header,user_col='uid' if header else '0',item_col='iid' if header else '1',
            rating_col='stars' if header else '2',time_col='when' if header else '3',
            timestamp_unit=unit,date_format=None,drop_invalid=False,min_user=1,min_item=1,bins=12)

    def test_adapter_and_all_three_training_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=self.fixture(root);before=Path(a.input).read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):meta=prepare(a)
            self.assertEqual(Path(a.input).read_bytes(),before)
            tr,va,te,edges,p,e,nu,ni=load_training_data(a.output)
            self.assertEqual(tr.timestamp.min(),1700000000)
            self.assertLess(tr.timestamp.max(),va.timestamp.min());self.assertLess(va.timestamp.max(),te.timestamp.min())
            self.assertEqual((nu,ni),(6,24));self.assertEqual(p.shape,(12,24));self.assertEqual(e.shape,(12,6))
            with contextlib.redirect_stdout(io.StringIO()):
                runs=run_modes(a.output,root/'runs',1,['moving_average','holt','calibration'],threads=1)
            self.assertEqual([r['exit_code'] for r in runs],[0,0,0])
            for r in runs:
                self.assertFalse(r['config']['use_llm_matching']);self.assertTrue(all(np.isfinite(x) for x in r['metrics'].values()))
                self.assertTrue((root/'runs'/r['mode']/'causalepp_ciao.pt').exists())
            self.assertIn('calibrated_metrics',runs[2])
            with self.assertRaises(FileExistsError):prepare(a)
            with self.assertRaises(FileExistsError):run_modes(a.output,root/'runs',1,['holt'])

    def test_headerless_millisecond_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=self.fixture(root,'ms',False)
            with contextlib.redirect_stdout(io.StringIO()):prepare(a)
            tr=load_training_data(a.output)[0]
            self.assertEqual(tr.timestamp.min(),1700000000)

    def test_explicit_text_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=self.fixture(root)
            raw=pd.read_csv(a.input)
            raw['when']=pd.to_datetime(raw['when'],unit='s',utc=True).dt.strftime('%Y-%m-%d %H:%M:%S')
            raw.to_csv(a.input,index=False)
            a.timestamp_unit=None;a.date_format='%Y-%m-%d %H:%M:%S'
            with contextlib.redirect_stdout(io.StringIO()):prepare(a)
            self.assertEqual(load_training_data(a.output)[0].timestamp.min(),1700000000)

    def test_invalid_dates_fail_without_silent_dropping(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=self.fixture(root)
            raw=pd.read_csv(a.input,dtype=str);raw.loc[0,'when']='invalid';raw.to_csv(a.input,index=False)
            with self.assertRaisesRegex(ValueError,'invalid rows'):prepare(a)
            self.assertFalse(Path(a.output).exists())

if __name__=='__main__':unittest.main()
