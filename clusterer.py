from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
from typing import List, Tuple

class MdClusterer:
    def __init__(self, n_clusters=5, max_features=10000):
        self.n_clusters = n_clusters
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english', ngram_range=(1,2))

    def fit_predict(self, docs: List[str], requested_clusters: int = None) -> Tuple[np.ndarray, object]:
        if requested_clusters is None:
            k = self.n_clusters
        else:
            k = requested_clusters
        k = min(max(1, k), len(docs))
        X = self.vectorizer.fit_transform(docs)
        if len(docs) == 1:
            labels = np.array([0])
            model = None
            return labels, (model, X)
        km = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = km.fit_predict(X)
        return labels, (km, X)
