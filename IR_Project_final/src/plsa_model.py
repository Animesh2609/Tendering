"""From-scratch PLSA model trained with the EM algorithm."""

import numpy as np
from scipy.sparse import csr_matrix


class PLSA:
    """PLSA trained directly with NumPy EM and sparse input counts."""

    def __init__(self, n_topics=5, max_iter=100, tol=1e-4,
                 random_state=42, beta=1.0):
        if n_topics < 1:
            raise ValueError("n_topics must be positive")
        if not (0 < beta):
            raise ValueError("beta must be positive")
        self.n_topics = n_topics
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state
        self.beta = beta
        self.log_likelihoods = []

    @staticmethod
    def _normalize(a, axis):
        denom = np.maximum(a.sum(axis=axis, keepdims=True), 1e-15)
        return a / denom

    @staticmethod
    def _observations(X):
        X = csr_matrix(X, dtype=np.float64)
        X.eliminate_zeros()
        X.sum_duplicates()
        docs, words, counts = [], [], []
        for d in range(X.shape[0]):
            start, end = X.indptr[d], X.indptr[d + 1]
            if end > start:
                docs.append(np.full(end - start, d, dtype=np.int64))
                words.append(X.indices[start:end].astype(np.int64))
                counts.append(X.data[start:end].astype(np.float64))
        if not docs:
            raise ValueError("Input has no observed word counts.")
        return X, np.concatenate(docs), np.concatenate(words), np.concatenate(counts)

    def fit(self, X):
        X, doc_ids, word_ids, counts = self._observations(X)
        n_documents, n_words = X.shape
        n_topics = self.n_topics
        rng = np.random.default_rng(self.random_state)

        theta = self._normalize(rng.random((n_documents, n_topics)) + 1e-3, axis=1)
        phi = self._normalize(rng.random((n_topics, n_words)) + 1e-3, axis=1)
        self.log_likelihoods = []

        for iteration in range(self.max_iter):
            unnormalized = theta[doc_ids].T * phi[:, word_ids]
            if self.beta != 1.0:
                unnormalized = np.maximum(unnormalized, 1e-15) ** self.beta
            posterior = unnormalized / np.maximum(
                unnormalized.sum(axis=0, keepdims=True), 1e-15
            )

            weighted = posterior * counts[None, :]
            topic_word = np.zeros((n_topics, n_words), dtype=np.float64)
            doc_topic = np.zeros((n_documents, n_topics), dtype=np.float64)
            for topic in range(n_topics):
                np.add.at(topic_word[topic], word_ids, weighted[topic])
                np.add.at(doc_topic[:, topic], doc_ids, weighted[topic])

            phi = self._normalize(topic_word + 1e-12, axis=1)
            theta = self._normalize(doc_topic + 1e-12, axis=1)

            p_observed = np.sum(theta[doc_ids] * phi[:, word_ids].T, axis=1)
            log_likelihood = float(
                np.sum(counts * np.log(np.maximum(p_observed, 1e-15)))
            )
            self.log_likelihoods.append(log_likelihood)

            if iteration > 0:
                improvement = log_likelihood - previous_ll
                if self.beta == 1.0 and improvement < -1e-7:
                    print("Warning: likelihood decreased slightly; check numerical behavior.")
                if abs(improvement) <= self.tol * (1 + abs(previous_ll)):
                    break
            previous_ll = log_likelihood

        self.theta_ = theta
        self.phi_ = phi
        self.n_features_in_ = n_words
        self.n_iter_ = len(self.log_likelihoods)
        return self

    def transform(self):
        """Return document-topic probabilities for the fitted documents."""
        return self.theta_

    def fold_in(self, X_new, max_iter=100):
        """Infer P(z|d_new) while keeping the learned topic-word matrix fixed."""
        X_new = csr_matrix(X_new, dtype=np.float64)
        if X_new.shape[1] != self.n_features_in_:
            raise ValueError("New data must use the same fitted vocabulary.")
        n_documents, _ = X_new.shape
        n_topics = self.n_topics
        rng = np.random.default_rng(self.random_state + 1000)
        theta = self._normalize(rng.random((n_documents, n_topics)) + 1e-3, axis=1)

        for _ in range(max_iter):
            doc_topic = np.zeros((n_documents, n_topics), dtype=np.float64)
            for document in range(n_documents):
                start, end = X_new.indptr[document], X_new.indptr[document + 1]
                words = X_new.indices[start:end]
                counts = X_new.data[start:end]
                if len(words) == 0:
                    continue
                unnormalized = theta[document, :, None] * self.phi_[:, words]
                if self.beta != 1.0:
                    unnormalized = np.maximum(unnormalized, 1e-15) ** self.beta
                posterior = unnormalized / np.maximum(
                    unnormalized.sum(axis=0, keepdims=True), 1e-15
                )
                doc_topic[document] = (posterior * counts[None, :]).sum(axis=1)
            theta = self._normalize(doc_topic + 1e-12, axis=1)
        return theta

    def top_words(self, vocabulary, n=10):
        """Return the top ``n`` word/probability pairs for each topic."""
        result = {}
        for topic, distribution in enumerate(self.phi_):
            ids = np.argsort(distribution)[::-1][:n]
            result[topic] = [
                (vocabulary[i], float(distribution[i])) for i in ids
            ]
        return result


def train_plsa_restarts(X, n_topics=5, n_restarts=5,
                        max_iter=100, tol=1e-4, base_seed=42):
    """Fit independent PLSA initializations and return the best training fit."""
    if n_restarts < 1:
        raise ValueError("n_restarts must be at least 1")
    runs = []
    for restart in range(n_restarts):
        model = PLSA(
            n_topics=n_topics,
            max_iter=max_iter,
            tol=tol,
            random_state=base_seed + restart,
            beta=1.0,
        ).fit(X)
        final_ll = model.log_likelihoods[-1]
        runs.append((model, final_ll))
        print(
            f"Restart {restart + 1}: final training log-likelihood={final_ll:.3f}, "
            f"iterations={model.n_iter_}"
        )
    best_model, best_ll = max(runs, key=lambda item: item[1])
    print("Selected best training likelihood:", round(best_ll, 3))
    return best_model, runs
