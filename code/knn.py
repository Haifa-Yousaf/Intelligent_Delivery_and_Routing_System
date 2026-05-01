import math

# KNN-based next delivery destination selector
# Uses Euclidean distance between node coordinates as proximity metric.
# k=1 mirrors the greedy nearest-neighbour already in UCS;
# k>1 evaluates the k closest candidates and picks the one with the
# lowest actual graph cost (via the supplied cost_fn), blending
# geographic proximity with true path cost.

def euclidean(nodes, a, b):
    return math.sqrt((nodes[a].x - nodes[b].x)**2 + (nodes[a].y - nodes[b].y)**2)

def knn_next_destination(nodes, current, remaining_goals, cost_fn, k=3):

    remaining = list(remaining_goals)
    if not remaining:
        return None

    # Sort by Euclidean distance, take top-k candidates
    remaining.sort(key=lambda g: euclidean(nodes, current, g))
    candidates = remaining[:k]

    # Among k geographically nearest, pick the one with lowest true path cost
    best_goal = None
    best_cost = float('inf')
    for goal in candidates:
        cost = cost_fn(current, goal)
        if cost is not None and cost < best_cost:
            best_cost = cost
            best_goal = goal

    # Fallback: if none of the k nearest are reachable, try the rest
    if best_goal is None:
        for goal in remaining[k:]:
            cost = cost_fn(current, goal)
            if cost is not None and cost < best_cost:
                best_cost = cost
                best_goal = goal

    return best_goal