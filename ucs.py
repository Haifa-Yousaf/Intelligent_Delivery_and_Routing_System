import heapq
from csp import build_filtered_graph

def ucs_on_filtered(filtered_graph, start, goal):
    if start not in filtered_graph or goal not in filtered_graph:
        return None, None

    open_list = []
    heapq.heappush(open_list, (0, start))
    came_from = {}
    g_score = {n: float('inf') for n in filtered_graph}
    g_score[start] = 0

    while open_list:
        current_cost, current = heapq.heappop(open_list)

        if current == goal:
            path, node = [], current
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.append(start)
            return path[::-1], g_score[goal]

        if current_cost > g_score[current]:
            continue    # stale entry so skip

        for neighbor, cost in filtered_graph[current].items():
            tentative = g_score[current] + cost
            if tentative < g_score[neighbor]:
                g_score[neighbor] = tentative
                came_from[neighbor] = current
                heapq.heappush(open_list, (tentative, neighbor))

    return None, None


def ucs(nodes, start, goal, blocked_nodes=frozenset(), blocked_edges=frozenset()):

    filtered = build_filtered_graph(nodes, blocked_nodes, blocked_edges)
    return ucs_on_filtered(filtered, start, goal)