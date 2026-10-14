# 🐾 DeskBuddy — High-Utility Desktop Pet Companion

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20WSL-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple)
![Offline](https://img.shields.io/badge/100%25-Free%20%26%20Offline-success)
![Safety](https://img.shields.io/badge/Privacy-100%25%20Local-brightgreen)

<p align="center">
  <b>DeskBuddy</b> is a delightful, responsive desktop companion inspired by <i>Wuthering Waves</i> Resonators. <br/>
  Beyond charming animations and personality, DeskBuddy packs <b>blazing-fast desktop utility tools</b> that give you an unfair advantage over slow, clunky native OS workflows.
</p>

[Quick Install](#-1-click-quick-installation-windows) • [Features](#-features-breakdown) • [How to Use](#-how-to-use-controls--gestures) • [Why 100% Rule-Based?](#-why-rule-based--zero-ai-dependency) • [Build Standalone .EXE](#-building-a-standalone-exe)

</div>

---

## ⚡ Why DeskBuddy?

Most desktop pets are merely passive decorations. DeskBuddy actively solves daily desktop annoyances:
- 🎒 **Tired of opening File Explorer just to attach a file to Discord?** Drop it on Chisa and drag it straight into Discord in one fluid motion!
- ⚡ **Windows search taking forever?** DeskBuddy's Sub-Second File Finder locates files in milliseconds using native binary directory traversal.
- ✂️ **Doing quick math or checking color hex codes?** Just copy the text (<kbd>Ctrl</kbd> + <kbd>C</kbd>) and DeskBuddy calculates the answer or renders a color swatch right on your screen.
- 📁 **Messy desktop?** 1-Click Smart File Organizer gathers clutter into neat categorized folders with **100% reversible 1-click Undo**.
- 🧹 **Duplicate downloads & dead shortcuts piling up?** Spot duplicate installers and broken shortcuts to uninstalled apps and reclaim disk space with one click.

---

## 🚀 1-Click Quick Installation (Windows)

> [!TIP]
> **No programming or Python experience required!** DeskBuddy includes an automated self-bootstrapping installer.

### 💾 Option 1: Standalone .EXE (No Python Needed!)
Download the pre-compiled, portable release directly from GitHub:
👉 **[Download DeskBuddy-Windows-x64.zip (v1.0.0)](https://github.com/Reneilrp/DeskBuddy/releases/latest/download/DeskBuddy-Windows-x64.zip)**

1. Extract the downloaded `DeskBuddy-Windows-x64.zip`.
2. Double-click **`DeskBuddy.exe`** to start playing right away!

---

### ⚙️ Option 2: Run via Source / Installer Batch Script
1. Download the repository source as ZIP or clone it.
2. Double-click **`install.bat`**!

```
📁 DeskBuddy/
  ├── ⚙️ install.bat   <--- Double-click this!
  ├── 🚀 run.bat
  └── ...
```

**What `install.bat` does automatically:**
- ✅ Detects or installs Python (via Windows `winget` if missing).
- ✅ Sets up a clean, isolated virtual environment.
- ✅ Installs required dependencies.
- ✅ **Creates a desktop shortcut (`DeskBuddy.lnk`) on your Windows Desktop with the custom icon!**

You can now launch DeskBuddy anytime by double-clicking the **DeskBuddy** icon on your Desktop or `run.bat`!

---

### For Developers / Linux / WSL:
```bash
git clone https://github.com/your-username/DeskBuddy.git
cd DeskBuddy

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch
./run.sh
```

---

## ✨ Features Breakdown

### 1. 🎒 "Chisa's Pocket" (1-Drag File Stash & Bag Viewer)
Effortlessly hold files in temporary memory and drag them anywhere without cluttering your desktop:
- **Drop-In:** Drag any file(s) onto your desktop companion. A cute `🎒 {count}` badge appears docked on the companion.
- **🚀 1-Drag Extraction:** Simply **click and drag the 🎒 badge** directly into Discord, a browser upload box, or File Explorer in **one fluid motion**!
- **Shift-Drag:** Holding <kbd>Shift</kbd> while dragging your companion also initiates a native OS file drag.
- **🎒 Dedicated Pocket Viewer:** Click the 🎒 badge or the speech bubble chip to open the **Pocket Inventory Dialog**:
  - View real Windows file icons and formatted sizes.
  - Drag individual files out one-by-one or use the `[🚀 Drag All Files Out]` bar.
  - Reveal files in Explorer or clear the stash with one click.

---

### 2. ⚡ Fast File Finder ("Speed Grep")
Windows File Explorer search is notoriously slow and frequently indexes unnecessarily.
- Accessible directly in the **Companion Workspace** (<kbd>Double-click</kbd> pet or press *Open Workspace*).
- **Sub-Second Speed:** Searches your user profile, Downloads, Desktop, or custom directory in milliseconds.
- **Filter Chips:** Instant 1-click filter by Images (`*.png`), Documents (`*.pdf`), Code, Audio, Video, or Archives.
- **Actions:** 1-click `[📂 Reveal in Explorer]`, `[🚀 Open File]`, or `[📋 Copy File Path]`.

---

### 3. 📁 Smart File Organizer with 1-Click Reversible Undo
Clean up loose files on your Desktop or Downloads folder with zero stress:
- **Zero AI Hallucinations:** 100% deterministic rule-based organization.
- **Pre-Move Dry Run Table:** Displays exact source and proposed destination paths before touching a single file.
- **Multiple Rules:**
  - *By Type:* Subfolders for Images, Documents, Installers, Archives, etc.
  - *By Date:* Subfolders grouped by Year-Month (`2026-10/`).
  - *Custom Subfolder:* Gather matching files (e.g. `*.png`) into a folder of your choice.
- **100% Reversible 1-Click Undo:** Every move is logged in a reverse transaction log. If you don't like the result, click **`↩️ Undo Last Organization`** to restore every file to its exact original location.

---

### 4. 🧹 Duplicate Download & Broken Shortcut Hunter
Reclaim wasted gigabytes of disk space and tidy up orphaned links:
- **Duplicate Downloads:** Uses SHA-256 chunk-hashing to identify duplicate downloads (e.g. `driver (1).exe` vs `driver.exe`) with identical sizes and contents.
- **Broken Shortcut Cleaner:** Pure-Python Windows Shell `.lnk` parser inspects Desktop shortcuts and flags broken links whose target executables were uninstalled or deleted.
- **Selective Cleanup:** Check the items you want to remove and click **`🗑️ Clean Selected Items`** to reclaim space.

---

### 5. ✂️ Smart Clipboard Assistant ("Paper-Cut Tools")
Passively monitors your clipboard (<kbd>Ctrl</kbd> + <kbd>C</kbd>) and surfaces non-intrusive action chips:
- **🧮 Safe Math Evaluation:** Copy `1280 * 720 / 60` or `15% of 450` — companion displays the result with a 1-click `[📋 Copy Result]` button (evaluated via AST, strictly without `eval()`).
- **🎨 Color Swatch:** Copy `#FF8B77` or `rgb(56, 161, 105)` — companion renders the color swatch with a 1-click `[📋 Copy RGB]` button.
- **🖼️ 1-Click Image URL Downloader:** Copy direct image URLs (`https://...png`) — companion offers a 1-click `[💾 Save Image]` chip directly into your `Downloads/` folder.
- **📋 JSON Beautifier:** Copy minified one-line JSON — companion provides a 1-click `[✨ Beautify JSON]` button.

---

### 6. 🔔 "Just Downloaded" Background Auto-Prompt
Never hunt through File Explorer or browser download trays again:
- Actively watches `Downloads/` in the background, safely ignoring partial files (`.crdownload`, `.part`, `.tmp`).
- As soon as a download finishes, companion pops up with:
  - **`[📂 Reveal]`** — Opens File Explorer with that specific file selected.
  - **`[📁 Move to Category]`** — Moves it into its corresponding category subfolder.
  - **`[🚀 Open]`** — Launches the file immediately.

---

### 7. 💧 Ergonomics & Hydration Partner
Maintains your wellbeing during intense study or coding sessions:
- **20-20-20 Rule:** Every 45 minutes of active screen time, the companion performs a gentle stretch and prompts you to look 20 feet away for 20 seconds.
- **Hydration Tracker:** Click the **`[💧 +1 Glass of Water]`** chip on the speech bubble to increment your daily intake counter (e.g. `Hydration: 4/8 glasses today`).

---

### 8. ⏱️ Pomodoro Focus Partner
- Right-click the companion and choose **`⏱️ Start Pomodoro`**.
- Displays a 25-minute focus countdown badge over the companion.
- Notifies you with motivational character dialogue when it is time for a 5-minute break.

---

### 9. 🌊 24+ Wuthering Waves Resonators
Switch your companion anytime via the **Resonator Selector Dialog**:
- **Chisa** (Special featured companion with custom 2D animated sprites, walking, climbing active windows, sitting, blinking, and a physics paper-carp puppet rig!)
- **Spectro:** Jinhsi, Shorekeeper, Rover (Spectro), Verina
- **Fusion:** Changli, Encore, Chixia, Mortefi
- **Electro:** Yinlin, Xiangli Yao, Calcharo, Yuanwu
- **Aero:** Jiyan, Yangyang, Aalto, Hsin
- **Glacio:** Sanhua, Baizhi, Youhu, Lingyang
- **Havoc:** Camellya, Danjin, Taoqi, Aemaeth

---

## 🎮 How to Use (Controls & Gestures)

| Gesture / Input | Action |
| :--- | :--- |
| **Left-Click Pet** | Toggle Speech Bubble & Quick Chat Bar. |
| **Left-Click + Drag Pet** | Reposition pet anywhere on your screen (with gravity settling). |
| **Drag Files onto Pet** | Stashes files into Chisa's Pocket. |
| **Drag 🎒 Badge** | **1-Drag Drop:** Drops stashed files directly into Discord, Chrome, or Explorer! |
| **Shift + Drag Pet** | Alternative 1-drag file extraction. |
| **Click 🎒 Badge** | Opens the **Pocket Inventory Dialog** to inspect or manage stashed files. |
| **Double-Click Pet** | Opens the **Companion Workspace** (File Finder, Organizer, Hunter, Tasks). |
| **Pet Head Stroking** | Gently stroke the pet's head back and forth with the cursor for cheerful heart reactions! |
| **Right-Click Pet** | Opens the Full Context Menu (Workspace, Resonator Switcher, Pomodoro, Free Roam, etc.). |

---

## 🔒 Why Rule-Based & Zero AI Dependency?

All core features in DeskBuddy are intentionally designed using **pure, deterministic algorithms**:
- **100% Free & Open-Source:** No paid subscription, no token limits, and no API keys required.
- **Blazing Fast:** File search and organization run in under 0.01 seconds.
- **100% Private:** Your files and clipboard content never leave your machine or get transmitted across the internet.
- **No Hallucinations:** When sorting or searching files, deterministic rules guarantee 100% precision.

*(Optional: Natural conversational chat can be plugged into the Google Antigravity SDK (`google-antigravity`) for users who want companion AI brainstorming.)*

---

## 📦 Building a Standalone .EXE

If you want to distribute a completely standalone `.exe` package that does not require users to install Python:

1. Run **`install.bat`** once to setup the environment.
2. Run **`build_exe.bat`**.
3. PyInstaller will compile everything into:
   ```
   dist\DeskBuddy\DeskBuddy.exe
   ```
4. Simply zip the `dist\DeskBuddy\` folder and share it with anyone!

---

## 🛡️ Antivirus & Security Transparency

DeskBuddy is engineered with strict security hygiene:
- **No Global Keyloggers:** Clipboard assistant uses standard Qt `QClipboard.dataChanged` user-space events.
- **No Inbound Network Listening:** DeskBuddy does not open background server ports (zero firewall warnings).
- **Safe File Renaming:** Never overwrites existing files; uses incrementing counters (`file (1).ext`) and logs all actions to a reversible JSON history.

---

## 🤝 Contributing & License

Contributions, feature suggestions, and sprite submissions are warmly welcomed!
- Licensed under the **MIT License**.
- DeskBuddy is a fan-made desktop project created for productive desk companions.
