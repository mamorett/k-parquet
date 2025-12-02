# 🖼️ Parquet Media Manager (KDE Edition)

**Parquet Media Manager** is a native Linux application (built with Python/PyQt6) designed to visualize, filter, and manage large **Parquet** datasets containing images and metadata.

Designed to integrate seamlessly with the **KDE Plasma** desktop environment, it offers high performance when handling datasets with 40,000+ images thanks to an intelligent pagination system and asynchronous loading.

---

## ✨ Key Features

* **🚀 High Performance:** Smooth navigation even with huge datasets (40k+ rows) via lazy loading and multithreading.
* **📂 Hybrid Support:** Automatically detects and reads images stored as binary data (`bytes`) within the parquet or as file paths (`path`) on disk.
* **🎨 KDE Integration:** Uses native system icons, dialogs, and themes for a consistent look and feel.
* **🖱️ Advanced Drag & Drop:** Drag images from the inspection window directly into Dolphin, Telegram, Browsers, or the Desktop to export/send them.
* **🔍 Search & Filter:** Instantly search text across all metadata fields (prompts, descriptions, filenames).
* **🎛️ Sorting:** Sort by filename, creation date, or last modification date.
* **📋 Smart Clipboard:** Quickly copy file paths, descriptions, or full JSON metadata with a single click.
* **🛡️ Crash-Proof:** Robust rendering engine that prevents segmentation faults and image distortion/skewing.

---

## 🛠️ Installation & Usage

No manual library installation is required. The project includes a **Smart Launcher** that handles the setup automatically.

### Prerequisites
* Linux (Optimized for KDE Plasma, but works on GNOME/XFCE with Qt libraries installed).
* Python 3 installed.

### First Run
1.  Open your terminal in the project folder.
2.  Make the launch script executable (only needed once):
    ```bash
    chmod +x start.sh
    ```
3.  Launch the application:
    ```bash
    ./start.sh
    ```

> **Note:** On the first run, the script will automatically create a hidden `.venv` folder, install all dependencies from `requirements.txt`, and start the program. Subsequent launches will be instant.

---

## 📖 User Guide

### 1. Loading a Dataset
Click **Open** in the toolbar and select a `.parquet` file.
The application automatically detects:
* Image columns (supporting both HuggingFace binary format and file paths).
* Metadata columns (descriptions, prompts, timestamps).

### 2. Navigation
* Use the **Arrow Buttons** in the toolbar to change pages.
* Use the **Slider** at the bottom to quickly scroll through thousands of pages.
* Use the **Number Box** to jump to a specific page (e.g., type `500` and press Enter).

### 3. Search & Sorting
* Type in the **Search...** box (e.g., "dog", "sunset") and press Enter or "Go". The grid will update to show only relevant results.
* Use the **Sort** dropdown menu to organize files by name or date.

### 4. Inspection & Drag-and-Drop
Click on any thumbnail to open the Detail Window.
* **Copy Data:** Use the top buttons to copy the file path or description to your clipboard.
* **Export (Drag & Drop):** Click and **hold** on the large preview image, then drag it into another application (like a File Manager or Chat app) to export the file instantly.

---

## 📂 Project Structure

```text
ParquetViewer/
├── main.py            # Application source code (v9.0)
├── requirements.txt   # Dependency list (PyQt6, pandas, pyarrow, Pillow)
├── start.sh           # Auto-setup launcher (Virtualenv manager)
└── README.md          # Project documentation
```
## ❓ Troubleshooting
The image is not showing (Gray rectangle)?

If the dataset uses file paths (path mode), ensure you launch the application from the correct root directory so relative paths remain valid.

If the files were moved or deleted, the app will display "File Missing".

The interface looks old/non-native?

Ensure you have the Qt6 integration packages installed for your Linux distribution (e.g., qt6-wayland, qt6-gtk-platformtheme).

## 📝 Credits
Developed as an internal tool for rapid management of AI training datasets (Image Captioning/Generation).

License: MIT / Open Source.