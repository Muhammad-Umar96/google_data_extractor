import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import pandas as pd
from tkinter import messagebox, filedialog

# Scrapy imports
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from google.spiders.google_spider import GoogleSpiderSpider

# Global variables
is_scraping = False
was_stopped = False
batch_stop_requested = False
current_mode = None
total_batch_urls = 0
current_batch_idx = 0

# Global variables
is_scraping = False
scrapy_process = None
was_stopped = False
batch_stop_requested = False
current_mode = None  # "single" | "batch" | None
total_batch_urls = 0
current_batch_idx = 0

# ==================== LOG FUNCTION ====================
def log(msg):
    if 'terminal' in globals() and terminal.winfo_exists():
        terminal.config(state="normal")
        terminal.insert(tk.END, msg + "\n")
        terminal.see(tk.END)
        terminal.config(state="disabled")
        terminal.update_idletasks()

# ==================== MODE MANAGEMENT ====================
def set_single_mode(event=None):
    """Lock into Single URL mode when user types in the URL field."""
    global current_mode

    typed = entry.get().strip()
    has_real_text = typed and typed != "Paste your Google Maps URL here"

    if has_real_text and current_mode != "single":
        current_mode = "single"
        path_entry.config(state="disabled", disabledforeground="#aaa", disabledbackground="#f0f0f0")
        import_btn.config(state="disabled", bg="#bdbdbd", activebackground="#bdbdbd")
        clear_csv_btn.pack_forget()
        clear_url_btn.pack(side="left", padx=(4, 0))   # ← show ✕ for URL
        button.config(text="Start Bot", bg="#4CAF50", activebackground="#45a049",
                      command=open_link, state="normal")
        mode_label.config(text="● URL Mode", fg="#FF9800")

    elif not has_real_text and current_mode == "single":
        _clear_mode()

    elif not has_real_text and current_mode == "single":
        # URL was cleared — release the lock
        _clear_mode()


def set_batch_mode(event=None):
    """Lock into Batch mode after a CSV is imported."""
    global current_mode

    typed = path_entry.get().strip()
    has_real_text = typed and typed != "/path/to/my_data.csv"

    if has_real_text and current_mode != "batch":
        current_mode = "batch"
    
        # Grey out URL entry
        entry.config(state="disabled", disabledforeground="#aaa", disabledbackground="#f0f0f0")
        # Show ✕ button next to Import CSV
        clear_csv_btn.pack(side="left", padx=(4, 0))
        # Button → Start Batch Processing
        button.config(text="Start Bot", bg="#4CAF50",
                    activebackground="#4CAF50", command=run_batch, state="normal")
        mode_label.config(text="● CSV Mode", fg="#FF9800")

    elif not has_real_text and current_mode == "batch":
        # URL was cleared — release the lock
        _clear_mode()


def _clear_mode():
    """Release mode lock and restore all widgets to their default state."""
    global current_mode
    current_mode = None

    entry.config(state="normal", fg="grey", bg="white")
    path_entry.config(state="normal", fg="grey", bg="white")
    import_btn.config(state="normal", bg="#2196F3", activebackground="#1976D2")
    clear_csv_btn.pack_forget()
    clear_url_btn.pack_forget()   # ← also hide URL ✕

    button.config(text="Start Bot", bg="#4CAF50", activebackground="#45a049",
                  command=open_link, state="normal")
    mode_label.config(text="", fg="#546E7A")

# ==================== STOP SCRAPING ====================
def stop_scraping():
    global is_scraping, was_stopped, batch_stop_requested
    was_stopped = True
    batch_stop_requested = True
    is_scraping = False
    log(" Stopping scraper...")
    messagebox.showinfo("Stopped", "Scraping was stopped by user.")

# ==================== RUN SPIDER (NEW DIRECT VERSION) ====================
def run_spider(url, output_file="output.csv"):
    global is_scraping, was_stopped

    is_scraping = True
    was_stopped = False
    final_found = 0
    final_scraped = 0

    try:
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                log(f"Cleared old {output_file}")
            except:
                pass

        # Reset progress bars
        progress_found['value'] = 0
        progress_scraped['value'] = 0
        label_found.config(text="Items Found: 0")
        label_scraped.config(text="Items Scraped: 0")

        terminal.config(state="normal")
        terminal.delete(1.0, tk.END)
        terminal.config(state="disabled")

        log("Starting scraper...")
        log("=" * 60)

        # === Direct Scrapy Run ===
        settings = get_project_settings()
        settings.set('FEEDS', {output_file: {'format': 'csv'}}, priority='cmdline')

        process = CrawlerProcess(settings)

        def crawl():
            nonlocal final_found, final_scraped
            try:
                process.crawl(GoogleSpiderSpider, start_url=url)
                process.start()   # This blocks until finished
            except Exception as e:
                log(f"Error during crawl: {e}")

        # Run crawler in a thread so GUI doesn't freeze
        thread = threading.Thread(target=crawl, daemon=True)
        thread.start()
        thread.join()   # Wait for it to finish

        log("=" * 60)
        log("✓ Scraping completed!")
        log("=" * 60)

        if current_mode != "batch":
            progress_urls['value'] = 1
            label_urls.config(text="URL(s) Processed: 1 / 1")

    except Exception as e:
        log(f"\n Error: {str(e)}")
        messagebox.showerror("Error", str(e))

    finally:
        is_scraping = False
        if not was_stopped and current_mode != "batch":
            clear_url_btn.config(state="normal")
            entry.config(state="normal", fg="black", bg="white")
            button.config(state="normal", text="Start Bot",
                          bg="#4CAF50", activebackground="#45a049", command=open_link)
            messagebox.showinfo(
                "Scraping Complete",
                f"Scraping finished successfully!\n\nData saved to {output_file}"
            )

    return final_found, final_scraped

# ==================== CLEANUP WHEN CLOSING ====================
def on_closing():
    global is_scraping, scrapy_process

    if is_scraping:
        if messagebox.askyesno("Quit", "Scraping is still running.\nDo you want to stop it and exit?"):
            if scrapy_process and scrapy_process.poll() is None:
                try:
                    scrapy_process.kill()
                    log("Scrapy process terminated by user.")
                except:
                    pass
            is_scraping = False
            time.sleep(0.3)
            window.destroy()
        else:
            return
    else:
        window.destroy()

# ==================== IMPORT FILE ====================
def import_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if file_path:
        path_entry.config(state="normal")
        path_entry.delete(0, tk.END)
        path_entry.insert(0, file_path)
        path_entry.config(fg='black')
        set_batch_mode()


def clear_csv():
    """✕ button — clears the CSV path and exits batch mode only."""
    path_entry.config(state="normal")
    path_entry.delete(0, tk.END)
    path_entry.config(fg="grey")
    _clear_mode()

def clear_url():
    """✕ button — clears the URL and exits single mode."""
    entry.config(state="normal")
    entry.delete(0, tk.END)
    entry.config(fg="grey")
    clear_url_btn.pack_forget()
    _clear_mode()

# ==================== BATCH LOGIC ====================
def _batch_thread():
    global batch_stop_requested, total_batch_urls, current_batch_idx

    csv_path = path_entry.get().strip()
    if not csv_path or csv_path == "/path/to/my_data.csv":
        messagebox.showwarning("Input Error", "Please import a CSV file first.")
        _restore_batch_button()
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        messagebox.showerror("CSV Error", f"Could not read CSV:\n{e}")
        _restore_batch_button()
        return

    url_col = None
    for url in ["url", "URL", "google_maps_url", "link", "Link"]:
        if url in df.columns:
            url_col = url
            break
    if url_col is None:
        col_lower = {c.lower(): c for c in df.columns}
        url_col = col_lower.get("url") or col_lower.get("link")
    if url_col is None:
        messagebox.showerror(
            "Column Error",
            f"No URL column found.\nExpected 'url' or 'link'.\nAvailable: {list(df.columns)}"
        )
        _restore_batch_button()
        return

    urls = df[url_col].dropna().astype(str).tolist()
    if not urls:
        messagebox.showwarning("Empty", "No URLs found in the CSV.")
        _restore_batch_button()
        return

    total = len(urls)
    total_batch_urls = total
    current_batch_idx = 0

    # Reset URL progress bar
    progress_urls['maximum'] = total
    progress_urls['value'] = 0
    label_urls.config(text=f"URL(s) Processed: 0 / {total}")

    log("=" * 60)
    log(f"Batch mode: {total} URL(s) queued  (column: '{url_col}')")
    log("=" * 60)

    grand_found = 0
    grand_scraped = 0

    for row_idx, url in df[url_col].dropna().items():
        if batch_stop_requested:
            break

        current_batch_idx += 1
        progress_urls['value'] = current_batch_idx  
        label_urls.config(text=f"URL(s) Processed: {current_batch_idx} / {total}")
        log(f"\n[{current_batch_idx}/{total}] {url}")
        output_file = f"results_row_{row_idx + 1}.csv"
        found, scraped = run_spider(url, output_file=output_file)

        grand_found += found
        grand_scraped += scraped

        log(f"[{current_batch_idx}/{total}] Saved → {output_file}  (found={found}, scraped={scraped})")

    log("=" * 60)
    log(f"Batch complete — total found: {grand_found}, total scraped: {grand_scraped}")
    log("=" * 60)

    if not batch_stop_requested:
        label_urls.config(text=f"URL(s) Processed: {total} / {total} ✓")
        messagebox.showinfo(
            "Batch Complete",
            f"All {total} URLs processed!\n"
            f"Total scraped: {grand_scraped}\n"
            f"Files saved as results_*.csv"
        )

    _restore_batch_button()


def _restore_batch_button():
    clear_csv_btn.config(state="normal") 
    import_btn.config(state="normal", bg="#2196F3", activebackground="#1976D2")
    path_entry.config(state="normal", fg="black", bg="white")
    button.config(
        text="Start Bot",
        bg="#4CAF50",
        activebackground="#4CAF50",
        command=run_batch,
        state="normal"
    )


def run_batch():
    global batch_stop_requested
    batch_stop_requested = False
    clear_csv_btn.config(state="disabled")  
    import_btn.config(state="disabled")
    path_entry.config(state="disabled", disabledforeground="#555", disabledbackground="#f0f0f0")
    button.config(
        text="Stop Bot",
        bg="#f44336",
        activebackground="#e53935",
        command=stop_scraping
    )
    threading.Thread(target=_batch_thread, daemon=True).start()

# ==================== SINGLE URL START ====================
def open_link():
    url = entry.get().strip()
    if not url or url == "Paste your Google Maps URL here":
        messagebox.showwarning("Input Error", "Please enter a valid Google Maps URL")
        return
    progress_urls['maximum'] = 1        
    progress_urls['value'] = 1          
    label_urls.config(text="URL(s) Processed: 1 / 1")
    clear_url_btn.config(state="disabled")
    entry.config(state="disabled", disabledforeground="#555", disabledbackground="#f0f0f0")
    button.config(state="active", text="Stop Bot",
                  bg="#f44336", activebackground="#e53935", command=stop_scraping)
    threading.Thread(target=run_spider, args=(url,), daemon=True).start()

# ==================== PLACEHOLDER HELPERS ====================
def clear_placeholder_url(event):
    if entry.get() == "Paste your Google Maps URL here":
        entry.delete(0, tk.END)
        entry.config(fg='black')

def add_placeholder_url(event):
    if not entry.get():
        entry.insert(0, "Paste your Google Maps URL here")
        entry.config(fg='grey')
    set_single_mode()

def clear_placeholder_import(event):
    if path_entry.get() == "/path/to/my_data.csv":
        path_entry.delete(0, tk.END)
        path_entry.config(fg='black')

def add_placeholder_import(event):
    if not path_entry.get():
        path_entry.insert(0, "/path/to/my_data.csv")
        path_entry.config(fg='grey')
    set_batch_mode()

# ==================== MAIN WINDOW SETUP ====================
window = tk.Tk()
window.title("Google Data Extractor")
window.geometry("900x600")
window.configure(bg="#f4f6f8")
window.protocol("WM_DELETE_WINDOW", on_closing)

# TOP FRAME
top_frame = tk.Frame(window, bg="white", bd=2, relief="groove")
top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

# BOTTOM LEFT (PROGRESS)
progress_frame = tk.Frame(window, bg="white", bd=2, relief="groove")
progress_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

# BOTTOM RIGHT (TERMINAL)
terminal_frame = tk.Frame(window, bg="white", bd=2, relief="groove")
terminal_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

window.grid_rowconfigure(0, weight=1)
window.grid_rowconfigure(1, weight=2)
window.grid_columnconfigure(0, weight=1)
window.grid_columnconfigure(1, weight=1)

# ── Title ─────────────────────────────────────────────────────
tk.Label(
    top_frame,
    text="Google Data Extractor",
    font=("Segoe UI", 28, "bold"),
    bg="white",
    fg="#546E7A"
).pack(pady=(20, 4))

# ── Mode indicator (blank until a mode is active) ─────────────
mode_label = tk.Label(
    top_frame,
    text="",
    font=("Segoe UI", 10, "bold"),
    bg="white",
    fg="#546E7A"
)
mode_label.pack(pady=(0, 8))

# ── Single URL entry ──────────────────────────────────────────
url_row = tk.Frame(top_frame, bg="white")
url_row.pack(pady=(0, 10))

entry = tk.Entry(
    url_row,
    width=80,
    font=("Segoe UI", 12),
    fg="grey",
    relief="flat",
    highlightthickness=1,
    highlightbackground="#ccc",
    highlightcolor="#4CAF50",
    bd=5
)
entry.insert(0, "Paste your Google Maps URL here")
entry.pack(side="left", ipady=6)
entry.bind("<FocusIn>", clear_placeholder_url)
entry.bind("<FocusOut>", add_placeholder_url)
entry.bind("<KeyRelease>", set_single_mode)

# ✕ clear-URL button — hidden until Single URL mode is active
clear_url_btn = tk.Button(
    url_row,
    text="✕",
    font=("Segoe UI", 10),
    bg="#eeeeee",
    fg="#777",
    activebackground="#e0e0e0",
    activeforeground="#333",
    relief="flat",
    padx=6,
    pady=10,
    cursor="hand2",
    command=lambda: clear_url()
)

# ── CSV import row ────────────────────────────────────────────
import_row = tk.Frame(top_frame, bg="white")
import_row.pack(pady=(0, 10))

path_entry = tk.Entry(
    import_row,
    width=66,
    font=("Segoe UI", 12),
    fg="grey",
    relief="flat",
    highlightthickness=1,
    highlightbackground="#ccc",
    highlightcolor="#4CAF50",
    bd=5
)
path_entry.insert(0, "/path/to/my_data.csv")
path_entry.pack(side="left", ipady=6)
path_entry.bind("<FocusIn>", clear_placeholder_import)
path_entry.bind("<FocusOut>", add_placeholder_import)
path_entry.bind("<KeyRelease>", set_batch_mode)


import_btn = tk.Button(
    import_row,
    text="Import CSV",
    font=("Segoe UI", 11, "bold"),
    bg="#2196F3",
    fg="white",
    activebackground="#1976D2",
    activeforeground="white",
    relief="flat",
    padx=15,
    pady=10,
    cursor="hand2",
    command=import_file
)
import_btn.pack(side="left", padx=(8, 0))

# ✕ clear-CSV button — created but NOT packed; set_batch_mode() shows it
clear_csv_btn = tk.Button(
    import_row,
    text="✕",
    font=("Segoe UI", 10),
    bg="#eeeeee",
    fg="#777",
    activebackground="#e0e0e0",
    activeforeground="#333",
    relief="flat",
    padx=6,
    pady=10,
    cursor="hand2",
    command=clear_csv
)

# ── Main action button ────────────────────────────────────────
button = tk.Button(
    top_frame,
    text="Start Bot",
    font=("Segoe UI", 12, "bold"),
    bg="#4CAF50",
    fg="white",
    activebackground="#45a049",
    activeforeground="white",
    relief="flat",
    padx=20,
    pady=10,
    cursor="hand2",
    command=open_link
)
button.pack(pady=(6, 20))

# ── Progress section ──────────────────────────────────────────
label_urls = tk.Label(
    progress_frame,
    text="URL(s) Processed: 0 / 0",
    font=("Segoe UI", 12, "bold"),
    bg="white",
    fg="#546E7A"
)
label_urls.pack(pady=(20, 5), anchor="w", padx=20)

progress_urls = ttk.Progressbar(
    progress_frame, orient='horizontal', length=350, mode='determinate')
progress_urls.pack(pady=(0, 20), anchor="w", padx=20)

label_found = tk.Label(
    progress_frame,
    text="Items Found: 0",
    font=("Segoe UI", 12, "bold"),
    bg="white",
    fg="#546E7A"
)
label_found.pack(pady=(5, 5), anchor="w", padx=20)

progress_found = ttk.Progressbar(
    progress_frame, orient='horizontal', length=350, mode='determinate')
progress_found.pack(pady=(0, 30), anchor="w", padx=20)

label_scraped = tk.Label(
    progress_frame,
    text="Items Scraped: 0",
    font=("Segoe UI", 12, "bold"),
    bg="white",
    fg="#546E7A"
)
label_scraped.pack(pady=(0, 5), anchor="w", padx=20)

progress_scraped = ttk.Progressbar(
    progress_frame, orient='horizontal', length=350, mode='determinate')
progress_scraped.pack(pady=(0, 20), anchor="w", padx=20)

# ── Terminal section ──────────────────────────────────────────
tk.Label(
    terminal_frame,
    text="TERMINAL OUTPUT",
    font=("Segoe UI", 12, "bold"),
    bg="white",
    fg="#546E7A"
).pack(pady=10)

terminal = tk.Text(
    terminal_frame,
    height=15,
    font=("Consolas", 9),
    wrap="word",
    state="disabled"
)
terminal.pack(fill="both", expand=True, padx=10, pady=10)

window.mainloop()