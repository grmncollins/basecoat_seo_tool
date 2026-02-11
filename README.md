# Basecoat SEO Image Tool

AI-powered image renaming & alt text generator for painting companies.  
Uses **Google Gemini 2.5 Flash** to analyze images and generate SEO-friendly titles and descriptions.

---

## Quick Start (Run without building)

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/) (check "Add to PATH" during install)
2. Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   python app.py
   ```

## Build as EXE (Windows)

1. Double-click **`build.bat`** (or run it from terminal)
2. Wait for it to finish — the EXE will be at `dist/Basecoat SEO Tool.exe`
3. Move the EXE wherever you want — it's fully portable

## How to Use

### Tab 1 — Process Images
1. **Click "Choose Folder"** → select a folder containing your painting images
2. **Select context tags** (optional) — if you know the folder has specific types (e.g., "Exterior House Painting", "Deck Staining"), check those tags to give the AI better context
3. **Click "Process Images"** → the AI analyzes each image and generates a Title + Alt Text
4. **Review results** in the table — double-click any Title or Alt Text cell to edit it
5. **Click "Rename Files"** → files are renamed using the generated titles (e.g., `Exterior-House-Painting.jpg`)
6. **"Try Again"** re-processes the same folder | **"New Task"** resets everything

### Tab 2 — Settings
- Enter your **Gemini API Key** and click Save
- Get a key at [Google AI Studio](https://aistudio.google.com/apikey)

## Features
- 🖼 **Thumbnail previews** in results table
- ✏️ **Inline editing** — double-click to fix any title/alt text before renaming
- 🏷 **Context tags** — help the AI understand your folder's content
- 🔄 **Try Again** — re-run the same batch if results aren't perfect
- 📁 **Smart renaming** — auto-handles filename collisions (adds -2, -3, etc.)
- 💾 **API key persistence** — saved to config.json, remembered between sessions

## Supported Image Formats
JPG, JPEG, PNG, WEBP, BMP, TIFF, GIF
