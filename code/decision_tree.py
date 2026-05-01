# Features (all computed before any search runs):
#
#   F1: num_goals          int   — how many destinations are selected
#   F2: has_blocks         bool  — any blocked nodes OR edges exist
#   F3: num_clusters       int   — how many K-Means clusters the goals form
#                                  (run K-Means once cheaply on coordinates)
#   F4: avg_cluster_size   float — avg goals per cluster (spread measure)
#   F5: goals_span         float — bounding box diagonal of all goal coords
#                                  (how geographically spread the goals are)
#
# Decision rules (read as a tree, root → leaves):
#
#                        num_goals == 1?
#                       /              \
#                    YES               NO
#              → SINGLE UCS        num_goals >= 5?
#                                  /             \
#                                YES              NO (2-4)
#                          → CLUSTERED         has_blocks?
#                                             /          \
#                                           YES            NO
#                                 num_clusters >= 2?     goals_span < 200?
#                                    /          \         /             \
#                                  YES           NO     YES              NO
#                             CLUSTERED       UCS+CSP  UCS+CSP        CLUSTERED
#
# Each leaf returns (algorithm_key, explanation) where:
#   "single"    → plain UCS+CSP, one goal
#   "hybrid"    → independent UCS+CSP per car (best when constraints matter
#                 more than clustering, or goals are few)
#   "clustered" → K-Means + KNN + UCS (best when goals are spread and numerous)

import math
from clustering import kmeans, auto_k


def _goals_span(nodes, goal_names):
    """Diagonal of the bounding box enclosing all goal coordinates."""
    if len(goal_names) < 2:
        return 0.0
    xs = [nodes[g].x for g in goal_names]
    ys = [nodes[g].y for g in goal_names]
    return math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2)


def _inter_cluster_spread(nodes, clusters):
    """
    Average distance between cluster centroids.
    High spread → goals are genuinely geographically separated → clustering helps.
    """
    if len(clusters) < 2:
        return 0.0
    centroids = []
    for c in clusters:
        cx = sum(nodes[g].x for g in c) / len(c)
        cy = sum(nodes[g].y for g in c) / len(c)
        centroids.append((cx, cy))
    dists = []
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            d = math.sqrt((centroids[i][0] - centroids[j][0]) ** 2 +
                          (centroids[i][1] - centroids[j][1]) ** 2)
            dists.append(d)
    return sum(dists) / len(dists)


def run_decision_tree(nodes, goal_names, blocked_nodes, blocked_edges):
    goals = list(goal_names)
    n = len(goals)

    # ── Compute features ──
    has_blocks   = bool(blocked_nodes or blocked_edges)
    span         = _goals_span(nodes, goals)

    k            = auto_k(n)
    clusters, _  = kmeans(nodes, goals, k) if n >= 2 else ([goals], [])
    num_clusters = len(clusters)
    avg_cls_size = n / num_clusters if num_clusters else n
    spread       = _inter_cluster_spread(nodes, clusters)

    features = {
        "num_goals":        n,
        "has_blocks":       has_blocks,
        "num_clusters":     num_clusters,
        "avg_cluster_size": round(avg_cls_size, 2),
        "goals_span_px":    round(span, 1),
        "cluster_spread_px":round(spread, 1),
    }

    splits = []   # record every decision for the explanation

    # ── Tree ───
    # Root split: trivial single-goal case
    if n == 0:
        return "single", "No destinations set.", features

    if n == 1:
        splits.append("num_goals == 1  →  only one destination")
        splits.append("→ SINGLE UCS+CSP: no ordering needed, direct path.")
        return "single", _fmt(splits), features

    # Many goals — clustering is almost always worth it
    if n >= 5:
        splits.append(f"num_goals = {n} ≥ 5  →  large delivery set")
        splits.append(f"K-Means found {num_clusters} cluster(s), "
                      f"avg {avg_cls_size:.1f} goals/cluster")
        splits.append("→ CLUSTERED: K-Means zones + KNN ordering + UCS paths.")
        return "clustered", _fmt(splits), features

    # 2–4 goals: refine by constraints and spread
    splits.append(f"num_goals = {n}  (2–4 range)")

    if has_blocks:
        splits.append(f"has_blocks = True  ({len(blocked_nodes)} node(s), "
                      f"{len(blocked_edges)} edge(s) blocked)")
        # Constraints exist — does clustering still make sense?
        if num_clusters >= 2 and spread > 150:
            splits.append(f"num_clusters = {num_clusters} ≥ 2  AND  "
                          f"cluster_spread = {spread:.0f}px > 150px")
            splits.append("Goals are geographically separated despite constraints.")
            splits.append("→ CLUSTERED: zones are distinct enough to benefit from clustering.")
            return "clustered", _fmt(splits), features
        else:
            splits.append(f"num_clusters = {num_clusters} or "
                          f"spread = {spread:.0f}px ≤ 150px")
            splits.append("Goals are nearby — clustering adds no benefit.")
            splits.append("→ HYBRID: independent UCS+CSP per car; "
                          "constraints handled precisely.")
            return "hybrid", _fmt(splits), features

    else:
        splits.append("has_blocks = False  →  no constraints")
        # No constraints — decide purely by spread
        if span < 200:
            splits.append(f"goals_span = {span:.0f}px < 200px  →  goals are clustered")
            splits.append("Goals are geographically close — clustering won't form "
                          "meaningful separate zones.")
            splits.append("→ HYBRID: direct UCS+CSP per car is efficient.")
            return "hybrid", _fmt(splits), features
        else:
            splits.append(f"goals_span = {span:.0f}px ≥ 200px  →  goals are spread out")
            splits.append(f"K-Means formed {num_clusters} zone(s) with "
                          f"spread = {spread:.0f}px")
            splits.append("→ CLUSTERED: geographic zones are meaningful; "
                          "KNN orders stops inside each zone.")
            return "clustered", _fmt(splits), features


def _fmt(splits):
    return "\n".join(f"  {'→' if i == len(splits)-1 else '•'} {s}"
                     for i, s in enumerate(splits))