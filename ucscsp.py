# ucs.py

import heapq

def ucscsp(nodes, start, goal, blocked_nodes=set(), blocked_edges=set()):
    open_list = []
    heapq.heappush(open_list, (0, start))
    came_from = {}
    goal_score = {name: float('inf') for name in nodes}
    goal_score[start] = 0

    while open_list:
        current_goal, current = heapq.heappop(open_list)

        if current == goal:
            path = []
            node = current
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.append(start)
            return path[::-1], goal_score[goal]

        if current in blocked_nodes:
            continue

        for neighbor, cost in nodes[current].edges.items():
            if neighbor in blocked_nodes:
                continue

            edge = tuple(sorted((current, neighbor)))
            if edge in blocked_edges:
                continue

            tentative_goal = goal_score[current] + cost

            if tentative_goal < goal_score[neighbor]:
                goal_score[neighbor] = tentative_goal
                came_from[neighbor] = current
                heapq.heappush(open_list, (tentative_goal, neighbor))

    return None, None