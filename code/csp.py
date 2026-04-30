# Reduces the search space before any pathfinding.
#
# UCS/GA then only ever sees valid nodes
#      and never wastes heap operations on dead-end expansions.
#   2. Forward checking: before the search starts, verify every goal is
#      reachable in the filtered graph. Fail fast instead of letting UCS
#      exhaust the entire graph on a disconnected problem.

def build_filtered_graph(nodes, blocked_nodes=frozenset(), blocked_edges=frozenset()):
#filtered graph physically excludes blocked nodes and blocked edges. 

    filtered = {}
    for name, vertex in nodes.items():
        if name in blocked_nodes:
            continue                              # remove blocked node
        filtered[name] = {}
        for neighbor, cost in vertex.edges.items():
            if neighbor in blocked_nodes:
                continue                          # edge to blocked node
            edge = tuple(sorted((name, neighbor)))
            if edge in blocked_edges:
                continue                          # blocked edge
            filtered[name][neighbor] = cost
    return filtered


def forward_check(filtered_graph, start, goals):
    #BFS reachability on the already-filtered graph.
    # fails fast when a goal is disconnected as it is run before search starts

    unreachable = []
    for goal in goals:
        if goal not in filtered_graph:
            unreachable.append(goal)
            continue
        visited, queue, found = set(), [start], False
        while queue:
            node = queue.pop()
            if node == goal:
                found = True
                break
            if node in visited:
                continue
            visited.add(node)
            for nb in filtered_graph.get(node, {}):
                if nb not in visited:
                    queue.append(nb)
        if not found:
            unreachable.append(goal)
    return (len(unreachable) == 0), unreachable


def apply_csp(nodes, start, goals, blocked_nodes=frozenset(), blocked_edges=frozenset()):
    filtered = build_filtered_graph(nodes, blocked_nodes, blocked_edges)
    if start not in filtered:
        return filtered, False, f"Start node '{start}' is blocked or missing."

    ok, unreachable = forward_check(filtered, start, goals)
    if not ok:
        return filtered, False, \
            f"Goals unreachable after constraint filtering: {unreachable}"

    return filtered, True, None
