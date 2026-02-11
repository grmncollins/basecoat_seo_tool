"""
Basecoat SEO Image Tool
Analyzes painting company images using Google Gemini AI
Generates SEO-friendly titles and alt text, then renames files.
"""

import os
import sys
import json
import re
import threading
import base64
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from google import genai

# ─── Constants ────────────────────────────────────────────────────────────────

APP_TITLE = "Basecoat SEO Image Tool"
APP_SIZE = "1150x780"
CONFIG_FILE = "config.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"}
THUMB_SIZE = (72, 72)
GEMINI_MODEL = "gemini-2.5-flash"

PAINTING_TAGS = [
    "Interior House Painting",
    "Exterior House Painting",
    "Deck Painting",
    "Deck Staining",
    "Fence Painting",
    "Fence Staining",
    "Interior Commercial Painting",
    "Exterior Commercial Painting",
    "Arbor Painting",
    "Gazebo Painting",
    "Shed Painting",
    "Shed Staining",
    "Playhouse Staining",
    "Barn Painting",
    "School Painting",
    "Hospital Painting",
    "Medical Facility Painting",
    "Hotel & Motel Painting",
    "Apartment Complex Painting",
    "Restaurant Painting",
    "Church Painting",
    "Religious Building Painting",
    "Gym Painting",
    "Fitness Center Painting",
    "Retail Store Painting",
    "Storefront Painting",
    "Office Painting",
    "Cabinet Painting",
    "Epoxy Floor Coating",
    "Epoxy Countertop Coating",
    "Popcorn Ceiling Removal",
    "Concrete Coating",
    "Pressure Washing",
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_config_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, CONFIG_FILE)


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_config(data):
    path = get_config_path()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def sanitize_filename(title: str) -> str:
    name = re.sub(r"[^\w\s-]", "", title).strip()
    name = re.sub(r"[\s]+", "-", name)
    return name


def make_unique_path(folder: str, stem: str, ext: str) -> str:
    candidate = os.path.join(folder, f"{stem}{ext}")
    if not os.path.exists(candidate):
        return candidate
    counter = 2
    while True:
        candidate = os.path.join(folder, f"{stem}-{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def get_mime_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    return mapping.get(ext, "image/jpeg")


def make_thumbnail(filepath: str) -> ImageTk.PhotoImage | None:
    try:
        img = Image.open(filepath)
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        bg = Image.new("RGB", THUMB_SIZE, (49, 50, 68))
        offset = ((THUMB_SIZE[0] - img.size[0]) // 2, (THUMB_SIZE[1] - img.size[1]) // 2)
        bg.paste(img, offset)
        return ImageTk.PhotoImage(bg)
    except Exception:
        return None


# ─── Gemini API (new google.genai SDK) ────────────────────────────────────────

def analyze_image(filepath: str, api_key: str, tags: list[str]) -> dict:
    client = genai.Client(api_key=api_key)

    tag_context = ""
    if tags:
        tag_context = (
            f"\n\nContext: This image is from a painting company's portfolio. "
            f"The likely categories are: {', '.join(tags)}. "
            f"Use these as SEO keyword hints if they match the visual content."
        )

    prompt = (
        "You are an SEO specialist for painting companies across the US. "
        "Analyze this image and return ONLY a JSON object with two keys:\n"
        '  "title": A short, SEO-friendly title (2-5 words) suitable as a web page title and filename. '
        "Use title case. Examples: 'Exterior House Painting', 'Interior Door Painting', 'White Brick Exterior Home Painting'.\n"
        '  "alt_text": An SEO-optimized alt text description under 125 characters. '
        "Describe ONLY the painted surface, structure, color, and painting work visible. "
        "Focus on what was painted, the color, and the type of structure.\n\n"
        "STRICT RULES:\n"
        "- Analyze the VISUAL content, not the filename.\n"
        "- Title should work as a filename (no special characters besides spaces).\n"
        "- Alt text must be under 125 characters.\n"
        "- DO NOT mention nature, weather, sky, trees, landscaping, sun, clouds, or surroundings.\n"
        "- DO NOT mention driveways, lawns, yards, or non-painted elements.\n"
        "- Focus ONLY on the painted structure, paint colors, and painting work.\n"
        "- Return ONLY valid JSON, no markdown, no explanation.\n"
        f"{tag_context}"
    )

    with open(filepath, "rb") as f:
        image_bytes = f.read()

    mime = get_mime_type(filepath)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            prompt,
            {
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                }
            },
        ],
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    result = json.loads(text)
    return {
        "title": result.get("title", "Untitled"),
        "alt_text": result.get("alt_text", ""),
    }


# ─── Main Application ────────────────────────────────────────────────────────

class BasecoatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(APP_SIZE)
        self.root.minsize(950, 650)

        self.config = load_config()
        self.api_key = self.config.get("api_key", "")
        self.folder_path = ""
        self.image_files: list[str] = []
        self.results: list[dict] = []
        self.processing = False
        self.tag_vars: dict[str, tk.BooleanVar] = {}
        self._thumb_refs: list[ImageTk.PhotoImage] = []

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        BG = "#1e1e2e"
        FG = "#cdd6f4"
        ACCENT = "#89b4fa"
        SURFACE = "#313244"
        GREEN = "#a6e3a1"
        RED = "#f38ba8"
        YELLOW = "#f9e2af"

        self.root.configure(bg=BG)

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=FG,
                         padding=[16, 8], font=("Segoe UI", 11, "bold"))
        style.map("TNotebook.Tab",
                   background=[("selected", ACCENT)],
                   foreground=[("selected", "#1e1e2e")])

        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG, foreground=ACCENT,
                         font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground="#a6adc8",
                         font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=BG, foreground=YELLOW,
                         font=("Segoe UI", 10, "italic"))

        style.configure("Accent.TButton", background=ACCENT, foreground="#1e1e2e",
                         font=("Segoe UI", 10, "bold"), padding=[14, 8])
        style.map("Accent.TButton", background=[("active", "#74c7ec")])

        style.configure("Green.TButton", background=GREEN, foreground="#1e1e2e",
                         font=("Segoe UI", 10, "bold"), padding=[14, 8])
        style.map("Green.TButton", background=[("active", "#94e2d5")])

        style.configure("Red.TButton", background=RED, foreground="#1e1e2e",
                         font=("Segoe UI", 10, "bold"), padding=[14, 8])
        style.map("Red.TButton", background=[("active", "#eba0ac")])

        style.configure("Secondary.TButton", background=SURFACE, foreground=FG,
                         font=("Segoe UI", 10), padding=[14, 8])
        style.map("Secondary.TButton", background=[("active", "#45475a")])

        style.configure("Orange.TButton", background="#fab387", foreground="#1e1e2e",
                         font=("Segoe UI", 10, "bold"), padding=[14, 8])
        style.map("Orange.TButton", background=[("active", "#f9e2af")])

        style.configure("Tag.TCheckbutton", background=BG, foreground=FG,
                         font=("Segoe UI", 9))
        style.map("Tag.TCheckbutton", background=[("active", BG)])

        style.configure("TEntry", fieldbackground=SURFACE, foreground=FG,
                         insertcolor=FG, font=("Segoe UI", 11))

        style.configure("Treeview", background=SURFACE, foreground=FG,
                         fieldbackground=SURFACE, font=("Segoe UI", 9),
                         rowheight=80)
        style.configure("Treeview.Heading", background="#45475a", foreground=FG,
                         font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#45475a")])

        style.configure("Accent.Horizontal.TProgressbar",
                         troughcolor=SURFACE, background=ACCENT, thickness=8)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_process = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_process, text="  Process Images  ")
        self.notebook.add(self.tab_settings, text="  Settings  ")

        self._build_process_tab()
        self._build_settings_tab()

    def _build_process_tab(self):
        frame = self.tab_process

        top = ttk.Frame(frame)
        top.pack(fill="x", padx=16, pady=(16, 8))
        ttk.Label(top, text="Image Folder SEO Processor", style="Header.TLabel").pack(side="left")
        self.btn_folder = ttk.Button(top, text="Choose Folder", style="Accent.TButton",
                                      command=self._choose_folder)
        self.btn_folder.pack(side="right")

        self.lbl_folder = ttk.Label(frame, text="No folder selected", style="Sub.TLabel")
        self.lbl_folder.pack(anchor="w", padx=16)

        # Tags
        tag_frame_outer = ttk.Frame(frame)
        tag_frame_outer.pack(fill="x", padx=16, pady=(10, 4))
        ttk.Label(tag_frame_outer, text="Optional Context Tags (select if you know what's in the folder):").pack(anchor="w")

        tag_container = ttk.Frame(frame)
        tag_container.pack(fill="x", padx=16, pady=(0, 8))

        tag_canvas = tk.Canvas(tag_container, bg="#1e1e2e", highlightthickness=0, height=105)
        tag_scrollbar = ttk.Scrollbar(tag_container, orient="vertical", command=tag_canvas.yview)
        tag_scroll_frame = ttk.Frame(tag_canvas)
        tag_scroll_frame.bind("<Configure>",
                               lambda e: tag_canvas.configure(scrollregion=tag_canvas.bbox("all")))
        tag_canvas.create_window((0, 0), window=tag_scroll_frame, anchor="nw")
        tag_canvas.configure(yscrollcommand=tag_scrollbar.set)
        tag_canvas.pack(side="left", fill="x", expand=True)
        tag_scrollbar.pack(side="right", fill="y")

        for i, tag in enumerate(PAINTING_TAGS):
            var = tk.BooleanVar(value=False)
            self.tag_vars[tag] = var
            cb = ttk.Checkbutton(tag_scroll_frame, text=tag, variable=var, style="Tag.TCheckbutton")
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 18), pady=1)

        tag_btn_frame = ttk.Frame(frame)
        tag_btn_frame.pack(fill="x", padx=16, pady=(0, 6))
        ttk.Button(tag_btn_frame, text="Select All", style="Secondary.TButton",
                    command=lambda: self._set_all_tags(True)).pack(side="left", padx=(0, 6))
        ttk.Button(tag_btn_frame, text="Deselect All", style="Secondary.TButton",
                    command=lambda: self._set_all_tags(False)).pack(side="left")

        # Action buttons
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_process = ttk.Button(action_frame, text="Process Images", style="Green.TButton",
                                       command=self._start_processing)
        self.btn_process.pack(side="left", padx=(0, 8))

        self.btn_try_again = ttk.Button(action_frame, text="Try Again", style="Secondary.TButton",
                                         command=self._try_again, state="disabled")
        self.btn_try_again.pack(side="left", padx=(0, 8))

        self.btn_rename = ttk.Button(action_frame, text="Rename Files", style="Green.TButton",
                                      command=self._rename_files, state="disabled")
        self.btn_rename.pack(side="left", padx=(0, 8))

        self.btn_save_txt = ttk.Button(action_frame, text="Save to TXT", style="Orange.TButton",
                                        command=self._save_to_txt, state="disabled")
        self.btn_save_txt.pack(side="left", padx=(0, 8))

        self.btn_new_task = ttk.Button(action_frame, text="New Task", style="Red.TButton",
                                        command=self._new_task, state="disabled")
        self.btn_new_task.pack(side="right")

        # Progress
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(frame, variable=self.progress_var, maximum=100,
                                         style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=16, pady=(0, 4))

        self.lbl_status = ttk.Label(frame, text="Ready", style="Status.TLabel")
        self.lbl_status.pack(anchor="w", padx=16)

        # Results table — use "tree headings" so #0 column shows thumbnails
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        cols = ("original", "title", "alt_text")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", selectmode="browse")

        self.tree.column("#0", width=90, minwidth=90, stretch=False)
        self.tree.heading("#0", text="Preview")

        self.tree.heading("original", text="Original Filename")
        self.tree.heading("title", text="New Title")
        self.tree.heading("alt_text", text="Alt Text")

        self.tree.column("original", width=220, minwidth=150)
        self.tree.column("title", width=250, minwidth=150)
        self.tree.column("alt_text", width=420, minwidth=200)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_settings_tab(self):
        frame = self.tab_settings
        container = ttk.Frame(frame)
        container.place(relx=0.5, rely=0.38, anchor="center")

        ttk.Label(container, text="Gemini API Settings", style="Header.TLabel").pack(pady=(0, 20))
        ttk.Label(container, text="API Key:").pack(anchor="w")
        self.entry_api_key = ttk.Entry(container, width=60, show="*")
        self.entry_api_key.pack(pady=(4, 4), ipady=6)
        self.entry_api_key.insert(0, self.api_key)

        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(container, text="Show key", variable=self.show_key_var,
                          command=self._toggle_key_visibility, style="Tag.TCheckbutton").pack(anchor="w", pady=(0, 12))

        ttk.Button(container, text="Save API Key", style="Green.TButton",
                    command=self._save_api_key).pack()

        self.lbl_settings_status = ttk.Label(container, text="", style="Status.TLabel")
        self.lbl_settings_status.pack(pady=(12, 0))
        ttk.Label(container, text=f"Model: {GEMINI_MODEL}", style="Sub.TLabel").pack(pady=(24, 0))

    # ── Settings ──────────────────────────────────────────────────────────

    def _toggle_key_visibility(self):
        self.entry_api_key.configure(show="" if self.show_key_var.get() else "*")

    def _save_api_key(self):
        key = self.entry_api_key.get().strip()
        if not key:
            messagebox.showwarning("Warning", "Please enter an API key.")
            return
        self.api_key = key
        self.config["api_key"] = key
        save_config(self.config)
        self.lbl_settings_status.configure(text="API key saved successfully!")
        self.root.after(3000, lambda: self.lbl_settings_status.configure(text=""))

    # ── Process Actions ───────────────────────────────────────────────────

    def _set_all_tags(self, value: bool):
        for var in self.tag_vars.values():
            var.set(value)

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if not folder:
            return
        self.folder_path = folder
        self.lbl_folder.configure(text=f"Folder: {folder}")
        self.image_files = sorted([
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if Path(f).suffix.lower() in IMAGE_EXTENSIONS
        ])
        count = len(self.image_files)
        self.lbl_status.configure(text=f"Found {count} image(s) in folder.")
        if count == 0:
            messagebox.showinfo("Info", "No images found in the selected folder.")

    def _get_selected_tags(self) -> list[str]:
        return [tag for tag, var in self.tag_vars.items() if var.get()]

    def _start_processing(self):
        key = self.entry_api_key.get().strip() if hasattr(self, "entry_api_key") else self.api_key
        if key:
            self.api_key = key
        if not self.api_key:
            messagebox.showwarning("No API Key", "Please set your Gemini API key in the Settings tab first.")
            self.notebook.select(self.tab_settings)
            return
        if not self.image_files:
            messagebox.showwarning("No Images", "Please choose a folder with images first.")
            return

        self.processing = True
        self.results.clear()
        self._thumb_refs.clear()
        self._clear_tree()
        self._set_buttons_processing(True)
        self.progress_var.set(0)

        tags = self._get_selected_tags()
        thread = threading.Thread(target=self._process_worker, args=(tags,), daemon=True)
        thread.start()

    def _process_worker(self, tags: list[str]):
        total = len(self.image_files)
        errors = []

        for i, filepath in enumerate(self.image_files):
            filename = os.path.basename(filepath)
            self.root.after(0, self._update_status, f"Processing {i + 1}/{total}: {filename}...")

            try:
                result = analyze_image(filepath, self.api_key, tags)
                title = result["title"]
                alt_text = result["alt_text"]
            except Exception as e:
                title = "ERROR"
                alt_text = str(e)[:120]
                errors.append(filename)

            entry = {
                "filepath": filepath,
                "original_name": filename,
                "title": title,
                "alt_text": alt_text,
            }
            self.results.append(entry)
            self.root.after(0, self._add_result_row, entry)
            self.root.after(0, self.progress_var.set, ((i + 1) / total) * 100)

        error_msg = f"  ({len(errors)} error(s))" if errors else ""
        self.root.after(0, self._update_status, f"Done! {total} image(s) processed.{error_msg}")
        self.root.after(0, self._set_buttons_processing, False)

    def _add_result_row(self, entry: dict):
        photo = make_thumbnail(entry["filepath"])
        if photo:
            self._thumb_refs.append(photo)
        self.tree.insert(
            "", "end",
            image=photo if photo else "",
            values=(entry["original_name"], entry["title"], entry["alt_text"]),
        )

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _update_status(self, text: str):
        self.lbl_status.configure(text=text)

    def _set_buttons_processing(self, is_processing: bool):
        self.processing = is_processing
        if is_processing:
            for btn in [self.btn_process, self.btn_try_again, self.btn_rename,
                        self.btn_save_txt, self.btn_new_task, self.btn_folder]:
                btn.configure(state="disabled")
        else:
            self.btn_process.configure(state="disabled")
            for btn in [self.btn_try_again, self.btn_rename, self.btn_save_txt,
                        self.btn_new_task, self.btn_folder]:
                btn.configure(state="normal")

    def _try_again(self):
        if not self.image_files:
            messagebox.showinfo("Info", "No images to process. Choose a folder first.")
            return
        self._start_processing()

    def _new_task(self):
        self.folder_path = ""
        self.image_files.clear()
        self.results.clear()
        self._thumb_refs.clear()
        self._clear_tree()
        self.progress_var.set(0)
        self.lbl_folder.configure(text="No folder selected")
        self.lbl_status.configure(text="Ready")
        self._set_all_tags(False)
        self.btn_process.configure(state="normal")
        for btn in [self.btn_try_again, self.btn_rename, self.btn_save_txt, self.btn_new_task]:
            btn.configure(state="disabled")

    def _rename_files(self):
        if not self.results:
            return
        valid = [r for r in self.results if r["title"] != "ERROR"]
        if not valid:
            messagebox.showwarning("No Valid Results", "All images had errors.")
            return

        confirm = messagebox.askyesno(
            "Confirm Rename",
            f"Rename {len(valid)} file(s) in:\n{self.folder_path}\n\nContinue?",
        )
        if not confirm:
            return

        renamed = errors = 0
        for result in valid:
            old_path = result["filepath"]
            if not os.path.exists(old_path):
                errors += 1
                continue
            ext = Path(old_path).suffix
            new_stem = sanitize_filename(result["title"])
            new_path = make_unique_path(os.path.dirname(old_path), new_stem, ext)
            try:
                os.rename(old_path, new_path)
                result["filepath"] = new_path
                renamed += 1
            except Exception:
                errors += 1

        msg = f"Renamed {renamed} file(s)."
        if errors:
            msg += f"  ({errors} error(s))"
        self.lbl_status.configure(text=msg)
        messagebox.showinfo("Rename Complete", msg)
        self.btn_rename.configure(state="disabled")

    def _save_to_txt(self):
        if not self.results:
            return
        filepath = filedialog.asksaveasfilename(
            title="Save Results",
            initialdir=self.folder_path or None,
            initialfile="seo_results.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("BASECOAT SEO IMAGE TOOL - RESULTS\n")
                f.write(f"Folder: {self.folder_path}\n")
                f.write("=" * 70 + "\n\n")
                for i, r in enumerate(self.results, 1):
                    f.write(f"Image {i}:\n")
                    f.write(f"  Original File: {r['original_name']}\n")
                    f.write(f"  Title:         {r['title']}\n")
                    f.write(f"  Alt Text:      {r['alt_text']}\n")
                    f.write(f"  New Filename:  {sanitize_filename(r['title'])}{Path(r['filepath']).suffix}\n")
                    f.write("\n")
            self.lbl_status.configure(text=f"Results saved to {os.path.basename(filepath)}")
            messagebox.showinfo("Saved", f"Results saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    # ── Inline Editing ────────────────────────────────────────────────────

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        col_index = int(col.replace("#", ""))
        if col_index not in (2, 3):
            return

        item = self.tree.identify_row(event.y)
        if not item:
            return
        bbox = self.tree.bbox(item, col)
        if not bbox:
            return

        current_values = self.tree.item(item, "values")
        current_text = current_values[col_index - 1]

        entry = tk.Entry(self.tree, font=("Segoe UI", 9))
        entry.insert(0, current_text)
        entry.select_range(0, "end")
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        entry.focus_set()

        def _save_edit(e=None):
            new_val = entry.get()
            vals = list(current_values)
            vals[col_index - 1] = new_val
            self.tree.item(item, values=vals)
            row_idx = self.tree.index(item)
            if row_idx < len(self.results):
                if col_index == 2:
                    self.results[row_idx]["title"] = new_val
                elif col_index == 3:
                    self.results[row_idx]["alt_text"] = new_val
            entry.destroy()

        entry.bind("<Return>", _save_edit)
        entry.bind("<Escape>", lambda e: entry.destroy())
        entry.bind("<FocusOut>", _save_edit)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = BasecoatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
