"""Desktop Graphical User Interface for Facebook Scraper & AI Agent."""

import os
import sys
import json
import time
import socket
import urllib.request
import urllib.error
import subprocess
import threading
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


def is_port_in_use(port: int = 8000) -> bool:
    """Check if a TCP port is currently listening on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_port_pids(port: int = 8000) -> list[int]:
    """Retrieve process IDs listening on the specified port on Windows."""
    pids = []
    if os.name == "nt":
        cmd = f"""Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"""
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
        except Exception:
            pass
    return list(set(pids))


def kill_port_processes(port: int = 8000) -> None:
    """Kill any process listening on the specified port on Windows."""
    if os.name == "nt":
        cmd = f"""
        $pids = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {{
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }}
        """
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=5)
        except Exception:
            pass


def contains_hebrew(text: str) -> bool:
    """Check if the string contains any Hebrew Unicode characters."""
    return bool(re.search(r"[\u0590-\u05fe]", text))


class FacebookScraperApp:
    """Modern Desktop UI for Facebook Scraper with n8n/Bridge orchestration."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.current_pid = os.getpid()
        self.root.title(f"Facebook Scraper AI Autonomous Agent (PID: {self.current_pid})")
        self.root.geometry("980x880")
        self.root.minsize(800, 700)

        # Bridge process handle
        self.bridge_proc: subprocess.Popen = None
        self.is_running_task = False

        # Apply Modern Styling & Colors
        self.setup_styles()

        # Startup Bridge Check & Warning (including PIDs)
        self.handle_startup_bridge()

        # Build Main UI Layout
        self.build_ui()

        # Intercept window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Configure fonts, colors, and ttk styles."""
        self.bg_color = "#f4f6f9"
        self.card_bg = "#ffffff"
        self.accent_color = "#0d6efd"
        self.text_color = "#212529"
        self.border_color = "#dee2e6"

        self.root.configure(bg=self.bg_color)
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=self.bg_color, foreground="#1e293b", font=("Segoe UI", 13, "bold"))
        self.style.configure("Status.TLabel", background=self.bg_color, foreground="#475569", font=("Segoe UI", 9))
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure("Action.TButton", font=("Segoe UI", 9), padding=4)

    def handle_startup_bridge(self):
        """Check for existing bridge instances, display warning with PIDs if detected, and start fresh bridge."""
        existing_pids = get_port_pids(8000)
        # Filter out current process PID just in case
        conflicting_pids = [p for p in existing_pids if p != self.current_pid]

        if conflicting_pids or is_port_in_use(8000):
            pid_str = ", ".join(str(p) for p in conflicting_pids) if conflicting_pids else "Unknown (Port 8000 in use)"
            messagebox.showwarning(
                "Instance Warning - Conflicting Process",
                f"Warning: Another instance of the Facebook Scraper Bridge or UI is already running!\n\n"
                f"• Current UI Process PID     : {self.current_pid}\n"
                f"• Conflicting Process PID(s) : {pid_str}\n\n"
                f"The application will now terminate the previous instance and start a fresh bridge session."
            )
            kill_port_processes(8000)
            time.sleep(1.0)

        self.start_bridge_process()

    def start_bridge_process(self):
        """Launch the FastAPI Uvicorn bridge in a subprocess."""
        cmd = [sys.executable, "-m", "uvicorn", "src.n8n_bridge.server:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.bridge_proc = subprocess.Popen(cmd, creationflags=flags)
        except Exception as e:
            messagebox.showerror("Startup Error", f"Failed to launch bridge server: {e}")

    def on_closing(self):
        """Cleanly terminate bridge and worker processes when UI is closed."""
        if self.bridge_proc:
            try:
                self.bridge_proc.terminate()
                self.bridge_proc.kill()
            except Exception:
                pass

        kill_port_processes(8000)
        self.root.destroy()

    def build_ui(self):
        """Construct the 3-pane layout: Input (Top), Technical (Middle), Payload (Bottom)."""
        main_frame = ttk.Frame(self.root, padding="14")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---------------- Top Header Bar ----------------
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_lbl = ttk.Label(header_frame, text="Facebook Scraper Autonomous Agent", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT)

        self.status_lbl = ttk.Label(header_frame, text="🟢 Initializing Bridge...", style="Status.TLabel")
        self.status_lbl.pack(side=tk.RIGHT)

        # ---------------- Pane 1: User Prompt Input ----------------
        pane1_frame = tk.LabelFrame(
            main_frame, text=" 1. User Prompt (English & Hebrew RTL Support) ",
            bg=self.bg_color, fg="#334155", font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        pane1_frame.pack(fill=tk.X, pady=(0, 10))

        # Text input box for prompt
        self.prompt_text = tk.Text(
            pane1_frame, height=4, font=("Segoe UI", 11), wrap=tk.WORD,
            bg="#ffffff", fg=self.text_color, relief=tk.SOLID, bd=1, padx=8, pady=8
        )
        self.prompt_text.pack(fill=tk.X, pady=(0, 8))
        self.prompt_text.insert(
            tk.END, "Extract 5 posts from Python Devs group in HTML with table"
        )
        self.prompt_text.tag_configure("rtl", justify="right")
        self.prompt_text.tag_configure("ltr", justify="left")
        self.prompt_text.bind("<KeyRelease>", self.on_prompt_key_release)
        self.add_context_menu(self.prompt_text)

        # Button and options toolbar
        toolbar = ttk.Frame(pane1_frame)
        toolbar.pack(fill=tk.X)

        self.send_btn = tk.Button(
            toolbar, text="▶ Send Prompt", bg="#0d6efd", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=5,
            cursor="hand2", command=self.on_send_clicked
        )
        self.send_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.toggle_dir_btn = ttk.Button(toolbar, text="⇄ Force RTL / LTR", command=self.toggle_text_direction)
        self.toggle_dir_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clear_btn = ttk.Button(toolbar, text="Clear", command=lambda: self.prompt_text.delete("1.0", tk.END))
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 12))

        # Target Endpoint Selector
        ttk.Label(toolbar, text="Target:").pack(side=tk.LEFT, padx=(0, 4))
        self.endpoint_var = tk.StringVar(value="n8n-test")
        self.endpoint_combo = ttk.Combobox(
            toolbar, textvariable=self.endpoint_var, state="readonly", width=30,
            values=[
                "n8n-test (http://localhost:5678/webhook-test/fb-scrape-task)",
                "n8n-prod (http://localhost:5678/webhook/fb-scrape-task)",
                "direct-bridge (http://127.0.0.1:8000/pipeline)",
            ]
        )
        self.endpoint_combo.current(0)
        self.endpoint_combo.pack(side=tk.LEFT)

        # ---------------- Pane 2: Technical Info without Payload ----------------
        pane2_frame = tk.LabelFrame(
            main_frame, text=" 2. Technical Execution Details & Metadata (Payload Excluded) ",
            bg=self.bg_color, fg="#334155", font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        pane2_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        self.tech_text = tk.Text(
            pane2_frame, height=7, font=("Consolas", 10), wrap=tk.WORD,
            bg="#f8fafc", fg="#1e293b", relief=tk.SOLID, bd=1, padx=8, pady=6
        )
        self.tech_text.pack(fill=tk.BOTH, expand=True)
        self.tech_text.insert(tk.END, "Ready to execute. Technical metadata will appear here after sending prompt.\n")
        self.tech_text.config(state=tk.DISABLED)
        self.add_context_menu(self.tech_text)

        # ---------------- Pane 3: Output Payload ----------------
        pane3_frame = tk.LabelFrame(
            main_frame, text=" 3. Output Payload ",
            bg=self.bg_color, fg="#334155", font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        pane3_frame.pack(fill=tk.BOTH, expand=True)

        payload_toolbar = ttk.Frame(pane3_frame)
        payload_toolbar.pack(fill=tk.X, pady=(0, 6))

        self.copy_btn = tk.Button(
            payload_toolbar, text="📋 Copy All", bg="#198754", fg="#ffffff",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=3,
            cursor="hand2", command=self.copy_all_payload
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.save_btn = ttk.Button(payload_toolbar, text="💾 Save to File...", command=self.save_payload_to_file)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_feedback_lbl = ttk.Label(payload_toolbar, text="", style="Status.TLabel")
        self.copy_feedback_lbl.pack(side=tk.LEFT)

        # Payload Text Box
        self.payload_text = tk.Text(
            pane3_frame, font=("Consolas", 10), wrap=tk.NONE,
            bg="#ffffff", fg="#0f172a", relief=tk.SOLID, bd=1, padx=8, pady=8
        )
        scroll_y = ttk.Scrollbar(pane3_frame, orient=tk.VERTICAL, command=self.payload_text.yview)
        scroll_x = ttk.Scrollbar(pane3_frame, orient=tk.HORIZONTAL, command=self.payload_text.xview)
        self.payload_text.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.payload_text.pack(fill=tk.BOTH, expand=True)
        self.payload_text.insert(tk.END, "Output payload (HTML / Markdown / Text / Table) will be displayed here.")
        self.payload_text.config(state=tk.DISABLED)
        self.add_context_menu(self.payload_text)

        # Check Bridge Health in Background Thread
        threading.Thread(target=self.poll_bridge_health, daemon=True).start()

    def add_context_menu(self, widget: tk.Text):
        """Add right-click Cut/Copy/Paste/Select All context menu to text widget."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.tag_add("sel", "1.0", "end"))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def on_prompt_key_release(self, event=None):
        """Dynamically detect Hebrew and switch text alignment to RTL."""
        content = self.prompt_text.get("1.0", tk.END).strip()
        if contains_hebrew(content):
            self.prompt_text.tag_add("rtl", "1.0", "end")
            self.prompt_text.tag_remove("ltr", "1.0", "end")
        else:
            self.prompt_text.tag_add("ltr", "1.0", "end")
            self.prompt_text.tag_remove("rtl", "1.0", "end")

    def toggle_text_direction(self):
        """Explicit manual toggle between RTL and LTR."""
        current_tags = self.prompt_text.tag_names("1.0")
        if "rtl" in current_tags:
            self.prompt_text.tag_remove("rtl", "1.0", "end")
            self.prompt_text.tag_add("ltr", "1.0", "end")
        else:
            self.prompt_text.tag_remove("ltr", "1.0", "end")
            self.prompt_text.tag_add("rtl", "1.0", "end")

    def poll_bridge_health(self):
        """Check if FastAPI bridge is up and update status label."""
        for _ in range(15):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1.5) as resp:
                    if resp.status == 200:
                        self.root.after(0, lambda: self.status_lbl.config(text="🟢 Bridge Online (Port 8000)"))
                        return
            except Exception:
                pass
            time.sleep(1.0)
        self.root.after(0, lambda: self.status_lbl.config(text="🟡 Bridge starting up..."))

    def on_send_clicked(self):
        """Handle send button click and trigger scraping task in background thread."""
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("Empty Prompt", "Please enter a prompt before sending.")
            return

        if self.is_running_task:
            return

        self.is_running_task = True
        self.send_btn.config(state=tk.DISABLED, text="⏳ Running Task...", bg="#6c757d")
        self.status_lbl.config(text="⚙️ Executing Facebook Scraper Flow...")

        # Update Technical Pane
        self.update_tech_pane("Sending request...\nWaiting for response from workflow...")
        self.update_payload_pane("Executing scraping & AI synthesis...\nPlease wait...")

        # Run network call in background thread
        selected_endpoint = self.endpoint_combo.get()
        threading.Thread(target=self.execute_request_worker, args=(prompt, selected_endpoint), daemon=True).start()

    def execute_request_worker(self, prompt: str, endpoint_selection: str):
        """Worker thread executing the HTTP request to n8n or direct bridge."""
        start_time = time.time()

        # Determine target URL
        if "n8n-prod" in endpoint_selection:
            url = "http://localhost:5678/webhook/fb-scrape-task"
        elif "direct-bridge" in endpoint_selection:
            url = "http://127.0.0.1:8000/pipeline"
        else:
            url = "http://localhost:5678/webhook-test/fb-scrape-task"

        payload = {"prompt": prompt}
        headers = {"Content-Type": "application/json"}
        req_data = json.dumps(payload).encode("utf-8")

        response_data = None
        error_msg = None

        try:
            http_req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(http_req, timeout=180) as resp:
                raw_body = resp.read().decode("utf-8")
                try:
                    response_data = json.loads(raw_body)
                except Exception:
                    response_data = {"raw_output": raw_body}
        except urllib.error.URLError as e:
            error_msg = f"Network Connection Error: {e.reason}"
        except Exception as e:
            error_msg = f"Request Failed: {e}"

        elapsed = time.time() - start_time
        self.root.after(0, lambda: self.handle_response_completed(response_data, error_msg, elapsed, url))

    def handle_response_completed(self, data: dict, error: str, elapsed: float, url: str):
        """Process API response on the main UI thread and populate panes."""
        self.is_running_task = False
        self.send_btn.config(state=tk.NORMAL, text="▶ Send Prompt", bg="#0d6efd")
        self.status_lbl.config(text="🟢 Idle - Ready")

        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S')

        if error:
            self.update_tech_pane(
                f"[Status]          : ERROR\n"
                f"[Endpoint Used]   : {url}\n"
                f"[Elapsed Time]    : {elapsed:.2f}s\n"
                f"[Timestamp]       : {timestamp_str}\n"
                f"[Error Details]   : {error}\n\n"
                f"--- Technical Details ---\n"
                f"Denoted payload   : [payload] (none returned due to network/execution failure)"
            )
            formatted_error_result = (
                f"================================================================================\n"
                f"❌ EXECUTION ERROR REPORT\n"
                f"================================================================================\n"
                f"Target Endpoint : {url}\n"
                f"Elapsed Time    : {elapsed:.2f} seconds\n"
                f"Timestamp       : {timestamp_str}\n\n"
                f"[Error Summary]\n"
                f"{error}\n\n"
                f"[Troubleshooting Guide]\n"
                f"1. If using n8n webhook, ensure n8n is running (http://localhost:5678) and workflow is active.\n"
                f"2. You can switch the 'Target' dropdown to 'direct-bridge (http://127.0.0.1:8000/pipeline)'.\n"
                f"3. Verify bridge health at: http://127.0.0.1:8000/health\n"
                f"4. Inspect detailed logs at: logs/scraper.log\n"
                f"================================================================================"
            )
            self.update_payload_pane(formatted_error_result)
            return

        # Extract payload vs metadata
        payload_content = ""
        tech_dict = dict(data)

        # Check for n8n format: "result"
        if "result" in tech_dict:
            payload_content = tech_dict["result"]
            tech_dict["result"] = "[payload]"
        # Check for bridge pipeline format: "formatted_output"
        elif "formatted_output" in tech_dict:
            payload_content = tech_dict["formatted_output"]
            tech_dict["formatted_output"] = "[payload]"
        elif "raw_output" in tech_dict:
            payload_content = tech_dict["raw_output"]
            tech_dict["raw_output"] = "[payload]"

        status = data.get("status", "completed")
        task_id = data.get("task_id", "N/A")
        posts_count = data.get("posts_scraped", data.get("posts_count", 0))

        tech_summary = (
            f"[Status]          : {status}\n"
            f"[Task ID]         : {task_id}\n"
            f"[Posts Scraped]   : {posts_count}\n"
            f"[Endpoint Used]   : {url}\n"
            f"[Execution Time]  : {elapsed:.2f} seconds\n"
            f"[Timestamp]       : {timestamp_str}\n\n"
            f"--- Technical JSON Response (Payload Redacted) ---\n"
            f"{json.dumps(tech_dict, indent=2, ensure_ascii=False)}"
        )
        self.update_tech_pane(tech_summary)

        # Format Pane 3 Output based on execution status
        if status == "obstacle_encountered":
            formatted_obstacle = (
                f"================================================================================\n"
                f"⚠️ OBSTACLE / SESSION CHALLENGE ENCOUNTERED\n"
                f"================================================================================\n"
                f"Task ID         : {task_id}\n"
                f"Status          : Obstacle Encountered (0 posts scraped)\n"
                f"Target Endpoint : {url}\n"
                f"Elapsed Time    : {elapsed:.2f} seconds\n"
                f"Timestamp       : {timestamp_str}\n\n"
                f"[AI Diagnostic / Reason]\n"
                f"{payload_content}\n\n"
                f"[Recommended Actions]\n"
                f"• Re-authenticate session: Run 'python login.py' in a terminal to refresh cookies.\n"
                f"• Ensure target Facebook groups are public and accessible without approval.\n"
                f"• Check execution details in logs/scraper.log.\n"
                f"================================================================================"
            )
            self.update_payload_pane(formatted_obstacle)
        elif status == "error":
            formatted_err = (
                f"================================================================================\n"
                f"❌ SERVER / AGENT ERROR REPORT\n"
                f"================================================================================\n"
                f"Task ID         : {task_id}\n"
                f"Status          : Error\n"
                f"Target Endpoint : {url}\n"
                f"Elapsed Time    : {elapsed:.2f} seconds\n"
                f"Timestamp       : {timestamp_str}\n\n"
                f"[Error Details]\n"
                f"{payload_content}\n\n"
                f"[Troubleshooting]\n"
                f"• Review server logs at: logs/scraper.log\n"
                f"================================================================================"
            )
            self.update_payload_pane(formatted_err)
        elif not payload_content or (posts_count == 0 and "Empty" in payload_content):
            formatted_empty = (
                f"================================================================================\n"
                f"ℹ️ SCRAPE COMPLETED (0 MATCHING POSTS FOUND)\n"
                f"================================================================================\n"
                f"Task ID         : {task_id}\n"
                f"Status          : Success (0 matching posts)\n"
                f"Target Endpoint : {url}\n"
                f"Elapsed Time    : {elapsed:.2f} seconds\n"
                f"Timestamp       : {timestamp_str}\n\n"
                f"[Details]\n"
                f"The scraping run completed, but no posts matched your filter criteria or the discovered groups had no accessible user posts.\n"
                f"Try broadening your search keywords or targeting an active public group directly.\n"
                f"================================================================================"
            )
            self.update_payload_pane(formatted_empty)
        else:
            self.update_payload_pane(payload_content)

    def update_tech_pane(self, text: str):
        """Safely update the technical metadata text box."""
        self.tech_text.config(state=tk.NORMAL)
        self.tech_text.delete("1.0", tk.END)
        self.tech_text.insert(tk.END, text)
        self.tech_text.config(state=tk.DISABLED)

    def update_payload_pane(self, text: str):
        """Safely update the output payload text box."""
        self.payload_text.config(state=tk.NORMAL)
        self.payload_text.delete("1.0", tk.END)
        self.payload_text.insert(tk.END, text)
        self.payload_text.config(state=tk.DISABLED)

    def copy_all_payload(self):
        """Copy entire payload text to Windows clipboard."""
        content = self.payload_text.get("1.0", tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.copy_feedback_lbl.config(text="✓ Copied to Clipboard!")
            self.root.after(2500, lambda: self.copy_feedback_lbl.config(text=""))

    def save_payload_to_file(self):
        """Save payload content to a user-chosen file."""
        content = self.payload_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Empty Payload", "There is no payload content to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[
                ("HTML Files", "*.html"),
                ("Markdown Files", "*.md"),
                ("Text Files", "*.txt"),
                ("JSON Files", "*.json"),
                ("All Files", "*.*"),
            ]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Saved", f"Payload saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {e}")


def launch_ui():
    """Main function to launch the desktop application."""
    root = tk.Tk()
    app = FacebookScraperApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_ui()
