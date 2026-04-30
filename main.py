# main.py

import tkinter as tk
from welcome import WelcomeScreen

if __name__ == "__main__":
    root = tk.Tk()
    welcome = WelcomeScreen(root)
    root.mainloop()