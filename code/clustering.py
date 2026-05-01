# clustering.py
#
# K-Means clustering for delivery zone partitioning.
#
# Why clustering fits this problem:
#   When multiple deliveries are spread across a large map, grouping them
#   into geographic zones means each "car" only covers its own cluster.
#   This avoids sending one car across the entire graph.
#
# How it works here:
#   1. Represent each destination node by its (x, y) canvas coordinates.
#   2. Run K-Means to find k cluster centroids.
#   3. Assign each destination to its nearest centroid → k delivery zones.
#   4. Each zone is routed independently (UCS+CSP within the zone).
#
# This is unsupervised learning applied to spatial routing decomposition.

import math
import random


def euclidean_2d(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def kmeans(nodes, goal_names, k, max_iter=100, seed=42):
    """
    K-Means clustering on node (x, y) coordinates.

    Parameters
    ----------
    nodes      : dict { name -> Vertex }
    goal_names : list of node names to cluster
    k          : number of clusters (clamped to len(goal_names))
    max_iter   : iteration cap

    Returns
    -------
    clusters : list of lists  [ [node_name, ...], [node_name, ...], ... ]
               Length = k.  Empty clusters are dropped.
    centroids: list of (cx, cy) tuples — one per returned cluster.
    """
    goals = list(goal_names)
    k = min(k, len(goals))

    if k <= 1:
        return [goals], [(nodes[g].x, nodes[g].y) for g in goals[:1]]

    # Initialise centroids by picking k distinct goals at random (k-means++)
    rng = random.Random(seed)
    centroids = []
    first = rng.choice(goals)
    centroids.append((nodes[first].x, nodes[first].y))

    for _ in range(k - 1):
        # Pick next centroid with probability proportional to distance²
        dists = []
        for g in goals:
            d2 = min(euclidean_2d(nodes[g].x, nodes[g].y, cx, cy) ** 2
                     for cx, cy in centroids)
            dists.append(d2)
        total = sum(dists)
        if total == 0:
            centroids.append((nodes[rng.choice(goals)].x, nodes[rng.choice(goals)].y))
        else:
            r = rng.uniform(0, total)
            cumul = 0
            for i, d in enumerate(dists):
                cumul += d
                if cumul >= r:
                    centroids.append((nodes[goals[i]].x, nodes[goals[i]].y))
                    break

    # Iterate
    assignments = [0] * len(goals)
    for _ in range(max_iter):
        # Assign each goal to nearest centroid
        new_assignments = []
        for g in goals:
            dists = [euclidean_2d(nodes[g].x, nodes[g].y, cx, cy)
                     for cx, cy in centroids]
            new_assignments.append(dists.index(min(dists)))

        if new_assignments == assignments:
            break                            # converged
        assignments = new_assignments

        # Recompute centroids
        new_centroids = []
        for c in range(k):
            members = [goals[i] for i, a in enumerate(assignments) if a == c]
            if members:
                cx = sum(nodes[g].x for g in members) / len(members)
                cy = sum(nodes[g].y for g in members) / len(members)
                new_centroids.append((cx, cy))
            else:
                new_centroids.append(centroids[c])    # keep old centroid
        centroids = new_centroids

    # Build output clusters (drop empty ones)
    cluster_dict = {}
    for i, g in enumerate(goals):
        c = assignments[i]
        cluster_dict.setdefault(c, []).append(g)

    clusters  = list(cluster_dict.values())
    centroids_out = [centroids[c] for c in cluster_dict]
    return clusters, centroids_out


def auto_k(num_goals):
    """
    Heuristic for choosing k:
      1 goal  → 1 cluster (no clustering needed)
      2-3     → 2 clusters
      4-5     → min(3, num_goals) clusters
    Keeps clusters meaningful on a small graph.
    """
    if num_goals <= 1:
        return 1
    if num_goals <= 3:
        return 2
    return min(3, num_goals)
