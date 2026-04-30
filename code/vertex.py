# Represents a single node (location) on the delivery map.

class Vertex:
    def __init__(self, name, posx, posy):
        self.name = name
        self.x = posx
        self.y = posy
        self.edges = {}  # neighbor_name: cost