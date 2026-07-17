"""Unit tests for src/models/train.py: playstyle cluster labeling."""

import numpy as np
from sklearn.cluster import KMeans

from src.models.train import FEATURE_COLUMNS, label_clusters


def _kmeans_with_centers(centers: np.ndarray) -> KMeans:
    km = KMeans(n_clusters=len(centers))
    km.cluster_centers_ = centers
    return km


def test_label_clusters_names_top_two_features_per_centroid():
    n_features = len(FEATURE_COLUMNS)
    center_0 = np.full(n_features, 0.1)
    center_0[0], center_0[1] = 2.0, 1.5  # xg_per_90, xa_per_90 dominate

    center_1 = np.full(n_features, 0.1)
    center_1[4], center_1[5] = 2.0, 1.5  # key_passes_per_90, xg_chain_per_90 dominate

    kmeans = _kmeans_with_centers(np.array([center_0, center_1]))

    labels = label_clusters(kmeans, scaler=None)

    assert labels[0] == "Cluster 0: high xg, xa"
    assert labels[1] == "Cluster 1: high key passes, xg chain"


def test_label_clusters_covers_every_cluster_id():
    kmeans = _kmeans_with_centers(np.random.default_rng(0).normal(size=(4, len(FEATURE_COLUMNS))))
    labels = label_clusters(kmeans, scaler=None)
    assert set(labels.keys()) == {0, 1, 2, 3}
