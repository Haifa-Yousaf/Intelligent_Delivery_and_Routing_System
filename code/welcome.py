# Displays the welcome screen and "Run Simulation" button

import tkinter as tk
from gui import GUI

class WelcomeScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Delivery Routing (Hybrid Version)")
        self.root.geometry("800x650")

        #Main canvas
        self.canvas = tk.Canvas(root, width=800, height=650, bg="#eaf6ff")
        self.canvas.pack(fill="both", expand=True)

        # Title and subtitles
        self.canvas.create_text(400, 80,
                                text="Intelligent Delivery & Logistics Routing System",
                                font=("Segoe UI", 24, "bold"),
                                fill="#2c3e50")

        self.canvas.create_text(400, 130,
                                text="Multiple Goals Hybrid Simulation",
                                font=("Segoe UI", 16),
                                fill="#34495e")

        self.canvas.create_text(400, 190,
                                text="Optimize delivery routes and explore dynamic logistics!",
                                font=("Segoe UI", 14),
                                fill="#2c3e50")
        #Adding car image
        self.car_photo = tk.PhotoImage(file="car.png")
        self.car_photo = self.car_photo.subsample(3, 3)

        self.canvas.create_image(400, 370, image=self.car_photo)

        self.canvas.create_line(0, 500, 800, 500, fill="black", width=4)
        self.canvas.create_line(0, 520, 800, 520, fill="gray", width=2, dash=(6, 4))

        self.start_button = tk.Button(root, text="Run Simulation",
                                     font=("Segoe UI", 14, "bold"),
                                     bg="#27ae60", fg="white",
                                     padx=20, pady=10,
                                     command=self.run_system)

        self.canvas.create_window(400, 580, window=self.start_button)

    # Destroying welcome canvas and launching the main routing GUI
    def run_system(self):
        self.canvas.destroy()
        GUI(self.root)