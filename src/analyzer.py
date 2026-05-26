import os
import subprocess
import glob
import tempfile
import numpy as np
from PIL import Image
import fitz  # PyMuPDF
import matplotlib.pyplot as plt

def validate_pdf(file_path):
    """
    Validates that the file exists, is a valid PDF, and is readable.
    """
    if not os.path.exists(file_path):
        return False, "File does not exist."
    
    # Check size (e.g. limit to 50MB for Web App safety)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 50:
        return False, f"File is too large ({file_size_mb:.1f} MB). Max limit is 50 MB."
    
    try:
        # Check PDF header bytes
        with open(file_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                return False, "Invalid file format. Not a valid PDF."
        
        # Test opening with PyMuPDF
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        
        if page_count == 0:
            return False, "PDF has 0 pages or is corrupted."
        
        return True, f"Valid PDF with {page_count} pages."
    except Exception as e:
        return False, f"Failed to read PDF: {str(e)}"

def find_ghostscript():
    """
    Attempts to locate the Ghostscript executable (gswin64c.exe, gswin32c.exe, or gs)
    in the system PATH or default Windows installation paths.
    """
    # 1. Search in PATH
    for gs_bin in ["gswin64c", "gs", "gswin32c"]:
        try:
            # Run a quick check
            subprocess.run([gs_bin, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return gs_bin
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
            
    # 2. Search in common Windows installation paths
    common_paths = [
        "C:\\Program Files\\gs\\gs*\\bin\\gswin64c.exe",
        "C:\\Program Files (x86)\\gs\\gs*\\bin\\gswin32c.exe",
    ]
    for pattern in common_paths:
        matches = glob.glob(pattern)
        if matches:
            # Return the latest version found (sorted descending)
            matches.sort(reverse=True)
            return matches[0]
            
    return None

def render_page_cmyk_gs(gs_path, pdf_path, page_idx, dpi=150):
    """
    Renders a single page (1-based index) of the PDF to a CMYK TIFF image using Ghostscript.
    Returns the CMYK NumPy array, or None if it fails.
    """
    # Ghostscript pages are 1-based
    gs_page_num = page_idx + 1
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_tiff = os.path.join(temp_dir, f"page_{gs_page_num}.tif")
        
        # Build command: -sDEVICE=tiff32nc produces 32-bit CMYK TIFF
        cmd = [
            gs_path,
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=tiff32nc",
            f"-r{dpi}",
            f"-dFirstPage={gs_page_num}",
            f"-dLastPage={gs_page_num}",
            f"-sOutputFile={output_tiff}",
            pdf_path
        ]
        
        try:
            # Run command silently
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_tiff):
                with Image.open(output_tiff) as img:
                    # Verify it's loaded in CMYK mode
                    if img.mode != "CMYK":
                        img = img.convert("CMYK")
                    # Convert to numpy array
                    cmyk_arr = np.array(img)
                    return cmyk_arr
        except Exception as e:
            # Log error or print it
            print(f"Ghostscript rendering failed for page {gs_page_num}: {e}")
            
    return None

def render_page_cmyk_pymupdf(pdf_path, page_idx, dpi=150):
    """
    Renders a single page of the PDF to a CMYK NumPy array using PyMuPDF.
    This serves as a reliable fallback.
    """
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_idx]
        # Render page to CMYK Pixmap
        pix = page.get_pixmap(colorspace=fitz.csCMYK, dpi=dpi)
        
        # Convert raw samples bytes to NumPy array
        # CMYK has 4 channels: C, M, Y, K
        cmyk_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 4)
        return cmyk_arr.copy() # Make a copy to avoid buffer lifetime issues
    finally:
        doc.close()

def analyze_cmyk_array(cmyk_arr, tic_limit=240.0):
    """
    Given a CMYK array (H, W, 4), calculates:
    - Cyan, Magenta, Yellow, Black average coverage percentage
    - Total Ink Coverage (TIC) statistics (max, average, and over-inked pixel percentage)
    """
    # CMYK channels are:
    # 0: Cyan, 1: Magenta, 2: Yellow, 3: Black (Key)
    c_chan = cmyk_arr[:, :, 0]
    m_chan = cmyk_arr[:, :, 1]
    y_chan = cmyk_arr[:, :, 2]
    k_chan = cmyk_arr[:, :, 3]
    
    # Calculate coverage per channel
    # Coverage % = (sum of pixel intensities) / (255 * total pixels) * 100
    c_cov = (np.sum(c_chan) / (255.0 * c_chan.size)) * 100.0
    m_cov = (np.sum(m_chan) / (255.0 * m_chan.size)) * 100.0
    y_cov = (np.sum(y_chan) / (255.0 * y_chan.size)) * 100.0
    k_cov = (np.sum(k_chan) / (255.0 * k_chan.size)) * 100.0
    
    # Calculate TIC map (per-pixel Total Ink Coverage: C% + M% + Y% + K%)
    # Range is 0% to 400%
    tic_map = (c_chan.astype(np.float32) + m_chan + y_chan + k_chan) / 255.0 * 100.0
    
    avg_tic = c_cov + m_cov + y_cov + k_cov
    max_tic = float(np.max(tic_map))
   
    # Detect over-inking
    over_inked_mask = tic_map > tic_limit
    over_inked_ratio = (np.sum(over_inked_mask) / tic_map.size) * 100.0
    
    return {
        "cyan": c_cov,
        "magenta": m_cov,
        "yellow": y_cov,
        "black": k_cov,
        "avg_tic": avg_tic,
        "max_tic": max_tic,
        "over_inked_ratio": over_inked_ratio,
        "tic_map": tic_map,
        "over_inked_mask": over_inked_mask
    }

def get_page_preview_rgb(pdf_path, page_idx, dpi=100):
    """
    Renders page as an RGB PIL Image to serve as the background preview.
    """
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_idx]
        pix = page.get_pixmap(colorspace=fitz.csRGB, dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    finally:
        doc.close()

def generate_heatmap_overlay(rgb_img, tic_map, over_inked_mask, alpha=0.5):
    """
    Generates a blended image containing the RGB page layout and a semi-transparent CMYK density heatmap.
    Over-inked pixels are highlighted in neon pink/magenta.
    """
    orig_w, orig_h = rgb_img.size
    orig_arr = np.array(rgb_img)
    
    # Normalize TIC map (0-400%) to [0, 1] for matplotlib colormap
    normalized_tic = tic_map / 400.0
    
    # Generate colormap
    colormap = plt.get_cmap('jet')
    heatmap_rgba = colormap(normalized_tic) # Shape (H, W, 4), values in [0, 1]
    heatmap_rgb = (heatmap_rgba[:, :, :3] * 255).astype(np.uint8)
    
    # Resize heatmap to match RGB image size
    heatmap_pil = Image.fromarray(heatmap_rgb).resize((orig_w, orig_h), Image.Resampling.BILINEAR)
    heatmap_arr = np.array(heatmap_pil)
    
    # Create mask where ink is present (TIC > 1.0%)
    ink_present = tic_map > 1.0
    ink_mask_pil = Image.fromarray((ink_present * 255).astype(np.uint8)).resize((orig_w, orig_h), Image.Resampling.NEAREST)
    ink_mask_arr = np.array(ink_mask_pil) > 0
    
    # Blend RGB and Heatmap where ink is present
    blended_arr = orig_arr.copy()
    for c in range(3):
        blended_arr[:, :, c] = np.where(
            ink_mask_arr,
            (alpha * heatmap_arr[:, :, c] + (1 - alpha) * orig_arr[:, :, c]).astype(np.uint8),
            orig_arr[:, :, c]
        )
        
    # Resize over-inking mask
    over_inked_pil = Image.fromarray((over_inked_mask * 255).astype(np.uint8)).resize((orig_w, orig_h), Image.Resampling.NEAREST)
    over_inked_arr = np.array(over_inked_pil) > 0
    
    # Highlight over-inked areas with a bright magenta color [255, 0, 128]
    blended_arr[over_inked_arr] = [255, 0, 128]
    
    return Image.fromarray(blended_arr)

def process_pdf(pdf_path, dpi=150, tic_limit=240.0, progress_cb=None):
    """
    End-to-end PDF analysis:
    - Runs Ghostscript or PyMuPDF.
    - Yields page-wise statistics.
    """
    valid, msg = validate_pdf(pdf_path)
    if not valid:
        raise ValueError(msg)
        
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    gs_path = find_ghostscript()
    engine = "Ghostscript" if gs_path else "PyMuPDF (Fallback)"
    
    results = []
    
    for i in range(total_pages):
        cmyk_arr = None
        if gs_path:
            cmyk_arr = render_page_cmyk_gs(gs_path, pdf_path, i, dpi=dpi)
            
        # Fallback to PyMuPDF if GS is missing or failed
        if cmyk_arr is None:
            cmyk_arr = render_page_cmyk_pymupdf(pdf_path, i, dpi=dpi)
            
        # Analyze channels
        stats = analyze_cmyk_array(cmyk_arr, tic_limit=tic_limit)
        
        # Retrieve page dimensions from PyMuPDF
        doc_tmp = fitz.open(pdf_path)
        page_tmp = doc_tmp[i]
        width_pts, height_pts = page_tmp.rect.width, page_tmp.rect.height
        doc_tmp.close()
        
        # Dimensions: 1 pt = 1/72 inch, 1 inch = 0.0254 meters
        width_m = (width_pts / 72.0) * 0.0254
        height_m = (height_pts / 72.0) * 0.0254
        area_m2 = width_m * height_m
        
        page_data = {
            "page_num": i + 1,
            "width_in": width_pts / 72.0,
            "height_in": height_pts / 72.0,
            "area_m2": area_m2,
            "cyan": stats["cyan"],
            "magenta": stats["magenta"],
            "yellow": stats["yellow"],
            "black": stats["black"],
            "avg_tic": stats["avg_tic"],
            "max_tic": stats["max_tic"],
            "over_inked_ratio": stats["over_inked_ratio"],
            # Keep map and mask for visualization
            "tic_map": stats["tic_map"],
            "over_inked_mask": stats["over_inked_mask"]
        }
        
        results.append(page_data)
        
        if progress_cb:
            progress_cb(i + 1, total_pages)
            
    return results, engine
