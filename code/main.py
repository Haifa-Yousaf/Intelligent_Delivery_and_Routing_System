# Starts the Tkinter window and welcome screen.

import tkinter as tk
from welcome import WelcomeScreen

if __name__ == "__main__":
    root = tk.Tk()
    welcome = WelcomeScreen(root)
    root.mainloop()