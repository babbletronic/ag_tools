import os
import tkinter as tk
from tkinter import filedialog, messagebox


def browse():
    path = filedialog.askdirectory(title="Choose parent folder")
    if path:
        folder_var.set(path)


def create_folders():
    prefix = prefix_var.get().strip() or "BFS"
    root = folder_var.get().strip()

    try:
        start = int(start_var.get())
        count = int(count_var.get())
        step = int(step_var.get())
    except ValueError:
        messagebox.showerror("Invalid input", "Start, count, and step must be whole numbers.")
        return

    if not root or not os.path.isdir(root):
        messagebox.showerror("Invalid folder", "Choose an existing parent folder.")
        return
    if count < 1 or step < 1:
        messagebox.showerror("Invalid input", "Count and step must be at least 1.")
        return

    created = []
    for i in range(count):
        n = start + i * step
        path = os.path.join(root, f"{prefix}_{n:04d}")
        os.makedirs(path, exist_ok=True)
        created.append(os.path.basename(path))

    messagebox.showinfo("Done", f"Created {len(created)} folders:\n{created[0]} to {created[-1]}")


root_win = tk.Tk()
root_win.title("Shot Folder Creator")
root_win.resizable(False, False)

pad = {"padx": 8, "pady": 4}

prefix_var = tk.StringVar(value="BFS")
start_var = tk.StringVar(value="10")
count_var = tk.StringVar(value="12")
step_var = tk.StringVar(value="10")
folder_var = tk.StringVar()

tk.Label(root_win, text="Prefix:").grid(row=0, column=0, sticky="e", **pad)
tk.Entry(root_win, textvariable=prefix_var, width=20).grid(row=0, column=1, columnspan=2, sticky="w", **pad)

tk.Label(root_win, text="Start number:").grid(row=1, column=0, sticky="e", **pad)
tk.Entry(root_win, textvariable=start_var, width=20).grid(row=1, column=1, columnspan=2, sticky="w", **pad)

tk.Label(root_win, text="Number of shots:").grid(row=2, column=0, sticky="e", **pad)
tk.Entry(root_win, textvariable=count_var, width=20).grid(row=2, column=1, columnspan=2, sticky="w", **pad)

tk.Label(root_win, text="Step:").grid(row=3, column=0, sticky="e", **pad)
tk.Entry(root_win, textvariable=step_var, width=20).grid(row=3, column=1, columnspan=2, sticky="w", **pad)

tk.Label(root_win, text="Parent folder:").grid(row=4, column=0, sticky="e", **pad)
tk.Entry(root_win, textvariable=folder_var, width=36).grid(row=4, column=1, sticky="w", **pad)
tk.Button(root_win, text="Browse...", command=browse).grid(row=4, column=2, sticky="w", **pad)

tk.Button(root_win, text="Create Folders", command=create_folders, width=20).grid(
    row=5, column=0, columnspan=3, pady=12
)

root_win.mainloop()