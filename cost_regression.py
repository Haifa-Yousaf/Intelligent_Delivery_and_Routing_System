# cost_regression.py
#
# Linear Regression for delivery cost prediction.
#
# Purpose: before running the full UCS search, give the user a fast
# estimated cost based on simple graph features.  Think of it like
# a "price estimate before booking" — runs in O(1) once trained.
#
# Features used (all computable without running UCS):
#   x1 = straight-line (Euclidean) distance between source and goal
#   x2 = number of blocked nodes in the graph
#   x3 = number of blocked edges in the graph
#
# Model:  predicted_cost = w0 + w1*x1 + w2*x2 + w3*x3
#
# Training: we use online (incremental) least-squares — each time a
# real UCS result comes back, we add one training sample and update
# the weights so predictions improve over time.
#
# This mirrors supervised regression: label = actual UCS cost,
# features = graph statistics at query time.

import math


def euclidean(nodes, a, b):
    return math.sqrt((nodes[a].x - nodes[b].x) ** 2 +
                     (nodes[a].y - nodes[b].y) ** 2)


class CostRegressor:
    """
    Incremental linear regression:  cost ~ w0 + w1*dist + w2*blocked_n + w3*blocked_e

    Uses the normal equations solved via a running (XtX, Xty) accumulator
    so weights update after every delivery — no batch re-training needed.

    With fewer than 4 samples (under-determined), falls back to a simple
    ratio estimate (cost ≈ dist * avg_cost_per_unit_distance seen so far).
    """

    def __init__(self):
        self.samples = []          # list of (features_vec, label)
        self.weights = None        # [w0, w1, w2, w3]  once trained

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, nodes, source, goal, blocked_nodes, blocked_edges, actual_cost):
        """
        Add one training sample from a completed delivery.
        Updates model weights immediately.
        """
        feat = self._features(nodes, source, goal, blocked_nodes, blocked_edges)
        self.samples.append((feat, actual_cost))
        if len(self.samples) >= 4:
            self._fit()

    def predict(self, nodes, source, goal, blocked_nodes, blocked_edges):
        """
        Return (predicted_cost, confidence_label).
        confidence_label is 'low' / 'medium' / 'high' based on sample count.
        """
        feat = self._features(nodes, source, goal, blocked_nodes, blocked_edges)
        n = len(self.samples)

        if self.weights is not None:
            pred = sum(w * f for w, f in zip(self.weights, feat))
            pred = max(0.0, pred)           # costs can't be negative
            conf = "high" if n >= 10 else "medium"
            return round(pred, 2), conf

        # Fallback: average cost-per-euclidean-unit seen so far
        if n >= 1:
            ratios = []
            for (f, c) in self.samples:
                if f[1] > 0:                # f[1] = euclidean dist
                    ratios.append(c / f[1])
            if ratios:
                avg_ratio = sum(ratios) / len(ratios)
                pred = max(0.0, avg_ratio * feat[1])
                return round(pred, 2), "low"

        return None, "none"                 # not enough data yet

    @property
    def trained(self):
        return self.weights is not None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _features(self, nodes, source, goal, blocked_nodes, blocked_edges):
        """Return [1, euclidean_dist, num_blocked_nodes, num_blocked_edges]."""
        dist = euclidean(nodes, source, goal) if (source in nodes and goal in nodes) else 0.0
        return [1.0, dist, float(len(blocked_nodes)), float(len(blocked_edges))]

    def _fit(self):
        """
        Solve normal equations: w = (X^T X)^{-1} X^T y
        Implemented without numpy — pure Python for portability.
        """
        X = [f for f, _ in self.samples]
        y = [label for _, label in self.samples]
        n_feat = len(X[0])

        # XtX = X^T @ X
        XtX = [[sum(X[i][a] * X[i][b] for i in range(len(X)))
                 for b in range(n_feat)]
                for a in range(n_feat)]

        # Xty = X^T @ y
        Xty = [sum(X[i][a] * y[i] for i in range(len(X)))
               for a in range(n_feat)]

        # Solve via Gaussian elimination with partial pivoting
        w = _solve(XtX, Xty)
        if w is not None:
            self.weights = w


# ── Gaussian elimination (no numpy dependency) ────────────────────────────────

def _solve(A, b):
    """
    Solve Ax = b via Gaussian elimination with partial pivoting.
    Returns solution vector or None if singular.
    """
    n = len(b)
    # Augmented matrix
    M = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        # Find pivot
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        if abs(M[col][col]) < 1e-12:
            return None                     # singular

        # Eliminate below
        for row in range(col + 1, n):
            factor = M[row][col] / M[col][col]
            for j in range(col, n + 1):
                M[row][j] -= factor * M[col][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = M[i][n]
        for j in range(i + 1, n):
            x[i] -= M[i][j] * x[j]
        x[i] /= M[i][i]
    return x
