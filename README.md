# PDF CMYK Ink Coverage Analyzer

An industry-relevant print analytics system that accepts PDF files, evaluates page-by-page and document-wide CMYK (Cyan, Magenta, Yellow, Black) ink coverage percentages, checks for over-inking, and estimates printing costs.

## Features
- **Dual-Engine Processing**: Uses Ghostscript for industry-standard CMYK TIFF separations, and automatically falls back to a high-speed PyMuPDF rasterizer if Ghostscript is not installed.
- **Over-Inking Detection**: Visualizes areas where Total Ink Coverage (TIC = C+M+Y+K) exceeds absorption limits (e.g. 240% or 300%) using a heat map overlay with hot pink highlighting.
- **Dynamic Cost Configurator**: Simulates ink usage (in ml) and print job pricing ($) using customizable cartridge pricing and consumption rates.
- **Interactive Dashboard**: Grouped bar charts (Plotly), ink ratio pie charts, and page-by-page preview sliders.
- **Downloadable Reports**: Generate print-ready PDF reports (built with ReportLab) and tabular CSV logs.

---

## Step-by-Step Installation & Run Guide

Follow these steps to set up and run the project completely:

### Prerequisites
- Python 3.10 or higher.
- Git (optional, for version control).

---

### Step 1: Clone or Open the Project
Open your terminal (PowerShell, Command Prompt, or Bash) and navigate to the project directory:
```bash
cd "path/to/PDF CMYK Ink Analyzer"
```

### Step 2: Create a Virtual Environment
Initialize a clean Python virtual environment named `.venv` to isolate the project's dependencies:
```bash
python -m venv .venv
```

### Step 3: Activate the Virtual Environment
Activate the environment to ensure Python uses the local virtual packages:
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

### Step 4: Install Dependencies
Install all required libraries (Streamlit, PyMuPDF, Plotly, Pillow, NumPy, Matplotlib, ReportLab) in one command:
```bash
pip install -r requirements.txt
```

### Step 5: Run Automated Tests (Verification)
Verify that the channel splitting, cost formulas, overlays, and report compilers work correctly:
```bash
python -m unittest tests/test_analyzer.py
```
*(All 5 tests should return `OK`)*.

### Step 6: Start the Streamlit Dashboard
Run the Streamlit web application:
```bash
streamlit run src/app.py
```

Streamlit will launch a local web server and automatically open the application in your default web browser (usually at `http://localhost:8501`).

---

## Sharing & Git Best Practices
The project includes a `.gitignore` file that automatically prevents Git from tracking large or volatile temporary files. When sharing or pushing this project to GitHub/GitLab:
1. Pushing to Git will **exclude**:
   - The virtual environment folder `.venv/` (which friends can recreate themselves using these instructions).
   - Python runtime caches (`__pycache__/`).
   - Temporary file separations (`*.tif`).
2. Friends only need to clone the repository and start from **Step 2** to run the app on their system.
