"""Experimental frozen-LLM text backbone. No graph propagation or generation.

Preserves CausalEPP.forward/quality_loss and the existing evaluator interface.
Text features are NOT assumed to be trained semantic retrieval embeddings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import torch
from torch import nn
import torch.nn.functional as F
from models import CausalEPP


def mapping_digest(mapping):
    rows = mapping.sort_values('item')[['item', 'raw_item']].to_json(orient='values')
    return hashlib.sha256(rows.encode()).hexdigest()


class TextBackbone(nn.Module):
    def __init__(self, item_vectors, train_df, num_users, dim):
        super().__init__()
        vectors = torch.as_tensor(item_vectors, dtype=torch.float32)
        if vectors.ndim != 2 or not torch.isfinite(vectors).all():
            raise ValueError('Item vectors must be a finite 2D matrix.')
        vectors = F.normalize(vectors, dim=1)
        users = torch.zeros(num_users, vectors.shape[1])
        counts = torch.zeros(num_users, 1)
        # Each training interaction contributes once; held-out histories are excluded.
        ids = torch.tensor(train_df.user.to_numpy(), dtype=torch.long)
        items = torch.tensor(train_df.item.to_numpy(), dtype=torch.long)
        users.index_add_(0, ids, vectors[items])
        counts.index_add_(0, ids, torch.ones(len(ids), 1))
        users = F.normalize(users / counts.clamp_min(1), dim=1)
        self.register_buffer('item_text', vectors)
        self.register_buffer('user_text', users)
        self.user_projection = nn.Linear(vectors.shape[1], dim, bias=False)
        self.item_projection = nn.Linear(vectors.shape[1], dim, bias=False)

    def propagate(self, norm_adj=None):
        # Historical evaluator API name only: no LightGCN or graph operations.
        return self.user_projection(self.user_text), self.item_projection(self.item_text)


class TextCausalEPP(CausalEPP):
    def __init__(self, item_vectors, train_df, num_users, dim=64,
                 mlp_hidden=32, alpha=.5):
        nn.Module.__init__(self)
        self.num_users = num_users
        self.num_items = len(item_vectors)
        self.alpha = alpha
        # Keep the attribute name for existing forward/evaluate/calibration APIs.
        self.lightgcn = TextBackbone(item_vectors, train_df, num_users, dim)
        self.q = nn.Parameter(torch.zeros(self.num_items))
        self.item_mlp = nn.Sequential(nn.Linear(dim, mlp_hidden), nn.ReLU(),
                                      nn.Linear(mlp_hidden, 1))


def encode(args):
    if args.batch_size < 1 or args.max_tokens < 1 or args.max_items < 0:
        raise ValueError('Invalid encoding limits.')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f'Refusing to replace {output}')
    model_path = Path(args.model_path).resolve()
    if not model_path.is_dir():
        raise FileNotFoundError('Provide an existing local Hugging Face model directory.')
    from transformers import AutoModel, AutoTokenizer
    mapping = pd.read_csv(args.mapping).sort_values('item').reset_index(drop=True)
    if not {'item', 'raw_item'}.issubset(mapping.columns):
        raise ValueError('Mapping requires item and raw_item columns.')
    if not np.array_equal(mapping.item.to_numpy(), np.arange(len(mapping))):
        raise ValueError('Mapping IDs must be contiguous, unique and start at zero.')
    selected = mapping if args.max_items == 0 else mapping.head(args.max_items)
    if selected.empty:
        raise ValueError('No item text to encode.')
    torch.set_num_threads(args.threads)
    start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True,
                                             trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        if tokenizer.eos_token_id is None:
            raise ValueError('Tokenizer has neither pad nor EOS token.')
        tokenizer.pad_token = tokenizer.eos_token
    # CPU-only prototype: no implicit GPU job or network downloads.
    model = AutoModel.from_pretrained(model_path, local_files_only=True,
                                     trust_remote_code=False).to('cpu').eval()
    loaded = time.perf_counter()
    vectors = []
    with torch.inference_mode():
        for first in range(0, len(selected), args.batch_size):
            titles = selected.raw_item.iloc[first:first + args.batch_size].fillna('').astype(str)
            tokens = tokenizer(titles.tolist(), padding=True, truncation=True,
                               max_length=args.max_tokens, return_tensors='pt')
            hidden = model(**tokens, use_cache=False).last_hidden_state
            # Last nonpadding token works with either padding side for a causal LM.
            mask = tokens['attention_mask'].bool()
            positions = torch.arange(mask.shape[1]).expand_as(mask).masked_fill(~mask, -1).max(1).values
            if (positions < 0).any():
                raise ValueError('Empty token sequence.')
            batch = hidden[torch.arange(len(hidden)), positions].float()
            vectors.append(F.normalize(batch, dim=1).cpu().numpy())
    values = np.concatenate(vectors)
    if not np.isfinite(values).all():
        raise ValueError('Encoder produced nonfinite vectors.')
    metadata = dict(model_path=str(model_path), model_class=type(model).__name__,
                    mapping_sha256=mapping_digest(mapping), pooling='last_nonpadding_token',
                    max_tokens=args.max_tokens, item_count=len(values),
                    complete=len(selected) == len(mapping),
                    model_load_seconds=loaded-start,
                    encode_seconds=time.perf_counter()-loaded,
                    torch_version=torch.__version__,
                    model_config=model.config.to_dict())
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects existing caches. Filename need not end in .npz.
    with output.open('xb') as stream:
        np.savez_compressed(stream, embeddings=values,
                            item_ids=selected.item.to_numpy(dtype=np.int64),
                            metadata=json.dumps(metadata))
    print(json.dumps({k:v for k,v in metadata.items() if k != 'model_config'}, indent=2))
    print('Saved:', output)


def run(args):
    from config import Config
    from train import train, load_training_data
    if args.epochs < 1:
        raise ValueError('epochs must be positive.')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f'Use a new output directory: {output}')
    cache_path = Path(args.cache)
    mapping = pd.read_csv(Path(args.data_dir) / 'item_mapping.csv')
    with np.load(cache_path, allow_pickle=False) as cache:
        metadata = json.loads(str(cache['metadata']))
        vectors = cache['embeddings'].copy()
        ids = cache['item_ids'].copy()
    nitems = load_training_data(args.data_dir)[-1]
    if (not metadata.get('complete') or metadata['mapping_sha256'] != mapping_digest(mapping)
            or len(vectors) < nitems or not np.array_equal(ids, np.arange(len(vectors)))):
        raise ValueError('Cache is partial or does not match the dataset item mapping.')
    c = Config()
    c.data_dir = args.data_dir
    c.output_dir = str(output)
    c.device = 'cpu'
    c.epochs = args.epochs
    c.forecast_method = args.forecast_method
    c.enable_popularity_calibration = args.calibrate
    c.matching_backend = 'frozen_llm_text_projections'
    c.text_cache_sha256 = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    c.text_encoder_metadata = metadata
    torch.set_num_threads(args.threads)
    def factory(config, frame, nu, ni, device):
        return TextCausalEPP(vectors[:ni], frame, nu, config.embedding_dim,
                            config.mlp_hidden_dim, config.alpha).to(device), None
    train(c, backend_factory=factory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('encode', help='CPU benchmark; existing local weights only')
    p.add_argument('--model-path', required=True)
    p.add_argument('--mapping', default='data/Ciao/item_mapping.csv')
    p.add_argument('--output', required=True)
    p.add_argument('--max-items', type=int, default=32, help='0 means all items; default is a small benchmark')
    p.add_argument('--batch-size', type=int, default=4)
    p.add_argument('--max-tokens', type=int, default=64)
    p.add_argument('--threads', type=int, default=2)
    p.set_defaults(func=encode)
    p = sub.add_parser('train', help='Train only projections/quality/MLP from complete cached features')
    p.add_argument('--cache', required=True)
    p.add_argument('--data-dir', default='data/Ciao')
    p.add_argument('--output', required=True)
    p.add_argument('--epochs', type=int, required=True)
    p.add_argument('--forecast-method', choices=['moving_average', 'holt'], default='moving_average')
    p.add_argument('--calibrate', action='store_true')
    p.add_argument('--threads', type=int, default=2)
    p.set_defaults(func=run)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be positive')
    args.func(args)


if __name__ == '__main__':
    main()
