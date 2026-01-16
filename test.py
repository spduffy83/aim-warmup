import tkinter as tk

root = tk.Tk()
root.title("Test Window")
root.geometry("400x300")
label = tk.Label(root, text="If you see this, Tkinter works!")
label.pack(pady=50)
root.mainloop()