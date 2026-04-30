# Tracks and compares routing algorithm performance across multiple runs.

# Metrics (ML evaluations):
#   total_cost    ~ MSE (lowest value)
#   success_rate  ~ accuracy
#   runtime       ~ inference time

import time

class Benchmark:
    def __init__(self):
        self.reset()

    def reset(self):
        self.records = []   # list of dicts, one per run

    def run(self, label, algorithm_fn, *args, **kwargs):
        #Time and record one algorithm run.

        start = time.perf_counter()
        try:
            result = algorithm_fn(*args, **kwargs)
            success = result is not None and result[0] is not None
        except Exception:
            result = (None, None)
            success = False
        elapsed = time.perf_counter() - start

        cost = result[1] if (success and len(result) > 1) else None

        self.records.append({
            "algorithm": label,
            "success":   success,
            "cost":      cost,
            "runtime_ms": round(elapsed * 1000, 3),
        })
        return result

    def summary(self):
        
        from collections import defaultdict

        groups = defaultdict(list)
        for r in self.records:
            groups[r["algorithm"]].append(r)

        out = {}
        for algo, runs in groups.items():
            successes = [r for r in runs if r["success"]]

            for r in successes:
                if "cost" not in r:
                    print("Missing cost in:", r)

            costs = [r.get("cost") for r in successes if r.get("cost") is not None]
            out[algo] = {
                "runs":          len(runs),
                "success_rate":  round(len(successes) / len(runs), 3) if runs else 0,
                "avg_cost":      round(sum(costs) / len(costs), 3) if costs else None,
                "min_cost":      round(min(costs), 3) if costs else None,
                "avg_runtime_ms":round(sum(r.get("runtime_ms", 0) for r in runs) / len(runs), 3),
            }
        return out

    def format_summary(self):
        s = self.summary()
        if not s:
            return "No benchmark data yet."
        lines = ["── Algorithm Benchmark ──"]
        for algo, m in s.items():
            lines.append(f"\n{algo}")
            lines.append(f"  Runs         : {m['runs']}")
            lines.append(f"  Success Rate : {m['success_rate']*100:.1f}%")
            lines.append(f"  Avg Cost     : {m['avg_cost'] if m['avg_cost'] is not None else 'N/A'}")
            lines.append(f"  Best Cost    : {m['min_cost'] if m['min_cost'] is not None else 'N/A'}")
            lines.append(f"  Avg Time     : {m['avg_runtime_ms']} ms")
        return "\n".join(lines)

    # Return the most recent record for a given algorithm label
    def last(self, label):
        for r in reversed(self.records):
            if r["algorithm"] == label:
                return r
        return None