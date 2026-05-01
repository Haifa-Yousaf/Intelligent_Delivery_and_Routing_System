# Smart Delivery Routing — Multi-Car, Multi-Goal GUI
#
# Graph layout: 18 nodes in 3 clearly separated geographic zones
#   Zone A (top-left)   : N1–N6   warehouse district
#   Zone B (top-right)  : N7–N12  commercial district
#   Zone C (bottom)     : N13–N18 residential district
#   Cross-zone bridges  : a few inter-zone edges with higher cost
#
# Algorithms:
#   Run Hybrid   → independent UCS+CSP path per car
#   Run Clustered → K-Means zones + KNN ordering + UCS paths
#   Run Smart    → Decision Tree picks the right one automatically
#   Cost Estimate → Linear Regression prediction

import tkinter as tk
from tkinter import simpledialog, messagebox
import time, os, math

from vertex import Vertex
from csp import build_filtered_graph
from ucs import ucs_on_filtered
from knn import knn_next_destination
from clustering import kmeans, auto_k
from cost_regression import CostRegressor
from benchmark import Benchmark
from decision_tree import run_decision_tree

VERTEX_RADIUS = 14
DESTINATIONS_LIMIT = 8

CAR_COLORS = ["#2980B9", "#E74C3C", "#27AE60", "#F39C12",
              "#8E44AD", "#16A085", "#D35400", "#2C3E50"]

ZONE_COLORS = {
    "A": "#D6EAF8",   # light blue
    "B": "#D5F5E3",   # light green
    "C": "#FDEBD0",   # light orange
}


class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Delivery Routing")

        self.canvas = tk.Canvas(root, width=720, height=520, bg="white")
        self.canvas.pack(pady=6)

        base = os.path.dirname(os.path.abspath(__file__))
        try:
            self.map = tk.PhotoImage(file=os.path.join(base, "map.png"))
            self.map = self.map.zoom(2, 2)
            self.canvas.create_image(0, 0, image=self.map, anchor="nw")
        except Exception:
            pass   # map image optional

        self.vertex           = {}
        self.vertex_positions = {}
        self.edge_lines       = {}
        self.edge_texts       = {}
        self.source_vertex    = None
        self.dest_vertex      = set()
        self.selected_vertex  = None
        self.blocked_vertex   = set()
        self.blocked_edges    = set()

        self.benchmark = Benchmark()
        self.regressor = CostRegressor()

        # ── Control panel ──
        cp = tk.Frame(root)
        cp.pack()

        # Row 0 — graph building
        tk.Button(cp, text="Add Vertex",      command=self.add_node_mode).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(cp, text="Add Edge",        command=self.add_edge_mode).grid(row=0, column=1, padx=2)
        self.btn_source = tk.Button(cp, text="Set Source", command=self.set_start_mode)
        self.btn_source.grid(row=0, column=2, padx=2)
        tk.Button(cp, text="Set Destination", command=self.set_goal_mode).grid(row=0, column=3, padx=2)
        tk.Button(cp, text="Block Vertex",    command=self.toggle_block_node_mode).grid(row=0, column=4, padx=2)
        tk.Button(cp, text="Block Edge",      command=self.block_edge_mode).grid(row=0, column=5, padx=2)

        # Row 1 — editing + run buttons
        tk.Button(cp, text="Delete Vertex",   command=self.delete_node_mode).grid(row=1, column=0, padx=2, pady=2)
        tk.Button(cp, text="Delete Edge",     command=self.delete_edge_mode).grid(row=1, column=1, padx=2)
        tk.Button(cp, text="Run UCS + CSP",      command=self.run_hybrid,
                  bg="#2471A3", fg="white").grid(row=1, column=2, padx=2)
        tk.Button(cp, text="Run Clustered",   command=self.run_clustered,
                  bg="#1E8449", fg="white").grid(row=1, column=3, padx=2)
        tk.Button(cp, text="▶ Run Smart",     command=self.run_smart,
                  bg="#922B21", fg="white", font=("Segoe UI", 9, "bold")).grid(row=1, column=4, padx=2)
        tk.Button(cp, text="Cost Estimate",   command=self.show_cost_estimate,
                  bg="#7D3C98", fg="white").grid(row=1, column=5, padx=2)

        # Row 2 — extras
        tk.Button(cp, text="Benchmark",       command=self.show_benchmark).grid(row=2, column=0, padx=2, pady=2)
        tk.Button(cp, text="Reset",           command=self.reset).grid(row=2, column=1, padx=2)

        self.mode = None
        self.vertex_counter = 0
        self.canvas.bind("<Button-1>", self.main_functionality)

        self.info_label = tk.Label(root, text="Mode: None", font=("Segoe UI", 11))
        self.info_label.pack(pady=1)
        self.status_label = tk.Label(root, text="", font=("Segoe UI", 9),
                                     fg="#555", wraplength=700, justify="left")
        self.status_label.pack(pady=1)

        self.initialize_graph()

    # ── Mode helpers ──
    def change_mode(self, m):
        self.mode = m
        self.info_label.config(text=f"Mode: {m}")

    def add_node_mode(self):          self.change_mode("add_vertex")
    def add_edge_mode(self):          self.change_mode("add_edge");          self.selected_vertex = None
    def set_start_mode(self):         self.change_mode("set_source");        self.selected_vertex = None
    def set_goal_mode(self):          self.change_mode("set_destination")
    def toggle_block_node_mode(self): self.change_mode("block_vertex")
    def block_edge_mode(self):        self.change_mode("block_edge");        self.selected_vertex = None
    def delete_node_mode(self):       self.change_mode("delete_vertex")
    def delete_edge_mode(self):       self.change_mode("delete_edge")

    # ── Canvas dispatcher ──
    def main_functionality(self, event):
        x, y = event.x, event.y
        nearest_id = None
        for oid, name in self.vertex_positions.items():
            vx, vy = self.vertex[name].x, self.vertex[name].y
            if (x - vx) ** 2 + (y - vy) ** 2 <= VERTEX_RADIUS ** 2:
                nearest_id = oid
                break

        if self.mode == "add_vertex":
            self.vertex_counter += 1
            name = f"N{self.vertex_counter}"
            self.vertex[name] = Vertex(name, x, y)
            oid = self.canvas.create_oval(x - VERTEX_RADIUS, y - VERTEX_RADIUS,
                                           x + VERTEX_RADIUS, y + VERTEX_RADIUS,
                                           fill="lightgray")
            self.vertex_positions[oid] = name
            self.canvas.create_text(x, y, text=name, font=("Segoe UI", 8, "bold"))
            return

        if nearest_id is None:
            return
        vname = self.vertex_positions[nearest_id]

        if self.mode == "add_edge":
            if not self.selected_vertex:
                self.selected_vertex = vname
            else:
                cost = self.get_cost()
                if cost is None:
                    self.selected_vertex = None
                    return
                self.add_edge(self.selected_vertex, vname, cost)
                self.selected_vertex = None

        elif self.mode == "set_source":
            if self.source_vertex:
                self.fill_vertex_color(self.source_vertex)
            self.source_vertex = vname
            self.fill_vertex_color(vname, "green")
            self.btn_source.config(state="disabled")
            self.mode = None
            self._refresh_status()

        elif self.mode == "set_destination":
            if len(self.dest_vertex) >= DESTINATIONS_LIMIT:
                messagebox.showwarning("Limit Reached",
                                       f"{DESTINATIONS_LIMIT} maximum deliveries allowed!")
                return
            if vname not in self.dest_vertex:
                self.dest_vertex.add(vname)
                self.fill_vertex_color(vname, "red")
            self._refresh_status()

        elif self.mode == "block_vertex":
            if vname in self.blocked_vertex:
                self.blocked_vertex.remove(vname)
                self.fill_vertex_color(vname)
            else:
                self.blocked_vertex.add(vname)
                self.fill_vertex_color(vname, "black")
            self._refresh_status()

        elif self.mode == "delete_vertex":
            self.delete_vertex(vname)
            self._refresh_status()

        elif self.mode == "delete_edge":
            if not self.selected_vertex:
                self.selected_vertex = vname
            else:
                self.delete_edge(self.selected_vertex, vname)
                self.selected_vertex = None

        elif self.mode == "block_edge":
            if not self.selected_vertex:
                self.selected_vertex = vname
            else:
                edge = tuple(sorted((self.selected_vertex, vname)))
                line_id = (self.edge_lines.get(edge) or
                           self.edge_lines.get((vname, self.selected_vertex)))
                if edge in self.blocked_edges:
                    self.blocked_edges.remove(edge)
                    if line_id:
                        self.canvas.itemconfig(line_id, fill="black", dash=())
                else:
                    self.blocked_edges.add(edge)
                    if line_id:
                        self.canvas.itemconfig(line_id, fill="red", dash=(4, 2))
                self.selected_vertex = None
                self._refresh_status()

    # ── Drawing ──
    def fill_vertex_color(self, vertex, color=None):
        for oid, name in self.vertex_positions.items():
            if name == vertex:
                if color is None:
                    fill = "lightgray"
                    if vertex == self.source_vertex:  fill = "green"
                    if vertex in self.dest_vertex:    fill = "red"
                    if vertex in self.blocked_vertex: fill = "black"
                    self.canvas.itemconfig(oid, fill=fill)
                else:
                    self.canvas.itemconfig(oid, fill=color)

    def add_edge(self, v1, v2, cost):
        self.vertex[v1].edges[v2] = cost
        self.vertex[v2].edges[v1] = cost
        line_id = self.canvas.create_line(self.vertex[v1].x, self.vertex[v1].y,
                                           self.vertex[v2].x, self.vertex[v2].y,
                                           fill="#888888", width=2)
        mid_x = (self.vertex[v1].x + self.vertex[v2].x) / 2
        mid_y = (self.vertex[v1].y + self.vertex[v2].y) / 2
        text_id = self.canvas.create_text(mid_x, mid_y - 9, text=str(int(cost)),
                                           fill="purple", font=("Segoe UI", 8))
        self.edge_lines[(v1, v2)] = line_id
        self.edge_texts[(v1, v2)] = text_id

    def delete_vertex(self, vname):
        for nb in list(self.vertex[vname].edges.keys()):
            self.delete_edge(vname, nb)
        del self.vertex[vname]
        for oid, name in list(self.vertex_positions.items()):
            if name == vname:
                self.canvas.delete(oid)
                del self.vertex_positions[oid]
        if vname == self.source_vertex:  self.source_vertex = None
        if vname in self.dest_vertex:    self.dest_vertex.remove(vname)
        if vname in self.blocked_vertex: self.blocked_vertex.remove(vname)

    def delete_edge(self, n1, n2):
        self.vertex[n1].edges.pop(n2, None)
        self.vertex[n2].edges.pop(n1, None)
        line_id = self.edge_lines.pop((n1, n2), self.edge_lines.pop((n2, n1), None))
        text_id = self.edge_texts.pop((n1, n2), self.edge_texts.pop((n2, n1), None))
        if line_id: self.canvas.delete(line_id)
        if text_id: self.canvas.delete(text_id)

    def get_cost(self):
        return simpledialog.askfloat("Edge Cost", "Enter edge cost:", parent=self.root)

    def _validate(self):
        if not self.source_vertex or not self.dest_vertex:
            messagebox.showwarning("Warning", "Set a source and at least one destination!")
            return False
        return True

    def _draw_path(self, path, color, offset=0):
        for i in range(len(path) - 1):
            v1, v2 = self.vertex[path[i]], self.vertex[path[i + 1]]
            self.canvas.create_line(v1.x + offset, v1.y + offset,
                                     v2.x + offset, v2.y + offset,
                                     fill=color, width=4, tags="path_line")

    # ── Status bar ──
    def _refresh_status(self):
        if not self.source_vertex or not self.dest_vertex:
            self.status_label.config(text="")
            return
        parts = []
        for goal in sorted(self.dest_vertex):
            pred, conf = self.regressor.predict(
                self.vertex, self.source_vertex, goal,
                self.blocked_vertex, self.blocked_edges)
            if pred is not None:
                parts.append(f"{self.source_vertex}→{goal}: ~{pred} ({conf})")
        if parts:
            self.status_label.config(text="Estimates: " + "  |  ".join(parts))
        else:
            self.status_label.config(text="Cost estimates: run a few deliveries first.")

    # ── CSP helper ──
    def _build_and_check(self, goals_list):
        """
        Run CSP: build filtered graph and forward-check all goals.
        Returns (filtered, ok, error_msg).
        """
        filtered = build_filtered_graph(
            self.vertex, self.blocked_vertex, self.blocked_edges)

        if self.source_vertex not in filtered:
            return filtered, False, "Source node is blocked!"

        unreachable = []
        for goal in goals_list:
            if goal not in filtered:
                unreachable.append(goal)
                continue
            visited, queue, found = set(), [self.source_vertex], False
            while queue:
                node = queue.pop()
                if node == goal: found = True; break
                if node in visited: continue
                visited.add(node)
                for nb in filtered.get(node, {}):
                    if nb not in visited: queue.append(nb)
            if not found:
                unreachable.append(goal)

        if unreachable:
            return filtered, False, (
                f"Goals unreachable after constraint filtering: {unreachable}\n"
                "Remove blocks or choose different goals.")
        return filtered, True, None

    # Algo 1: Hybrid (UCS + CSP) — one car per destination
    def run_hybrid(self):
        if not self._validate(): return
        self.canvas.delete("path_line")
        t0 = time.perf_counter()

        filtered, ok, err = self._build_and_check(list(self.dest_vertex))
        if not ok:
            messagebox.showinfo("CSP Failure", err); return

        total_cost, summary = 0, []
        for idx, goal in enumerate(sorted(self.dest_vertex)):
            color  = CAR_COLORS[idx % len(CAR_COLORS)]
            path, cost = ucs_on_filtered(filtered, self.source_vertex, goal)
            if path is None:
                summary.append(f"Car {idx+1}: {self.source_vertex}→{goal} | No path")
                continue
            self._draw_path(path, color, offset=idx * 3)
            total_cost += cost
            summary.append(f"Car {idx+1}: {' → '.join(path)} | Cost={cost}")
            self.regressor.record(self.vertex, self.source_vertex, goal,
                                  self.blocked_vertex, self.blocked_edges, cost)

        elapsed = round((time.perf_counter() - t0) * 1000, 3)
        self.benchmark.records.append({"algorithm": "Hybrid (UCS+CSP)",
                                        "success": True, "cost": total_cost,
                                        "runtime_ms": elapsed})
        self._refresh_status()
        messagebox.showinfo("Hybrid UCS+CSP",
            "\n".join(summary) +
            f"\n\nTotal Cost: {total_cost}  |  Runtime: {elapsed} ms"
            f"\nCSP pruned {len(self.blocked_vertex)} node(s), "
            f"{len(self.blocked_edges)} edge(s)")


    # Algo 2: Clustered (K-Means + KNN + CSP + UCS)
    def run_clustered(self):
        if not self._validate(): return
        self.canvas.delete("path_line")
        t0 = time.perf_counter()

        goals = list(self.dest_vertex)
        filtered, ok, err = self._build_and_check(goals)
        if not ok:
            messagebox.showinfo("CSP Failure", err); return

        k = auto_k(len(goals))
        clusters, centroids = kmeans(self.vertex, goals, k)

        total_cost, summary = 0, [f"K-Means: {len(goals)} goals → {len(clusters)} cluster(s)\n"]

        for ci, cluster_goals in enumerate(clusters):
            color = CAR_COLORS[ci % len(CAR_COLORS)]

            # Draw zone label on canvas
            cx = sum(self.vertex[g].x for g in cluster_goals) / len(cluster_goals)
            cy = sum(self.vertex[g].y for g in cluster_goals) / len(cluster_goals)
            self.canvas.create_text(cx, cy - 22, text=f"Zone {ci+1}",
                                     fill=color, font=("Segoe UI", 9, "bold"),
                                     tags="path_line")

            bad = [g for g in cluster_goals if g not in filtered]
            if bad:
                summary.append(f"Zone {ci+1}: {bad} blocked — skipped.")
                continue

            def cost_fn(cur, goal, f=filtered):
                _, c = ucs_on_filtered(f, cur, goal)
                return c

            remaining, current = set(cluster_goals), self.source_vertex
            route, cluster_cost, ok2 = [], 0, True

            while remaining:
                # KNN selects WHICH goal to visit next (geographic proximity)
                next_stop = knn_next_destination(
                    self.vertex, current, remaining, cost_fn, k=2)
                if next_stop is None:
                    summary.append(f"Zone {ci+1}: unreachable goal — skipped.")
                    ok2 = False; break
                # UCS finds HOW to get there (actual edge traversal)
                path, cost = ucs_on_filtered(filtered, current, next_stop)
                if path is None:
                    summary.append(f"Zone {ci+1}: no path to {next_stop}.")
                    ok2 = False; break
                self._draw_path(path, color, offset=ci * 3)
                route.append(next_stop)
                cluster_cost += cost
                current = next_stop
                remaining.remove(next_stop)
                self.regressor.record(self.vertex, self.source_vertex, next_stop,
                                      self.blocked_vertex, self.blocked_edges, cost)
            if ok2:
                total_cost += cluster_cost
                summary.append(f"Car {ci+1} ({color}): "
                                f"{self.source_vertex}→{'→'.join(route)} | Cost={cluster_cost}")

        elapsed = round((time.perf_counter() - t0) * 1000, 3)
        self.benchmark.records.append({"algorithm": "Clustered",
                                        "success": True, "cost": total_cost,
                                        "runtime_ms": elapsed})
        self._refresh_status()
        messagebox.showinfo("Clustered Delivery",
            "\n".join(summary) +
            f"\n\nTotal Cost: {total_cost}  |  Runtime: {elapsed} ms"
            f"\nClusters: {len(clusters)}  |  KNN k=2 per step")

  
    # Algo 3: Run Smart — DT picks the algorithm
    def run_smart(self):
        if not self._validate(): return

        algo_key, reason, features = run_decision_tree(
            self.vertex,
            self.dest_vertex,
            self.blocked_vertex,
            self.blocked_edges
        )

        algo_names = {
            "single":    "UCS (single goal)",
            "hybrid":    "Hybrid UCS+CSP (multi-car)",
            "clustered": "Clustered (K-Means + KNN + UCS)",
        }

        # Show the decision tree's reasoning before running
        feat_str = "\n".join(f"  {k}: {v}" for k, v in features.items())
        messagebox.showinfo(
            "▶ Run Smart — Decision Tree",
            f"── Features ──\n{feat_str}\n\n"
            f"── Decision Path ──\n{reason}\n\n"
            f"Running: {algo_names.get(algo_key, algo_key)}"
        )

        if algo_key in ("single", "hybrid"):
            self.run_hybrid()
        else:
            self.run_clustered()

    # ── Cost Estimate ──
    def show_cost_estimate(self):
        if not self._validate(): return
        lines = ["Linear Regression Cost Estimates", "=" * 38, "",
                 f"Samples: {len(self.regressor.samples)}   "
                 f"Trained: {'Yes' if self.regressor.trained else 'No (need ≥4)'}",
                 "Features: [1, Euclidean_dist, blocked_nodes, blocked_edges]"]
        if self.regressor.weights:
            w = self.regressor.weights
            lines.append(f"Weights: w0={w[0]:.2f}, w1={w[1]:.2f}, "
                          f"w2={w[2]:.2f}, w3={w[3]:.2f}")
        lines.append("")
        for goal in sorted(self.dest_vertex):
            pred, conf = self.regressor.predict(
                self.vertex, self.source_vertex, goal,
                self.blocked_vertex, self.blocked_edges)
            tag = f"~{pred}  ({conf} confidence)" if pred is not None else "Not enough data"
            lines.append(f"{self.source_vertex} → {goal}:  {tag}")
        messagebox.showinfo("Cost Estimates", "\n".join(lines))

    # ── Benchmark ──
    def show_benchmark(self):
        messagebox.showinfo("Benchmark", self.benchmark.format_summary())

    # ── Reset ──
    def reset(self):
        self.canvas.delete("all")
        base = os.path.dirname(os.path.abspath(__file__))
        try:
            self.map = tk.PhotoImage(file=os.path.join(base, "map.png"))
            self.map = self.map.zoom(2, 2)
            self.canvas.create_image(0, 0, image=self.map, anchor="nw")
        except Exception:
            pass
        self.vertex.clear(); self.vertex_positions.clear()
        self.edge_lines.clear(); self.edge_texts.clear()
        self.source_vertex = None; self.dest_vertex.clear()
        self.selected_vertex = None; self.blocked_vertex.clear()
        self.blocked_edges.clear(); self.vertex_counter = 0
        self.btn_source.config(state="normal")
        self.benchmark.reset()
        self.status_label.config(text="")
        self.initialize_graph()

    #Initializing basic graph
    def initialize_graph(self):

        # Zone A — top-left cluster
        zone_a = [
            ("N1",  60,  80), ("N2", 160,  60), ("N3", 240, 100),
            ("N4",  80, 170), ("N5", 180, 190), ("N6", 240, 220),
        ]
        # Zone B — top-right cluster
        zone_b = [
            ("N7",  440,  70), ("N8",  560,  60), ("N9",  660,  90),
            ("N10", 430, 180), ("N11", 550, 190), ("N12", 660, 200),
        ]
        # Zone C — bottom cluster
        zone_c = [
            ("N13", 150, 360), ("N14", 280, 350), ("N15", 420, 370),
            ("N16", 180, 460), ("N17", 330, 460), ("N18", 510, 450),
        ]

        all_nodes = zone_a + zone_b + zone_c

        #Storing nodes
        for name, x, y in all_nodes:
            node = Vertex(name, x, y)
            self.vertex[name] = node
            self.vertex_counter += 1

        # ── Draw zone background labels ──
        self.canvas.create_text(130, 40,  text="Zone A — Warehouse",
                                 fill="#2471A3", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(555, 35,  text="Zone B — Commercial",
                                 fill="#1E8449", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(350, 330, text="Zone C — Residential",
                                 fill="#922B21", font=("Segoe UI", 9, "bold"))

        # ── Intra-zone edges (low cost — same neighbourhood) ──
        intra_edges = [
            # Zone A
            ("N1","N2",3), ("N2","N3",4), ("N1","N4",2), ("N2","N5",3),
            ("N3","N6",3), ("N4","N5",4), ("N5","N6",2),
            # Zone B
            ("N7","N8",3), ("N8","N9",4), ("N7","N10",3), ("N8","N11",3),
            ("N9","N12",2), ("N10","N11",4), ("N11","N12",3),
            # Zone C
            ("N13","N14",3), ("N14","N15",4), ("N13","N16",2), ("N14","N17",3),
            ("N15","N18",3), ("N16","N17",4), ("N17","N18",3),
        ]

        # ── Bridge edges (high cost — cross-zone roads) ──
        bridge_edges = [
            ("N3", "N7",  12),   # A → B
            ("N4", "N13", 10),   # A → C
            ("N6", "N14",  9),   # A → C
            ("N12","N15", 11),   # B → C
            ("N10","N17", 13),   # B → C
        ]

        #Draw edges
        for v1, v2, cost in intra_edges + bridge_edges:
            self.add_edge(v1, v2, cost)
        
        # Draw nodes
        for name, x, y in all_nodes:
            oid = self.canvas.create_oval(x - VERTEX_RADIUS, y - VERTEX_RADIUS,
                                           x + VERTEX_RADIUS, y + VERTEX_RADIUS,
                                           fill="lightgray")
            self.vertex_positions[oid] = name
            self.canvas.create_text(x, y, text=name, font=("Segoe UI", 8, "bold"))