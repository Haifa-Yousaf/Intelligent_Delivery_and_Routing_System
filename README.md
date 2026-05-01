# 🚗 Smart Delivery Routing System — Hybrid AI

A multi-algorithm, multi-car delivery routing simulation built with Python and Tkinter. The system combines classical search (UCS), constraint satisfaction (CSP), unsupervised learning (K-Means), supervised learning (Linear Regression), and a Decision Tree to intelligently route deliveries across an interactive map.

---

## 📸 Overview

The application presents an 18-node graph divided into three geographic zones:

| Zone | Location | District |
|------|----------|----------|
| A (N1–N6) | Top-left | Warehouse |
| B (N7–N12) | Top-right | Commercial |
| C (N13–N18) | Bottom | Residential |

Users can add/delete nodes and edges, block roads, set a source and up to 8 delivery destinations, then run one of three routing algorithms.

---

## 🧠 Algorithms

### 1. Hybrid UCS + CSP (`Run UCS + CSP`)
- Assigns one independent car per destination.
- **CSP** first removes blocked nodes/edges from the graph entirely (true search space reduction via constraint propagation + forward checking).
- **UCS** then finds the shortest path to each goal on the filtered graph.

### 2. Clustered Routing (`Run Clustered`)
- **K-Means** partitions destinations into geographic zones — one car per zone.
- **KNN** orders stops within each zone by blending geographic proximity with actual path cost.
- **UCS + CSP** finds the path between each stop.

### 3. Smart Routing (`▶ Run Smart`)
- A **Decision Tree** computes features (number of goals, blocked constraints, cluster spread, bounding box diagonal) and automatically selects the best algorithm.
- Shows its full reasoning before running.

### 4. Cost Estimate
- An **incremental Linear Regression** model predicts delivery cost before UCS runs.
- Features: Euclidean distance, number of blocked nodes, number of blocked edges.
- Confidence improves from `low → medium → high` as more deliveries are completed.

---

## 📁 Project Structure

```
├── code/
│   ├── main.py              # Entry point — launches the Tkinter app
│   ├── welcome.py           # Splash/welcome screen
│   ├── gui.py               # Main interactive GUI and algorithm runners
│   ├── vertex.py            # Vertex (node) data structure
│   ├── csp.py               # Constraint propagation + forward checking
│   ├── ucs.py               # UCS running on the CSP-filtered graph
│   ├── knn.py               # KNN-based next-destination selector
│   ├── clustering.py        # K-Means++ geographic zone clustering
│   ├── decision_tree.py     # Feature-based algorithm selection tree
│   ├── cost_regression.py   # Incremental linear regression cost predictor
│   └── benchmark.py         # Per-algorithm performance tracker        
├── images/
│   ├── car.png
│   └── map.png
└── docs/
    └── report.pdf
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Tkinter (included with standard Python on Windows/macOS; on Linux: `sudo apt install python3-tk`)

No third-party libraries required — the project is pure Python stdlib.

### Run

```bash
git clone https://github.com/Haifa-Yousaf/Intelligent_Delivery_and_Routing_System.git
cd Intelligent_Delivery_and_Routing_System
python main.py
```

---

## 🖱️ How to Use

1. **Launch** the app — a welcome screen appears. Click **Run Simulation**.
2. The default 18-node graph loads automatically.
3. Use the control panel buttons to interact:

| Button | Action |
|--------|--------|
| `Add Vertex` | Click canvas to place a new node |
| `Add Edge` | Click two nodes, enter cost |
| `Set Source` | Click a node to mark it green (start) |
| `Set Destination` | Click nodes to mark them red (goals, max 8) |
| `Block Vertex` | Click a node to block/unblock it (black) |
| `Block Edge` | Click two nodes to block/unblock the edge (red dashed) |
| `Delete Vertex / Edge` | Remove nodes or edges from the graph |
| `Run UCS + CSP` | One car per destination, shortest path |
| `Run Clustered` | Zone-based multi-car routing |
| `▶ Run Smart` | Auto-selects the best algorithm |
| `Cost Estimate` | Regression-based cost prediction |
| `Benchmark` | View performance stats across all runs |
| `Reset` | Clear everything and reload default graph |

---

## 📊 Benchmark Metrics

After running algorithms, click **Benchmark** to see:

- **Runs** — total executions
- **Success Rate** — proportion of runs that found a valid path
- **Avg / Best Cost** — route cost statistics
- **Avg Runtime (ms)** — execution time per run

---

## 🔬 Algorithm Selection — Decision Tree Logic

```
num_goals == 1?
├── YES → Single UCS
└── NO
    num_goals >= 5?
    ├── YES → Clustered
    └── NO (2–4 goals)
        has_blocks?
        ├── YES
        │   num_clusters >= 2 AND spread > 150px?
        │   ├── YES → Clustered
        │   └── NO  → Hybrid
        └── NO
            goals_span < 200px?
            ├── YES → Hybrid
            └── NO  → Clustered
```

---

## 🤖 ML Components Summary

| Component | Type | Purpose |
|-----------|------|---------|
| `clustering.py` | Unsupervised (K-Means++) | Geographic zone partitioning |
| `knn.py` | Instance-based (KNN) | Next-stop ordering within a zone |
| `cost_regression.py` | Supervised (Linear Regression) | Pre-search cost prediction |
| `decision_tree.py` | Rule-based Decision Tree | Algorithm selection |
| `benchmark.py` | Evaluation | Runtime & cost tracking |

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
