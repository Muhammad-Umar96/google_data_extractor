import tkinter as tk

window = tk.Tk()

window.title("Google Bot")
window.geometry("800x500")

label = tk.Label(window, text="Google Bot", font=("Arial", 24))
label.pack(pady=20, padx=20)

inputbox = tk.Text(window, height=1, width=50)
inputbox.pack(pady=10, padx=20)

button = tk.Button(window, text="Start Bot", font=("Arial", 12))
button.pack(pady=10, padx=20)

window.mainloop()