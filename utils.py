import re
from typing import List

def sanitize_folder_name(name: str) -> str:
    # basitçe illegal karakterleri değiştir
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.strip()[:200]
    return name or "cluster"

def top_keywords_from_vectorizer(vectorizer, tfidf_matrix, cluster_labels, cluster_id, top_n=3):
    # cluster için en yüksek ortalama tfidf değerine sahip terimleri döndür
    import numpy as np
    mask = cluster_labels == cluster_id
    if not mask.any():
        return []
    cluster_tfidf = tfidf_matrix[mask].mean(axis=0).A1  # dense array
    top_indices = cluster_tfidf.argsort()[::-1][:top_n]
    features = vectorizer.get_feature_names_out()
    return [features[i] for i in top_indices if cluster_tfidf[i] > 0]
