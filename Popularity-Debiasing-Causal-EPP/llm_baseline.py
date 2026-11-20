"""Local Hugging Face matching scores used as CausalEPP's m_ui term."""

import json
from pathlib import Path
import re

import numpy as np
import torch


class LocalHuggingFaceScorer:
    """Generate deterministic numeric user-item scores with a local HF model."""

    def __init__(self, model_id, device="auto"):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "The local LLM needs transformers and accelerate. Install the "
                "project requirements, then rerun."
            ) from exc

        if device == "auto":
            use_cuda = torch.cuda.is_available()
        elif device == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("llm_device is cuda, but CUDA is unavailable.")
            use_cuda = True
        elif device == "cpu":
            use_cuda = False
        else:
            raise ValueError("llm_device must be 'auto', 'cpu', or 'cuda'.")

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        load_options = {"torch_dtype": "auto" if use_cuda else torch.float32}
        if use_cuda:
            load_options["device_map"] = "auto"
        self.model = AutoModelForCausalLM.from_pretrained(model_id, **load_options)
        if not use_cuda:
            self.model.to("cpu")
        self.model.eval()
        self.device = self.model.device

    @staticmethod
    def _parse_scores(text, candidate_ids):
        # Accept a complete JSON object or recover numeric pairs from truncated JSON.
        match = re.search(r"\{[\s\S]*\}", text)
        raw = {}
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    raw = parsed
            except json.JSONDecodeError:
                pass
        if not raw:
            pairs = re.findall(
                r'["\']?(\d+)["\']?\s*:\s*'
                r'(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)',
                text,
            )
            raw = {item_id: value for item_id, value in pairs}

        scores = {}
        for item_id in candidate_ids:
            value = raw.get(str(item_id), raw.get(item_id))
            if value is None:
                continue
            value = float(value)
            if not np.isfinite(value):
                continue
            scores[int(item_id)] = float(np.clip(value, 0.0, 1.0))
        return scores

    def score(self, profile, candidates):
        """Return one 0-1 relevance score for every (item_id, item_name)."""
        pending = list(candidates)
        scores = {}
        for attempt in range(3):
            candidate_text = "\n".join(
                f"{item_id}\t{name.replace(chr(9), ' ').replace(chr(10), ' ')}"
                for item_id, name in pending
            )
            prompt = (
                "Score how relevant each candidate item is for the user, using only "
                "the user's previous item titles. Return exactly one score from 0.0 "
                "to 1.0 for every candidate ID. Return only a JSON object with item "
                "IDs as keys and numeric scores as values. Do not explain. /no_think\n\n"
                f"User's past item titles, oldest first:\n{profile}\n\n"
                f"Candidates, ID then title:\n{candidate_text}"
            )
            formatted_prompt = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                add_generation_prompt=True,
                tokenize=False,
            )
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
            inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
            with torch.inference_mode():
                generated = self.model.generate(
                    **inputs,
                    max_new_tokens=max(512, len(pending) * 12),
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            response = self.tokenizer.decode(
                generated[0, inputs["input_ids"].shape[-1]:],
                skip_special_tokens=True,
            )
            scores.update(self._parse_scores(
                response, [item for item, _ in pending]
            ))
            pending = [row for row in pending if row[0] not in scores]
            if not pending:
                break
            if attempt < 2:
                print(
                    f"LLM omitted {len(pending)} item score(s); "
                    f"retrying them (attempt {attempt + 2}/3)."
                )

        if pending:
            print(
                f"Warning: LLM still omitted {len(pending)} item score(s) "
                "after retries; assigning neutral score 0.5 to those items."
            )
            scores.update({item_id: 0.5 for item_id, _ in pending})
        return scores


def build_llm_matching_scores(config, train_df, val_df, test_df, num_items):
    """Score user-specific candidate pools once and persist scores for reuse.

    Candidate pools contain each user's training positives and globally popular
    training items until at least the configured pool size is reached. The
    saved scores are reused across every epoch, validation, and test evaluation.
    """
    import pandas as pd

    data_dir = Path(config.data_dir)
    mapping_path = data_dir / "item_mapping.csv"
    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Item title mapping is required for LLM matching: {mapping_path}"
        )
    item_mapping = pd.read_csv(mapping_path)
    if not {"item", "raw_item"}.issubset(item_mapping.columns):
        raise ValueError("item_mapping.csv must contain item and raw_item columns.")
    item_names = dict(zip(
        item_mapping["item"].astype(int),
        item_mapping["raw_item"].astype(str),
    ))

    item_counts = train_df["item"].value_counts().reindex(
        range(num_items), fill_value=0
    )
    popular_items = item_counts.sort_values(ascending=False).index.tolist()
    all_users = set(train_df["user"].astype(int))
    all_users.update(val_df["user"].astype(int))
    all_users.update(test_df["user"].astype(int))
    user_histories = {
        int(user): rows.sort_values("timestamp")["item"].astype(int).tolist()
        for user, rows in train_df.groupby("user")
    }

    cache_path = Path(config.output_dir) / "llm_matching_scores.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        saved = json.loads(cache_path.read_text())
        score_cache = {
            int(user): {int(item): float(score) for item, score in scores.items()}
            for user, scores in saved.items()
        }
    else:
        score_cache = {}

    scorer = LocalHuggingFaceScorer(config.llm_model_id, config.llm_device)
    candidate_cache = {}
    pool_size = max(int(config.llm_candidate_pool), 1)
    for index, user in enumerate(sorted(all_users), start=1):
        positives = set(user_histories.get(user, []))
        candidates = set(positives)
        for item in popular_items:
            candidates.add(int(item))
            if len(candidates) >= pool_size:
                break
        candidate_ids = sorted(candidates)
        candidate_cache[user] = candidate_ids

        cached_user_scores = score_cache.setdefault(user, {})
        missing = [item for item in candidate_ids if item not in cached_user_scores]
        if missing:
            history = user_histories.get(user, [])[-config.llm_history_length:]
            profile = "\n".join(
                item_names.get(item, f"Item {item}") for item in history
            ) or "No prior item history."
            candidate_rows = [
                (item, item_names.get(item, f"Item {item}")) for item in missing
            ]
            cached_user_scores.update(scorer.score(profile, candidate_rows))
            cache_path.write_text(json.dumps({
                str(uid): {str(item): score for item, score in scores.items()}
                for uid, scores in score_cache.items()
            }))
        if index % 25 == 0 or index == len(all_users):
            print(f"Prepared local LLM scores for {index}/{len(all_users)} users")

    score_cache = {
        user: {item: score_cache[user][item] for item in candidate_ids}
        for user, candidate_ids in candidate_cache.items()
    }
    cache_path.write_text(json.dumps({
        str(user): {str(item): score for item, score in scores.items()}
        for user, scores in score_cache.items()
    }))

    negative_candidates = {}
    for user, candidate_ids in candidate_cache.items():
        positives = set(user_histories.get(user, []))
        negative_candidates[user] = [
            item for item in candidate_ids if item not in positives
        ]
        if user in user_histories and not negative_candidates[user]:
            raise ValueError(
                f"LLM candidate pool for user {user} contains no training negative."
            )

    return score_cache, candidate_cache, negative_candidates, item_names
