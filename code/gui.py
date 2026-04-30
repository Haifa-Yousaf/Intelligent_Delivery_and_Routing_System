# gui.py

import tkinter as tk
from tkinter import simpledialog, messagebox
from vertex import Vertex
from ucscsp import ucscsp

VERTEX_RADIUS = 15
DESTINATIONS_LIMIT = 5

class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Delivery Routing (Hybrid Version)")

        self.canvas = tk.Canvas(root, width=700, height=500, bg="white")
        self.canvas.pack(pady=10)

        self.map = tk.PhotoImage(file="map.png")
        self.map = self.map.zoom(2, 2)
        self.canvas.create_image(0, 0, image=self.map, anchor="nw")

        self.vertex = {}
        self.vertex_positions = {}
        self.edge_lines = {}
        self.edge_texts = {}
        self.source_vertex = None
        self.dest_vertex = set()
        self.selected_vertex = None
        self.blocked_vertex = set()
        self.blocked_edges = set()

        control_panel = tk.Frame(root)
        control_panel.pack()

        tk.Button(control_panel, text="Add Vertex", command=self.add_node_mode).grid(row=0, column=0)
        tk.Button(control_panel, text="Add Edge", command=self.add_edge_mode).grid(row=0, column=1)
        self.btn_source = tk.Button(control_panel, text="Set Source", command=self.set_start_mode)
        self.btn_source.grid(row=0, column=2)
        tk.Button(control_panel, text="Set Destination", command=self.set_goal_mode).grid(row=0, column=3)
        tk.Button(control_panel, text="Block Vertex", command=self.toggle_block_node_mode).grid(row=0, column=4)
        tk.Button(control_panel, text="Block Edge", command=self.block_edge_mode).grid(row=0, column=5)
        tk.Button(control_panel, text="Delete Vertex", command=self.delete_node_mode).grid(row=1, column=0)
        tk.Button(control_panel, text="Delete Edge", command=self.delete_edge_mode).grid(row=1, column=1)
        tk.Button(control_panel, text="Run Hybrid", command=self.run_ucs).grid(row=1, column=2)
        tk.Button(control_panel, text="Reset", command=self.reset).grid(row=1, column=3)

        self.mode = None
        self.vertex_counter = 0
        self.canvas.bind("<Button-1>", self.main_functionality)
        self.info_label = tk.Label(root, text="Mode: None", font=("Segoe UI", 12))
        self.info_label.pack(pady=4)
        self.initialize_graph()


    # Mode setter
    def change_mode(self, mode):
        self.mode = mode
        self.info_label.config(text=f"Mode: {mode}")

    def add_node_mode(self): self.change_mode("add_vertex")
    def add_edge_mode(self): self.change_mode("add_edge"); self.selected_vertex=None
    def set_start_mode(self): self.change_mode("set_source"); self.selected_vertex=None
    def set_goal_mode(self): self.change_mode("set_destination")
    def toggle_block_node_mode(self): self.change_mode("block_vertex")
    def block_edge_mode(self): self.change_mode("block_edge"); self.selected_vertex=None
    def delete_node_mode(self): self.change_mode("delete_vertex")
    def delete_edge_mode(self): self.change_mode("delete_edge")

    # Main functionality
    def main_functionality(self, event):
        x, y = event.x, event.y
        nearest_id = None
        for id, name in self.vertex_positions.items():
            vertexX, vertexY = self.vertex[name].x, self.vertex[name].y
            if (x-vertexX)**2 + (y-vertexY)**2 <= VERTEX_RADIUS**2:   #Euclidean distance
                nearest_id = id
                break
        if self.mode=="add_vertex":
            self.vertex_counter +=1
            name=f"N{self.vertex_counter}"
            self.vertex[name]=Vertex(name,x,y)
            id=self.canvas.create_oval(x-VERTEX_RADIUS,y-VERTEX_RADIUS,x+VERTEX_RADIUS,y+VERTEX_RADIUS,fill="lightgray")
            self.vertex_positions[id]=name
            self.canvas.create_text(x,y,text=name)
            return
        if nearest_id is None: return
        vertex_name = self.vertex_positions[nearest_id]

        if self.mode=="add_edge":
            if not self.selected_vertex:
                self.selected_vertex=vertex_name
            else:
                cost = self.get_cost()
                if cost is None: self.selected_vertex=None; return
                self.add_edge(self.selected_vertex,vertex_name,cost)
                self.selected_vertex=None

        elif self.mode=="set_source":
            if self.source_vertex: self.fill_vertex_color(self.source_vertex)
            self.source_vertex = vertex_name
            self.fill_vertex_color(vertex_name,"green")
            self.btn_source.config(state="disabled")  # only 1 start
            self.mode=None

        elif self.mode=="set_destination":
            if len(self.dest_vertex) >= DESTINATIONS_LIMIT:
                messagebox.showwarning("Limit Reached", "5 maximum deliveries allowed!")
                return
            if vertex_name not in self.dest_vertex:
                self.dest_vertex.add(vertex_name)
                self.fill_vertex_color(vertex_name,"red")

        elif self.mode=="block_vertex":
            if vertex_name in self.blocked_vertex:
                self.blocked_vertex.remove(vertex_name)
                self.fill_vertex_color(vertex_name)
            else:
                self.blocked_vertex.add(vertex_name)
                self.fill_vertex_color(vertex_name,"black")

        elif self.mode=="delete_vertex":
            self.delete_vertex(vertex_name)

        elif self.mode=="delete_edge":
            if not self.selected_vertex:
                self.selected_vertex=vertex_name
            else:
                self.delete_edge(self.selected_vertex,vertex_name)
                self.selected_vertex=None

        elif self.mode=="block_edge":
            if not self.selected_vertex:
                self.selected_vertex=vertex_name
            else:
                edge=tuple(sorted((self.selected_vertex,vertex_name)))
                line_id=self.edge_lines.get(edge) or self.edge_lines.get((vertex_name,self.selected_vertex))
                if edge in self.blocked_edges:
                    self.blocked_edges.remove(edge)
                    if line_id: self.canvas.itemconfig(line_id,fill="black",dash=())
                else:
                    self.blocked_edges.add(edge)
                    if line_id: self.canvas.itemconfig(line_id,fill="red",dash=(4,2))
                self.selected_vertex=None

    #fill color in the vertex
    def fill_vertex_color(self,vertex,color=None):
        for id,name in self.vertex_positions.items():
            if name==vertex:
                if color is None:
                    fill="lightgray"
                    if vertex==self.source_vertex: fill="green"
                    if vertex in self.dest_vertex: fill="red"
                    if vertex in self.blocked_vertex: fill="black"
                    self.canvas.itemconfig(id,fill=fill)
                else:
                    self.canvas.itemconfig(id,fill=color)

    # add and delete functions (add vertex done above already)
    def add_edge(self,v1,v2,cost):
        self.vertex[v1].edges[v2]=cost
        self.vertex[v2].edges[v1]=cost
        line_id=self.canvas.create_line(self.vertex[v1].x,self.vertex[v1].y,
                                        self.vertex[v2].x,self.vertex[v2].y,fill="black",width=2)
        mid_x=(self.vertex[v1].x+self.vertex[v2].x)/2
        mid_y=(self.vertex[v1].y+self.vertex[v2].y)/2
        text_id=self.canvas.create_text(mid_x,mid_y-10,text=str(cost),fill="purple")
        self.edge_lines[(v1,v2)]=line_id
        self.edge_texts[(v1,v2)]=text_id

    def delete_vertex(self,vertex_name):
        for neighbor in list(self.vertex[vertex_name].edges.keys()):
            self.delete_edge(vertex_name,neighbor)
        del self.vertex[vertex_name]
        for id,name in list(self.vertex_positions.items()):
            if name==vertex_name:
                self.canvas.delete(id)
                del self.vertex_positions[id]
        if vertex_name==self.source_vertex: self.source_vertex=None
        if vertex_name in self.dest_vertex: self.dest_vertex.remove(vertex_name)
        if vertex_name in self.blocked_vertex: self.blocked_vertex.remove(vertex_name)

    def delete_edge(self,n1,n2):
        self.vertex[n1].edges.pop(n2,None)
        self.vertex[n2].edges.pop(n1,None)
        line_id = self.edge_lines.pop((n1,n2), self.edge_lines.pop((n2,n1),None))
        text_id = self.edge_texts.pop((n1,n2), self.edge_texts.pop((n2,n1),None))
        if line_id: self.canvas.delete(line_id)
        if text_id: self.canvas.delete(text_id)

    # cost getter
    def get_cost(self):
        return simpledialog.askfloat("Edge Cost","Enter edge cost:",parent=self.root)

    # Run UCS (Multi-Goal Greedy)
    def run_ucs(self):
        if not self.source_vertex or not self.dest_vertex:
            messagebox.showwarning("Warning","Source and/or Destination(s) not set!")
            return

        if len(self.dest_vertex) > DESTINATIONS_LIMIT:
            messagebox.showwarning("Limit Exceeded","Maximum 5 deliveries allowed at once!")
            return

        self.canvas.delete("path_line")

        colors = ["orange", "pink", "blue", "yellow", "green"]  # max 5 cars
        total_cost = 0
        summary = []

        for idx, goal in enumerate(self.dest_vertex):
            path, cost = ucscsp(
                self.vertex, self.source_vertex, goal,
                self.blocked_vertex, self.blocked_edges
            )

            if path is None:
                messagebox.showinfo("No Path", f"Cannot reach goal {goal}")
                continue

            color = colors[idx % 5]

            # Draw independent path
            for i in range(len(path) - 1):
                n1 = self.vertex[path[i]]
                n2 = self.vertex[path[i+1]]
                offset = idx * 3
                self.canvas.create_line(
                    n1.x + offset, n1.y + offset,
                    n2.x + offset, n2.y + offset,
                    fill=color, width=4, tags="path_line"
                )

            total_cost += cost
            summary.append(f"{self.source_vertex} → {goal} | Cost = {cost}")

        messagebox.showinfo(
            "Multi-Car Delivery Paths",
            "\n".join(summary) + f"\n\nTotal Cost: {total_cost}"
        )

    # Reset system
    def reset(self):
       
        self.canvas.delete("all")
        
        #load map image
        self.map = tk.PhotoImage(file="map.png")
        self.map = self.map.zoom(2,2)

        # Place from top-left corner
        self.canvas.create_image(0, 0, image=self.map, anchor="nw")
        self.vertex.clear()
        self.vertex_positions.clear()
        self.edge_lines.clear()
        self.edge_texts.clear()
        self.source_vertex=None
        self.dest_vertex.clear()
        self.selected_vertex=None
        self.blocked_vertex.clear()
        self.blocked_edges.clear()
        self.vertex_counter=0
        self.btn_source.config(state="normal")
        self.initialize_graph()
        
    # Initialize graph with vertices and edges
    def initialize_graph(self):
        
        # positions for 10 nodes
        positions = [
            (100,100),(300,100),(500,100),(600,100),
            (150,250),(350,250),(550,250),(250,400),
            (450,400),(600,400)
        ]
        for pos in positions:
            self.vertex_counter +=1
            name=f"N{self.vertex_counter}"
            node=Vertex(name,pos[0],pos[1])
            self.vertex[name]=node
            id=self.canvas.create_oval(pos[0]-VERTEX_RADIUS,pos[1]-VERTEX_RADIUS,pos[0]+VERTEX_RADIUS,pos[1]+VERTEX_RADIUS,fill="lightgray")
            self.vertex_positions[id]=name
            self.canvas.create_text(pos[0],pos[1],text=name)

        # edges (v1, v2, cost)
        edges = [
            ("N1","N2",5), ("N2","N3",3), ("N3","N4",4), ("N1","N5",2),
            ("N5","N6",3), ("N6","N7",2), ("N7","N4",5), ("N5","N8",4),
            ("N6","N9",3), ("N7","N10",2), ("N8","N9",2), ("N9","N10",3)
        ]
        for v1,v2,cost in edges:
            self.add_edge(v1,v2,cost)