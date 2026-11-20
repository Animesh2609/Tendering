"""Explicit timestamped interaction adapter to the existing processed Ciao schema.

Does not download data or guess a Douban distribution's raw format.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from data.preprocess import _k_core,_chronological_split,_assign_training_time_bins
from data.popularity import compute_local_popularity,compute_evolving_personal_popularity


def prepare(args):
    destination=Path(args.output)
    if destination.exists():raise FileExistsError('Use a new output directory.')
    if min(args.min_user,args.min_item,args.bins)<1:raise ValueError('Core thresholds and bins must be positive.')
    separator='\t' if args.sep==r'\t' else args.sep
    raw=pd.read_csv(args.input,sep=separator,header=None if args.no_header else 0,dtype=str,
                    engine='python' if len(separator)>1 else 'c')
    def column(name):return int(name) if args.no_header else name
    mapping={'user':column(args.user_col),'item':column(args.item_col),
             'rating':column(args.rating_col),'timestamp':column(args.time_col)}
    missing=[v for v in mapping.values() if v not in raw.columns]
    if missing:raise ValueError('Missing source columns: '+str(missing))
    data=pd.DataFrame({name:raw[col] for name,col in mapping.items()})
    data['rating']=pd.to_numeric(data.rating,errors='coerce')
    if args.timestamp_unit:
        dates=pd.to_datetime(pd.to_numeric(data.timestamp,errors='coerce'),unit=args.timestamp_unit,utc=True,errors='coerce')
    else:dates=pd.to_datetime(data.timestamp,format=args.date_format,utc=True,errors='coerce')
    valid=data.user.notna() & data.item.notna() & data.rating.notna() & dates.notna()
    valid &= data.user.fillna('').str.strip().ne('') & data.item.fillna('').str.strip().ne('')
    valid &= np.isfinite(data.rating.to_numpy(dtype=float))
    invalid=int((~valid).sum())
    if invalid and not args.drop_invalid:raise ValueError(f'{invalid} invalid rows; correct the mapping or explicitly use --drop-invalid.')
    data=data.loc[valid].copy();dates=dates.loc[valid]
    # Explicit units avoid the original pandas-us/ns timestamp conversion bug.
    data['timestamp']=dates.dt.as_unit('ns').astype('int64')//10**9
    data=_k_core(data,args.min_user,args.min_item)
    if data.empty:raise ValueError('No interactions remain after filtering.')
    users=sorted(data.user.unique());items=sorted(data.item.unique())
    um={v:i for i,v in enumerate(users)};im={v:i for i,v in enumerate(items)}
    data['user']=data.user.map(um).astype('int64');data['item']=data.item.map(im).astype('int64')
    data=data.sort_values(['timestamp','user','item']).reset_index(drop=True)
    train,val,test=_chronological_split(data)
    warm_users=set(train.user);warm_items=set(train.item)
    before={'val':len(val),'test':len(test)}
    val=val[val.user.isin(warm_users)&val.item.isin(warm_items)].copy()
    test=test[test.user.isin(warm_users)&test.item.isin(warm_items)].copy()
    if train.empty or val.empty or test.empty:raise ValueError('Insufficient chronological warm-start train/validation/test interactions.')
    if train.timestamp.max()>=val.timestamp.min() or val.timestamp.max()>=test.timestamp.min():
        raise ValueError('Tied timestamps prevent strictly separated splits; supply higher-resolution dates or revise the split explicitly.')
    train,data,edges=_assign_training_time_bins(train,data,args.bins)
    for frame in [val,test]:frame['time_bin']=np.searchsorted(edges[1:-1],frame.timestamp,side='right').clip(0,args.bins-1)
    pop=compute_local_popularity(train,args.bins,len(items))
    epp=compute_evolving_personal_popularity(train,pop,len(users),num_time_bins=args.bins)
    destination.mkdir(parents=True)
    for name,frame in [('all',data),('train',train),('val',val),('test',test)]:
        frame.to_csv(destination/f'{name}_data.csv',sep='\t',index=False)
    pd.DataFrame({'raw_user':users,'user':range(len(users))}).to_csv(destination/'user_mapping.csv',index=False)
    pd.DataFrame({'raw_item':items,'item':range(len(items))}).to_csv(destination/'item_mapping.csv',index=False)
    np.save(destination/'item_local_popularity.npy',pop);np.save(destination/'user_epp.npy',epp)
    np.save(destination/'time_bin_edges.npy',edges)
    meta={'source_sha256':hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
          'source_rows':len(raw),'invalid_rows_dropped':invalid,'filtered_rows':len(data),
          'users':len(users),'items':len(items),'train_rows':len(train),'val_rows':len(val),'test_rows':len(test),
          'cold_rows_dropped':{n:before[n]-len(f) for n,f in [('val',val),('test',test)]},
          'timestamp_unit':'Unix seconds UTC','source_columns':mapping,'min_user':args.min_user,'min_item':args.min_item,
          'bins':args.bins,'split':'Original global chronological 90% timestamp quantile, remaining median; warm-start holdout.',
          'limitations':['Fixed-bin features retain original implementation, not paper sliding windows.',
                         'Full-data k-core and ID mapping retain original transductive protocol.',
                         'raw_item contains source IDs, not semantic item titles; unsuitable for text LLM input without enrichment.',
                         'Schema compatibility does not establish Douban paper reproduction.']}
    (destination/'preprocessing_manifest.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2));return meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    p.add_argument('--sep',default=',');p.add_argument('--no-header',action='store_true')
    p.add_argument('--user-col',required=True);p.add_argument('--item-col',required=True)
    p.add_argument('--rating-col',required=True);p.add_argument('--time-col',required=True)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--timestamp-unit',choices=['s','ms','us','ns']);group.add_argument('--date-format')
    p.add_argument('--min-user',type=int,default=10);p.add_argument('--min-item',type=int,default=10)
    p.add_argument('--bins',type=int,default=100);p.add_argument('--drop-invalid',action='store_true')
    prepare(p.parse_args())

if __name__=='__main__':main()
